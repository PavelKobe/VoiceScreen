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
from datetime import datetime

import httpx
import structlog
from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.scenario import load_scenario
from app.db.models import Call, Candidate, Vacancy
from app.notifications.email import send_email
from app.notifications.sms import send_sms
from app.notifications.templates import (
    render_call_result_email,
    render_sms_before_call,
)
from app.storage.yos import YOS_PREFIX, presign_recording, upload_recording
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
        # Гейт строго на status == 'pending'. Это закрывает гонку, которая
        # пропускала параллельные задачи: после первого UPDATE строка
        # становится in_progress, и второй UPDATE при переоценке WHERE на
        # свежем состоянии увидит status != 'pending' и обновит 0 строк.
        # webhook /call_failed и /reset_attempts перед своим retry'ем
        # явно ставят status='pending', так что retry-цикл проходит.
        conditions = [
            Candidate.id == candidate_id,
            Candidate.active.is_(True),
            Candidate.status == "pending",
            Candidate.attempts_count < settings.call_max_attempts,
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


def schedule_sms_for_attempt(
    *,
    candidate_id: int,
    vacancy: Vacancy,
    eta: datetime,
) -> None:
    """Поставить SMS-предупреждение за `vacancy.sms_lead_minutes` до eta.

    No-op, если у вакансии sms_enabled=False, или если SMS пришлось бы
    отправлять «в прошлом» (звонок уже скоро — успеть оповестить нет смысла).
    Безопасно вызывать в любой точке, где планируется звонок.
    """
    from datetime import timedelta

    if not vacancy.sms_enabled:
        return
    sms_eta = eta - timedelta(minutes=vacancy.sms_lead_minutes)
    now = datetime.utcnow()
    # Если до звонка меньше минуты — SMS уже не успеет/не имеет смысла.
    if sms_eta <= now + timedelta(seconds=30):
        return
    send_sms_before_call.apply_async(
        args=[candidate_id, eta.isoformat()],
        eta=sms_eta,
    )


# --- HR-уведомления и SMS ----------------------------------------------------

async def _send_call_result_email_async(call_db_id: int) -> dict:
    async with _task_session() as db:
        call = (
            await db.execute(
                select(Call)
                .options(selectinload(Call.candidate))
                .where(Call.id == call_db_id)
            )
        ).scalar_one_or_none()
        if call is None or call.candidate is None:
            return {"call_id": call_db_id, "status": "skipped_missing"}
        candidate = call.candidate
        vacancy = await db.get(Vacancy, candidate.vacancy_id)
        if vacancy is None:
            return {"call_id": call_db_id, "status": "skipped_no_vacancy"}

        notify_on = vacancy.notify_on or "pass_review"
        recipients = list(vacancy.notify_emails or [])
        decision = call.decision
        if not recipients or notify_on == "off":
            return {"call_id": call_db_id, "status": "skipped_off"}
        # Фильтр по политике уведомлений.
        if notify_on == "pass_only" and decision != "pass":
            return {"call_id": call_db_id, "status": "skipped_policy"}
        if notify_on == "pass_review" and decision not in ("pass", "review"):
            return {"call_id": call_db_id, "status": "skipped_policy"}

        recording_url: str | None = None
        if call.recording_url and call.recording_url.startswith(YOS_PREFIX):
            try:
                # Подписанная ссылка на 7 дней — HR удобно открыть из почты.
                recording_url = presign_recording(
                    call.recording_url, expires_seconds=7 * 24 * 3600,
                )
            except Exception as exc:
                log.warning("email_recording_presign_failed", call_id=call_db_id, error=str(exc))

        call_card_url = f"{settings.web_app_base_url.rstrip('/')}/calls/{call.id}"

        subject, text_body, html_body = render_call_result_email(
            fio=candidate.fio,
            phone=candidate.phone,
            vacancy_title=vacancy.title,
            decision=decision,
            score=call.score,
            reasoning=call.score_reasoning,
            summary=call.summary,
            recording_url=recording_url,
            call_card_url=call_card_url,
        )

    await send_email(recipients, subject, text_body, html=html_body)
    return {
        "call_id": call_db_id,
        "status": "sent",
        "recipients": len(recipients),
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_call_result_email(self, call_db_id: int) -> dict:
    """Отправить HR письмо с итогом скрининг-звонка.

    Решение об отправке — внутри (политика notify_on/notify_emails в Vacancy).
    Так HR может выключить уведомления для конкретной вакансии без правок
    в каллере.
    """
    log.info("task_send_call_result_email", call_db_id=call_db_id)
    try:
        return asyncio.run(_send_call_result_email_async(call_db_id))
    except Exception as exc:
        log.exception("task_send_call_result_email_failed", call_db_id=call_db_id, error=str(exc))
        raise self.retry(exc=exc)


async def _send_sms_before_call_async(
    candidate_id: int,
    expected_iso: str,
) -> dict:
    """Идемпотентный гейт: SMS уходит, только если у кандидата всё ещё
    запланирован звонок именно на ожидаемое время. Если HR обнулил
    next_attempt_at или попытка уже отстрелялась — задача no-op.
    """
    expected = datetime.fromisoformat(expected_iso)

    async with _task_session() as db:
        cand = await db.get(Candidate, candidate_id)
        if cand is None or not cand.active:
            return {"candidate_id": candidate_id, "status": "skipped_inactive"}
        if cand.next_attempt_at is None:
            return {"candidate_id": candidate_id, "status": "skipped_no_eta"}
        # Допускаем рассинхрон в пределах минуты — Celery eta может «дрожать».
        delta = abs((cand.next_attempt_at - expected).total_seconds())
        if delta > 60:
            return {"candidate_id": candidate_id, "status": "skipped_rescheduled"}

        vacancy = await db.get(Vacancy, cand.vacancy_id)
        if vacancy is None or not vacancy.sms_enabled:
            return {"candidate_id": candidate_id, "status": "skipped_disabled"}

        # company_name берём из сценария вакансии (lazy-seed из YAML, как ws.py).
        try:
            scenario = await load_scenario(vacancy.scenario_name, vacancy.client_id, db)
        except FileNotFoundError:
            scenario = {}
        company = (scenario.get("company_name") or "").strip() or "компания"

        text = render_sms_before_call(
            vacancy.sms_template,
            fio=cand.fio,
            minutes=vacancy.sms_lead_minutes,
            company=company,
            vacancy=vacancy.title,
        )
        phone = cand.phone

    result = await send_sms(phone, text)

    # Помечаем последнюю pending-попытку отправки SMS на этом кандидате —
    # для отчётности через Call.sms_sent_at. Но Call ещё не создан (он
    # рождается в момент start), поэтому пишем ничего — просто логируем.
    log.info(
        "sms_before_call_sent",
        candidate_id=candidate_id,
        phone=phone,
        sms_status=result.get("status"),
    )
    return {"candidate_id": candidate_id, "status": "sent"}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def send_sms_before_call(self, candidate_id: int, expected_iso: str) -> dict:
    """SMS-предупреждение кандидату за N минут до звонка."""
    log.info("task_send_sms_before_call", candidate_id=candidate_id)
    try:
        return asyncio.run(_send_sms_before_call_async(candidate_id, expected_iso))
    except Exception as exc:
        log.exception("task_send_sms_before_call_failed", candidate_id=candidate_id, error=str(exc))
        raise self.retry(exc=exc)


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


