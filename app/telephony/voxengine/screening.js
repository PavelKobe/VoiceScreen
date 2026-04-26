/**
 * VoiceScreen — VoxEngine screening scenario.
 *
 * Launched by Voximplant StartScenarios (rule bound to the VoiceScreen app).
 * Expected customData (JSON string, set by app/telephony/voximplant.py):
 *   {
 *     "to_number":     "+7...",
 *     "candidate_id":  123,         // optional
 *     "scenario":      "courier_screening",
 *     "ws_url":        "wss://<host>/api/v1/ws/call",
 *     "call_id":       "<our id>"   // optional, session id if not provided
 *   }
 *
 * Flow:
 *   1. Parse customData.
 *   2. Outbound PSTN call to to_number.
 *   3. On answer: open WebSocket to backend.
 *   4. Backend ASR is done here via Yandex profile; transcripts are sent as
 *      {"type":"user_text"}.
 *   5. Backend sends {"type":"say"} — we TTS it back into the call.
 *   6. Backend sends {"type":"hangup"} — we end the call.
 *
 * NOTE: TTS is done via Voximplant-managed Yandex SpeechKit voice "Alena"
 *       (VoiceList.Yandex.Alena). Direct SpeechKit streaming via our own
 *       credentials remains a future option if we hit Voximplant limits.
 */

require(Modules.WebSocket);
require(Modules.ASR);

let data = {};
let toNumber, scenarioName, candidateId, wsUrl, callId;
let call = null;
let ws = null;
let asr = null;
let wasConnected = false;
let failureReported = false;

VoxEngine.addEventListener(AppEvents.Started, (e) => {
    data = JSON.parse(VoxEngine.customData() || "{}");

    toNumber     = data.to_number;
    scenarioName = data.scenario || "courier_screening";
    candidateId  = data.candidate_id || null;
    wsUrl        = data.ws_url;
    callId       = data.call_id || e.sessionId;

    if (!toNumber || !wsUrl) {
        Logger.write("VoiceScreen: missing to_number or ws_url, terminating");
        VoxEngine.terminate();
        return;
    }

    call = VoxEngine.callPSTN(toNumber, data.from_number || undefined);
    call.addEventListener(CallEvents.Connected, onCallConnected);
    call.addEventListener(CallEvents.Disconnected, onCallDisconnected);
    call.addEventListener(CallEvents.Failed, onCallFailed);
});

function onCallConnected() {
    Logger.write("VoiceScreen: call connected, opening WS");
    wasConnected = true;

    try { call.record(); } catch (err) {
        Logger.write("VoiceScreen: record() failed: " + err);
    }

    ws = VoxEngine.createWebSocket(wsUrl);
    ws.addEventListener(WebSocketEvents.OPEN,    onWsOpen);
    ws.addEventListener(WebSocketEvents.MESSAGE, onWsMessage);
    ws.addEventListener(WebSocketEvents.CLOSE,   onWsClose);
    ws.addEventListener(WebSocketEvents.ERROR,   onWsError);

    asr = VoxEngine.createASR({
        profile: ASRProfileList.Yandex.ru_RU,
        singleUtterance: false,
    });
    VoxEngine.sendMediaBetween(call, asr);
    asr.addEventListener(ASREvents.Result, onAsrResult);
    asr.addEventListener(ASREvents.ASRError, (e) => {
        Logger.write("VoiceScreen: ASR ERROR: " + JSON.stringify(e));
    });
}

function onWsOpen() {
    ws.send(JSON.stringify({
        type: "start",
        call_id: callId,
        candidate_id: candidateId,
        scenario: scenarioName,
        to_number: toNumber,
        ws_auth_token: data.ws_auth_token || "",
    }));
}

function onWsMessage(e) {
    let msg;
    try { msg = JSON.parse(e.text); } catch (_) {
        Logger.write("VoiceScreen: bad WS message: " + e.text);
        return;
    }
    if (msg.type === "say" && msg.text) {
        call.say(msg.text, VoiceList.Yandex.Neural.ru_RU_alena);
    } else if (msg.type === "hangup") {
        Logger.write("VoiceScreen: hangup requested by backend");
        call.hangup();
    }
}

function onAsrResult(e) {
    if (!e.text) return;
    if (ws && ws.readyState === "open") {
        ws.send(JSON.stringify({ type: "user_text", text: e.text }));
    }
}

function reportFailureAndTerminate(reason) {
    if (failureReported) { VoxEngine.terminate(); return; }
    failureReported = true;

    // wsUrl: wss://host/api/v1/ws/call → https://host/api/v1/webhooks/call_failed
    let webhookUrl = wsUrl
        .replace(/^wss:\/\//, "https://")
        .replace(/^ws:\/\//, "http://")
        .replace(/\/ws\/call$/, "/webhooks/call_failed");

    let payload = JSON.stringify({
        call_id: callId,
        candidate_id: candidateId,
        to_number: toNumber,
        scenario: scenarioName,
        reason: reason,
        auth_token: data.ws_auth_token || "",
    });

    Net.httpRequestAsync(webhookUrl, {
        method: "POST",
        postData: payload,
        contentType: "application/json",
    }, function (response) {
        Logger.write("VoiceScreen: failure webhook code=" + response.code);
        VoxEngine.terminate();
    });
}

function onCallDisconnected() {
    Logger.write("VoiceScreen: call disconnected");
    if (ws && ws.readyState === "open") {
        ws.send(JSON.stringify({ type: "call_ended", reason: "disconnected" }));
        ws.close();
        VoxEngine.terminate();
        return;
    }
    if (!wasConnected) {
        // Disconnected до Connected = звонок не дошёл (быстрый сброс).
        reportFailureAndTerminate("disconnected_before_connect");
        return;
    }
    VoxEngine.terminate();
}

function onCallFailed(e) {
    Logger.write("VoiceScreen: call failed code=" + e.code + " reason=" + e.reason);
    let reason = "failed:" + e.code;
    if (ws && ws.readyState === "open") {
        ws.send(JSON.stringify({ type: "call_ended", reason: reason }));
        ws.close();
        VoxEngine.terminate();
        return;
    }
    reportFailureAndTerminate(reason);
}

function onWsClose()   { Logger.write("VoiceScreen: WS closed"); }
function onWsError(e)  { Logger.write("VoiceScreen: WS error: " + (e.error || "")); }
