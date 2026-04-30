"""Webhooks from Voximplant VoxEngine scenarios."""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.dispatch_window import schedule_next_attempt
from app.db.models import Call, Candidate
from app.db.session import async_session

router = APIRouter()
log = structlog.get_logger()


@router.post("/voximplant/call-event")
async def voximplant_call_event(request: Request) -> dict:
    """Webhook from Voximplant on call state changes (HTTP from VoxEngine)."""
    body = await request.json()
    log.info("voximplant_call_event", payload=body)
    return {"status": "ok"}


@router.post("/voximplant/media-stream")
async def voximplant_media_stream(request: Request) -> dict:
    """HTTP fallback for media-stream metadata."""
    return {"status": "ok"}


@router.post("/call_failed")
async def call_failed(request: Request) -> dict:
    """VoxEngine сообщает о звонке, который не дошёл до Connected (busy / no answer / declined / blocked).

    Создаём Call-строку с `decision='not_reached'`, чтобы кандидат не выглядел
    как «не обзвонённый» в UI. Защищено `ws_auth_token` (если задан).
    """
    body = await request.json()

    if settings.ws_auth_token:
        if body.get("auth_token") != settings.ws_auth_token:
            log.warning("call_failed_webhook_auth_rejected")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    candidate_id = body.get("candidate_id")
    reason = body.get("reason", "unknown")
    voximplant_call_id = body.get("call_id")

    if not candidate_id:
        log.warning("call_failed_webhook_no_candidate", body=body)
        return {"status": "no_candidate"}

    # Импорт здесь, чтобы избежать циклической зависимости api → workers → api.
    from app.workers.tasks import initiate_call

    async with async_session() as db:
        # Загружаем кандидата вместе с вакансией — нужны её call_slots
        # для расписания следующей попытки.
        cand_q = await db.execute(
            select(Candidate)
            .options(selectinload(Candidate.vacancy))
            .where(Candidate.id == int(candidate_id))
        )
        candidate = cand_q.scalar_one_or_none()
        if candidate is None:
            log.warning("call_failed_webhook_candidate_missing", candidate_id=candidate_id)
            return {"status": "candidate_not_found"}

        now = datetime.utcnow()
        call = Call(
            candidate_id=candidate.id,
            voximplant_call_id=str(voximplant_call_id) if voximplant_call_id else None,
            started_at=now,
            finished_at=now,
            duration=0,
            decision="not_reached",
            score_reasoning=f"Не дозвонились ({reason})",
        )
        db.add(call)
        await db.flush()

        # Source of truth для счётчика — фактический count(*) в calls.
        total_attempts = (
            await db.execute(
                select(func.count(Call.id)).where(Call.candidate_id == candidate.id)
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
        await db.refresh(call)

    if retry_eta is not None:
        initiate_call.apply_async(
            args=[int(candidate_id)],
            kwargs={"expect_scheduled": True},
            eta=retry_eta,
        )

    log.info(
        "call_failed_recorded",
        candidate_id=candidate_id,
        call_db_id=call.id,
        reason=reason,
        attempts_count=candidate.attempts_count if candidate else None,
        retry_eta=retry_eta.isoformat() + "Z" if retry_eta else None,
        exhausted=retry_eta is None,
    )
    return {"status": "ok", "call_db_id": call.id}
