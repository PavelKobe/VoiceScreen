"""WebSocket endpoint for VoxEngine screening scenario.

Protocol (JSON text frames):

  client (VoxEngine) -> server:
    {"type": "start", "call_id": "...", "scenario": "courier_screening",
     "candidate_id": 123, "to_number": "+7..."}
    {"type": "user_text", "text": "..."}          // ASR result from VoxEngine
    {"type": "call_ended", "reason": "..."}

  server -> client:
    {"type": "say", "text": "..."}                 // agent reply, speak via TTS
    {"type": "hangup"}                             // end the call

Binary audio streaming (for custom SpeechKit TTS in the call) is a TODO —
see app/telephony/CLAUDE.md.
"""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.dialog import DialogSession

router = APIRouter()
log = structlog.get_logger()


@router.websocket("/call")
async def call_ws(ws: WebSocket) -> None:
    await ws.accept()
    session: DialogSession | None = None
    call_id: str | None = None

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "start":
                call_id = msg.get("call_id")
                scenario = msg.get("scenario", "courier_screening")
                log.info("ws_call_start", call_id=call_id, scenario=scenario)
                session = DialogSession(scenario)
                greeting = await session.get_greeting()
                await ws.send_text(json.dumps({"type": "say", "text": greeting}))

            elif mtype == "user_text":
                if session is None:
                    log.warning("ws_user_text_without_session", call_id=call_id)
                    continue
                text = msg.get("text", "")
                reply = await session.process_candidate_reply(text)
                if reply is None:
                    await ws.send_text(json.dumps({"type": "hangup"}))
                    break
                await ws.send_text(json.dumps({"type": "say", "text": reply}))
                # Natural end of scenario — farewell already sent, now hang up.
                if session.turn_count >= session.scenario.get("max_turns", 20):
                    await ws.send_text(json.dumps({"type": "hangup"}))
                    break

            elif mtype == "call_ended":
                log.info("ws_call_ended", call_id=call_id, reason=msg.get("reason"))
                break

            else:
                log.warning("ws_unknown_message_type", type=mtype, call_id=call_id)

    except WebSocketDisconnect:
        log.info("ws_disconnected", call_id=call_id)
    except Exception as exc:
        log.exception("ws_error", call_id=call_id, error=str(exc))
    finally:
        # TODO: persist session.get_transcript() into DB via CallTurn.
        if session is not None:
            log.info(
                "ws_session_closed",
                call_id=call_id,
                turns=len(session.get_transcript()),
            )
