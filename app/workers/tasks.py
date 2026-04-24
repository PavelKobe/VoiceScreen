"""Celery tasks for call processing.

Each task creates a fresh SQLAlchemy async engine — переиспользовать
глобальный engine из app.db.session нельзя: Celery запускает async-код
через asyncio.run() в новом event loop'е на каждый таск, а asyncpg
connection-pool привязан к предыдущему loop'у и падает с
"another operation is in progress".
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import Call, Candidate, Vacancy
from app.telephony.voximplant import get_record_url, originate_call
from app.workers.celery_app import celery_app

log = structlog.get_logger()


@asynccontextmanager
async def _task_session() -> AsyncIterator[AsyncSession]:
    """Per-task engine — избегаем cross-loop pool re-use."""
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with maker() as session:
            yield session
    finally:
        await engine.dispose()


async def _initiate_call_async(candidate_id: int) -> dict:
    async with _task_session() as db:
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

    TODO: upload recording to Object Storage, notify client via Telegram.
    Score + transcript уже персистятся в ws.py, recording_url
    подтягивается отдельным таском fetch_recording.
    """
    log.info("task_finalize_call", call_id=call_id)
    return {"call_id": call_id, "status": "noop"}


async def _fetch_recording_async(call_db_id: int) -> str | None:
    async with _task_session() as db:
        call = await db.get(Call, call_db_id)
        if call is None or not call.voximplant_call_id:
            return None
        vox_id = call.voximplant_call_id

    url = await get_record_url(vox_id)
    if not url:
        return None

    async with _task_session() as db:
        call = await db.get(Call, call_db_id)
        if call is None:
            return None
        call.recording_url = url
        await db.commit()
    return url


@celery_app.task(bind=True, max_retries=6, default_retry_delay=60)
def fetch_recording(self, call_db_id: int) -> dict:
    """Pull Voximplant record_url for a completed call and store it.

    Recordings are not instantly available after hangup — Voximplant
    нужно время для обработки. Retry с задержкой: 6 попыток × 60 сек
    ≈ 6 минут окно ожидания.
    """
    log.info("task_fetch_recording", call_db_id=call_db_id, attempt=self.request.retries + 1)
    try:
        url = asyncio.run(_fetch_recording_async(call_db_id))
    except Exception as exc:
        log.exception("task_fetch_recording_error", call_db_id=call_db_id, error=str(exc))
        raise self.retry(exc=exc)
    if url is None:
        log.info("task_fetch_recording_not_ready", call_db_id=call_db_id)
        raise self.retry()
    log.info("task_fetch_recording_saved", call_db_id=call_db_id, url=url)
    return {"call_db_id": call_db_id, "recording_url": url}


@celery_app.task
def schedule_pending_calls() -> int:
    """Periodic task: find pending candidates and enqueue calls.

    TODO: respect timezone (9:00–21:00 local), max 3 attempts, rate limits.
    """
    log.info("task_schedule_pending_calls")
    return 0
