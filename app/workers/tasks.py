"""Celery tasks for call processing."""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Candidate, Vacancy
from app.db.session import async_session
from app.telephony.voximplant import originate_call
from app.workers.celery_app import celery_app

log = structlog.get_logger()


async def _initiate_call_async(candidate_id: int) -> dict:
    async with async_session() as db:
        result = await db.execute(
            select(Candidate)
            .options(selectinload(Candidate.vacancy))
            .where(Candidate.id == candidate_id)
        )
        candidate = result.scalar_one_or_none()
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found")
        vacancy: Vacancy = candidate.vacancy

    vox_result = await originate_call(
        candidate.phone,
        {
            "scenario": vacancy.scenario_name,
            "candidate_id": candidate.id,
        },
    )
    return {
        "candidate_id": candidate.id,
        "phone": candidate.phone,
        "scenario": vacancy.scenario_name,
        "voximplant_session_id": vox_result.get("call_session_history_id"),
        "status": "initiated",
    }


@celery_app.task(bind=True, max_retries=3)
def initiate_call(self, candidate_id: int) -> dict:
    """Initiate a screening call to a candidate.

    Loads candidate + linked vacancy, fires Voximplant StartScenarios.
    The VoxEngine scenario then originates the PSTN call and opens a WS
    back to our backend, which creates the Call record on 'start'.
    """
    log.info("task_initiate_call", candidate_id=candidate_id)
    try:
        return asyncio.run(_initiate_call_async(candidate_id))
    except Exception as exc:
        log.exception("task_initiate_call_failed", candidate_id=candidate_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=2)
def finalize_call(self, call_id: int) -> dict:
    """Finalize a completed call.

    TODO: download recording from Voximplant, upload to Object Storage,
    notify client via Telegram. Score + transcript already persisted
    from ws.py on call end.
    """
    log.info("task_finalize_call", call_id=call_id)
    return {"call_id": call_id, "status": "noop"}


@celery_app.task
def schedule_pending_calls() -> int:
    """Periodic task: find pending candidates and enqueue calls.

    TODO: respect timezone (9:00–21:00 local), max 3 attempts, rate limits.
    """
    log.info("task_schedule_pending_calls")
    return 0
