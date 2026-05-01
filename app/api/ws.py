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
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.dialog import DialogSession
from app.core.dispatch_window import schedule_next_attempt
from app.core.scenario import load_scenario
from app.core.scoring import score_call
from app.db.models import Call, CallTurn, Candidate, Vacancy
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
    summary: str | None = None,
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
        if summary is not None:
            call.summary = summary
        await db.commit()


def _format_transcript(history: list[dict[str, str]]) -> str:
    label = {"assistant": "agent", "user": "candidate"}
    return "\n".join(f"{label.get(m['role'], m['role'])}: {m['content']}" for m in history)


async def _schedule_silent_retry(candidate_id: int, call_id: str | None) -> None:
    """После «молчаливого» звонка планируем retry — та же логика, что в
    webhook /call_failed: count(*) calls = source of truth, eta из
    `schedule_next_attempt` (учитывает vacancy.call_slots или глобальный
    backoff), при exhausted — соответствующий статус.
    """
    # Импорт здесь — circular import workers→api→workers иначе.
    from app.workers.tasks import initiate_call, schedule_sms_for_attempt

    try:
        async with async_session() as db:
            cand_q = await db.execute(
                select(Candidate)
                .options(selectinload(Candidate.vacancy))
                .where(Candidate.id == candidate_id)
            )
            candidate = cand_q.scalar_one_or_none()
            if candidate is None:
                log.warning("ws_silent_retry_candidate_missing", candidate_id=candidate_id)
                return

            now = datetime.utcnow()
            total_attempts = (
                await db.execute(
                    select(func.count(Call.id)).where(Call.candidate_id == candidate_id)
                )
            ).scalar_one()
            candidate.attempts_count = int(total_attempts)

            retry_eta = schedule_next_attempt(
                candidate.vacancy.call_slots if candidate.vacancy else None,
                attempts_count=candidate.attempts_count,
                after_utc=now,
            )
            if retry_eta is not None:
                candidate.next_attempt_at = retry_eta
                candidate.status = "pending"
            else:
                candidate.status = "exhausted"
                candidate.next_attempt_at = None

            await db.commit()

        if retry_eta is not None:
            initiate_call.apply_async(
                args=[candidate_id],
                kwargs={"expect_scheduled": True},
                eta=retry_eta,
            )
            if candidate.vacancy is not None:
                schedule_sms_for_attempt(
                    candidate_id=candidate_id,
                    vacancy=candidate.vacancy,
                    eta=retry_eta,
                )

        log.info(
            "ws_silent_retry_scheduled",
            call_id=call_id,
            candidate_id=candidate_id,
            attempts_count=int(total_attempts),
            retry_eta=retry_eta.isoformat() + "Z" if retry_eta else None,
            exhausted=retry_eta is None,
        )
    except Exception as exc:
        log.exception(
            "ws_silent_retry_failed",
            call_id=call_id,
            candidate_id=candidate_id,
            error=str(exc),
        )


