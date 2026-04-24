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
from datetime import datetime

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.core.dialog import DialogSession
from app.core.scoring import score_call
from app.db.models import Call, CallTurn, Candidate
from app.db.session import async_session

router = APIRouter()
log = structlog.get_logger()


async def _create_call_record(vox_call_id: str, candidate_id: int | None) -> int | None:
    """Create Call row tied to candidate. Returns Call.id or None if candidate missing."""
    if not candidate_id:
        return None
    async with async_session() as db:
        candidate = await db.get(Candidate, candidate_id)
        if candidate is None:
            log.warning("candidate_not_found", candidate_id=candidate_id)
            return None
        call = Call(
            candidate_id=candidate_id,
            voximplant_call_id=str(vox_call_id) if vox_call_id else None,
            started_at=datetime.utcnow(),
        )
        db.add(call)
        await db.commit()
        await db.refresh(call)
        return call.id


async def _append_turn(db_call_id: int, speaker: str, text: str, order: int) -> None:
    async with async_session() as db:
        db.add(CallTurn(call_id=db_call_id, speaker=speaker, text=text, order=order))
        await db.commit()


async def _finalize_call(
    db_call_id: int,
    transcript: str,
    score: float | None = None,
    decision: str | None = None,
    reasoning: str | None = None,
    answers: dict | None = None,
) -> None:
    async with async_session() as db:
        call = await db.get(Call, db_call_id)
        if call is None:
            return
        now = datetime.utcnow()
        call.finished_at = now
        if call.started_at:
            call.duration = int((now - call.started_at).total_seconds())
        call.transcript = transcript
        if score is not None:
            call.score = score
        if decision is not None:
            call.decision = decision
        if reasoning is not None:
            call.score_reasoning = reasoning
        if answers is not None:
            call.answers = answers
        await db.commit()


def _format_transcript(history: list[dict[str, str]]) -> str:
    label = {"assistant": "agent", "user": "candidate"}
    return "\n".join(f"{label.get(m['role'], m['role'])}: {m['content']}" for m in history)


@router.websocket("/call")
async def call_ws(ws: WebSocket) -> None:
    await ws.accept()
    session: DialogSession | None = None
    call_id: str | None = None
    db_call_id: int | None = None
    turn_order: int = 0

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "start":
                call_id = msg.get("call_id")
                if settings.ws_auth_token:
                    provided = msg.get("ws_auth_token", "")
                    if provided != settings.ws_auth_token:
                        log.warning("ws_auth_rejected", call_id=call_id)
                        await ws.close(code=4401)
                        return
                scenario = msg.get("scenario", "courier_screening")
                candidate_id = msg.get("candidate_id")
                log.info("ws_call_start", call_id=call_id, scenario=scenario, candidate_id=candidate_id)
                db_call_id = await _create_call_record(call_id, candidate_id)
                session = DialogSession(scenario)
                greeting = await session.get_greeting()
                if db_call_id is not None:
                    await _append_turn(db_call_id, "agent", greeting, turn_order)
                    turn_order += 1
                await ws.send_text(json.dumps({"type": "say", "text": greeting}))

            elif mtype == "user_text":
                if session is None:
                    log.warning("ws_user_text_without_session", call_id=call_id)
                    continue
                text = msg.get("text", "")
                if db_call_id is not None and text:
                    await _append_turn(db_call_id, "candidate", text, turn_order)
                    turn_order += 1
                reply = await session.process_candidate_reply(text)
                if reply is None:
                    await ws.send_text(json.dumps({"type": "hangup"}))
                    break
                if db_call_id is not None:
                    await _append_turn(db_call_id, "agent", reply, turn_order)
                    turn_order += 1
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
        if session is not None and db_call_id is not None:
            transcript_text = _format_transcript(session.get_transcript())
            score: float | None = None
            decision: str | None = None
            reasoning: str | None = None
            answers: dict | None = None
            try:
                result = await score_call(session.scenario, session.get_transcript())
                raw_score = result.get("score")
                if isinstance(raw_score, (int, float)):
                    score = float(raw_score)
                raw_decision = result.get("decision")
                if isinstance(raw_decision, str):
                    decision = raw_decision
                raw_reasoning = result.get("reasoning")
                if isinstance(raw_reasoning, str):
                    reasoning = raw_reasoning
                raw_answers = result.get("answers")
                if isinstance(raw_answers, dict):
                    answers = raw_answers
            except Exception as exc:
                log.exception("ws_scoring_failed", call_id=call_id, error=str(exc))
            try:
                await _finalize_call(
                    db_call_id, transcript_text,
                    score=score, decision=decision,
                    reasoning=reasoning, answers=answers,
                )
            except Exception as exc:
                log.exception("ws_finalize_failed", call_id=call_id, error=str(exc))
        if session is not None:
            log.info(
                "ws_session_closed",
                call_id=call_id,
                db_call_id=db_call_id,
                turns=len(session.get_transcript()),
            )
