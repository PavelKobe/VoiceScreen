"""Webhooks from Voximplant VoxEngine scenarios."""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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

    async with async_session() as db:
        candidate = await db.get(Candidate, int(candidate_id))
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
        await db.commit()
        await db.refresh(call)

    log.info(
        "call_failed_recorded",
        candidate_id=candidate_id,
        call_db_id=call.id,
        reason=reason,
    )
    return {"status": "ok", "call_db_id": call.id}