@router.websocket("/call")
async def call_ws(ws: WebSocket) -> None:
    await ws.accept()
    session: DialogSession | None = None
    call_id: str | None = None
    db_call_id: int | None = None
    candidate_id: int | None = None
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
                scenario_slug = msg.get("scenario", "courier_screening")
                candidate_id = msg.get("candidate_id")
                log.info(
                    "ws_call_start",
                    call_id=call_id,
                    scenario=scenario_slug,
                    candidate_id=candidate_id,
                )
                db_call_id = await _create_call_record(call_id, candidate_id)

                # Резолвим client_id и загружаем сценарий из БД (с lazy-seed из YAML).
                async with async_session() as db:
                    cand = (
                        await db.get(Candidate, candidate_id) if candidate_id else None
                    )
                    if cand is None:
                        log.warning("ws_candidate_missing", candidate_id=candidate_id)
                        await ws.close(code=4400)
                        return
                    vacancy = await db.get(Vacancy, cand.vacancy_id)
                    if vacancy is None:
                        log.warning("ws_vacancy_missing", vacancy_id=cand.vacancy_id)
                        await ws.close(code=4400)
                        return
                    try:
                        scenario_dict = await load_scenario(
                            scenario_slug, vacancy.client_id, db
                        )
                    except FileNotFoundError:
                        log.warning(
                            "ws_scenario_missing",
                            slug=scenario_slug,
                            client_id=vacancy.client_id,
                        )
                        await ws.close(code=4404)
                        return

                session = DialogSession(scenario_dict)
                greeting = session.get_greeting()
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
                reply = session.process_candidate_reply(text)
                if reply is None:
                    # Сессия уже была завершена — кандидат продолжает говорить
                    # после прощания. Просто молча кладём трубку.
                    await ws.send_text(json.dumps({"type": "hangup"}))
                    break
                if db_call_id is not None:
                    await _append_turn(db_call_id, "agent", reply, turn_order)
                    turn_order += 1
                await ws.send_text(json.dumps({"type": "say", "text": reply}))
                # Если бэк только что произнёс прощание — кладём трубку, не ждём
                # следующей реплики кандидата.
                if session.finished:
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
            transcript = session.get_transcript()
            transcript_text = _format_transcript(transcript)
            user_turns_count = sum(1 for t in transcript if t.get("role") == "user")

            if user_turns_count == 0:
                # Соединение состоялось (Voximplant видел Connected), но
                # кандидат не сказал ни слова — voicemail/долгие гудки и т.п.
                # Не зовём LLM (он бы вернул reject на пустоте), а сразу
                # помечаем как not_reached и отправляем в retry-цикл.
                log.info(
                    "ws_silent_call_treated_as_not_reached",
                    call_id=call_id,
                    candidate_id=candidate_id,
                )
                try:
                    await _finalize_call(
                        db_call_id,
                        transcript_text,
                        score=None,
                        decision="not_reached",
                        reasoning="Кандидат не ответил (соединение было, но речи не зафиксировано)",
                        answers=None,
                    )
                except Exception as exc:
                    log.exception(
                        "ws_finalize_failed_silent", call_id=call_id, error=str(exc),
                    )
                if candidate_id is not None:
                    await _schedule_silent_retry(int(candidate_id), call_id)
            else:
                # Обычный путь: есть реплики кандидата, скорим через LLM.
                score: float | None = None
                decision: str | None = None
                reasoning: str | None = None
                answers: dict | None = None
                summary: str | None = None
                # Для анонимизации перед LLM нужен candidate.fio.
                candidate_fio: str | None = None
                if candidate_id is not None:
                    try:
                        async with async_session() as db:
                            cand = await db.get(Candidate, candidate_id)
                            if cand is not None:
                                candidate_fio = cand.fio
                    except Exception as exc:
                        log.exception("ws_load_candidate_fio_failed", call_id=call_id, error=str(exc))
                try:
                    result = await score_call(
                        session.scenario, transcript, candidate_fio=candidate_fio,
                    )
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
                    raw_summary = result.get("summary")
                    if isinstance(raw_summary, str):
                        summary = raw_summary
                except Exception as exc:
                    log.exception("ws_scoring_failed", call_id=call_id, error=str(exc))
                try:
                    await _finalize_call(
                        db_call_id, transcript_text,
                        score=score, decision=decision,
                        reasoning=reasoning, answers=answers, summary=summary,
                    )
                except Exception as exc:
                    log.exception("ws_finalize_failed", call_id=call_id, error=str(exc))
                # Кандидат закрывается только при финальном решении. Если scoring
                # упал (decision is None) — оставляем in_progress как сигнал «надо
                # посмотреть руками».
                if decision in ("pass", "reject", "review") and candidate_id is not None:
                    try:
                        async with async_session() as db:
                            cand = await db.get(Candidate, candidate_id)
                            if cand is not None:
                                cand.status = "done"
                                cand.next_attempt_at = None
                                await db.commit()
                    except Exception as exc:
                        log.exception("ws_done_transition_failed", call_id=call_id, error=str(exc))
                # HR-уведомление по итогам — задача сама проверит политику
                # notify_on/notify_emails в Vacancy и no-op'нет, если выключено.
                if decision in ("pass", "reject", "review"):
                    try:
                        from app.workers.tasks import send_call_result_email
                        send_call_result_email.apply_async(
                            args=[db_call_id], countdown=5,
                        )
                    except Exception as exc:
                        log.exception(
                            "ws_enqueue_email_failed", call_id=call_id, error=str(exc),
                        )
            try:
                from app.workers.tasks import fetch_recording
                fetch_recording.apply_async(args=[db_call_id], countdown=30)
            except Exception as exc:
                log.exception("ws_enqueue_fetch_recording_failed", call_id=call_id, error=str(exc))
        if session is not None:
            log.info(
                "ws_session_closed",
                call_id=call_id,
                db_call_id=db_call_id,
                turns=len(session.get_transcript()),
            )
