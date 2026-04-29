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

import httpx
import structlog
from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Call, Candidate, Vacancy
from app.storage.yos import upload_recording
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


async def _initiate_call_async(candidate_id: int, expect_scheduled: bool = False) -> dict:
    """Атомарный гейт по лимиту попыток + старт звонка.

    Один SQL UPDATE инкрементирует attempts_count, выставляет status='in_progress'
    и обнуляет next_attempt_at — но только если кандидат активен, не исчерпан/done
    и attempts_count < max. Если 0 строк обновилось — задача выходит без звонка
    (страховка от гонок: одновременно стартовавшие дубликаты задач не дадут
    лишних звонков).

    Параметр `expect_scheduled` отличает bulk/retry-задачи (стоят в очереди
    с заранее заданным next_attempt_at) от одиночного звонка через
    «Позвонить» (без расписания). Для запланированных задач гейт
    дополнительно требует `next_attempt_at IS NOT NULL` — это даёт HR
    реальную возможность отменить запланированный звонок: достаточно
    обнулить next_attempt_at в БД (через reset_attempts), и стоящая в
    Celery задача при срабатывании молча пропустится.

    Счётчик инкрементируется ДО успешного originate_call. Trade-off: при сетевой
    ошибке Voximplant попытка «потратится». На нашем объёме это редко и
    предпочтительнее, чем риск 4 параллельных звонков одному кандидату.
    """
    async with _task_session() as db:
        # Условие гейта расширено EXISTS-проверкой: вакансия должна быть
        # активной и не на паузе (Vacancy.dispatch_paused=False). Это даёт
        # «горячее» отключение: уже стоящие в очереди задачи молча
        # пропускаются после нажатия HR'ом «Приостановить обзвон» — без
        # необходимости перебирать и удалять что-то из Celery вручную.
        active_vacancy = (
            select(Vacancy.id)
            .where(
                Vacancy.id == Candidate.vacancy_id,
                Vacancy.active.is_(True),
                Vacancy.dispatch_paused.is_(False),
            )
        )
        conditions = [
            Candidate.id == candidate_id,
            Candidate.active.is_(True),
            Candidate.attempts_count < settings.call_max_attempts,
            Candidate.status.notin_(("exhausted", "done")),
            exists(active_vacancy),
        ]
        if expect_scheduled:
            conditions.append(Candidate.next_attempt_at.is_not(None))

        result = await db.execute(
            update(Candidate)
            .where(*conditions)
            .values(
                attempts_count=Candidate.attempts_count + 1,
                status="in_progress",
                next_attempt_at=None,
            )
            .returning(
                Candidate.vacancy_id,
                Candidate.phone,
                Candidate.attempts_count,
            )
        )
        row = result.first()
        await db.commit()

        if row is None:
            log.info("task_initiate_call_gate_blocked", candidate_id=candidate_id)
            return {"candidate_id": candidate_id, "status": "skipped"}

        vacancy_id, phone, attempts_count = row
        vacancy = await db.get(Vacancy, vacancy_id)
        if vacancy is None:
            raise ValueError(f"Vacancy {vacancy_id} for candidate {candidate_id} not found")
        scenario_name = vacancy.scenario_name

    vox_result = await originate_call(
        phone,
        {
            "scenario": scenario_name,
            "candidate_id": candidate_id,
        },
    )

    return {
        "candidate_id": candidate_id,
        "phone": phone,
        "scenario": scenario_name,
        "voximplant_session_id": vox_result.get("call_session_history_id"),
        "attempts_count": attempts_count,
        "status": "initiated",
    }


@celery_app.task(bind=True, max_retries=3)
def initiate_call(self, candidate_id: int, expect_scheduled: bool = False) -> dict:
    """Initiate a screening call to a candidate.

    Loads candidate + linked vacancy, fires Voximplant StartScenarios.
    The VoxEngine scenario then originates the PSTN call and opens a WS
    back to our backend, which creates the Call record on 'start'.

    `expect_scheduled` — для bulk/retry задач (требуют next_attempt_at != NULL,
    чтобы можно было отменить запланированное обзвонивание простой очисткой
    поля). Одиночный звонок через POST /candidates/{id}/call оставляет False.
    """
    log.info("task_initiate_call", candidate_id=candidate_id, expect_scheduled=expect_scheduled)
    try:
        return asyncio.run(_initiate_call_async(candidate_id, expect_scheduled=expect_scheduled))
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

    # Voximplant signed record_url отвергает прямой запрос — нужно дописать
    # account_id+api_key в query. Это работает только server-side, отдавать
    # такой URL клиенту нельзя (утечка api_key).
    sep = "&" if "?" in url else "?"
    auth_url = (
        f"{url}{sep}account_id={settings.voximplant_account_id}"
        f"&api_key={settings.voximplant_api_key}"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(auth_url)
        resp.raise_for_status()
        mp3_bytes = resp.content

    yos_uri = upload_recording(call_db_id, mp3_bytes)

    async with _task_session() as db:
        call = await db.get(Call, call_db_id)
        if call is None:
            return None
        call.recording_url = yos_uri
        await db.commit()
    return yos_uri


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


