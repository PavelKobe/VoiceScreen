"""Vacancy CRUD scoped to the calling client."""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api._time import iso_utc
from app.api.deps import get_current_principal
from app.core.dispatch_window import (
    effective_max_attempts,
    schedule_next_attempt,
)
from app.core.scenario import available_scenarios
from app.db.models import Call, Candidate, Client, Vacancy
from app.db.session import get_session
from app.exports.xlsx import build_candidates_xlsx
from app.workers.tasks import initiate_call, schedule_sms_for_attempt

router = APIRouter()
log = structlog.get_logger()


_HHMM_RE = __import__("re").compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _validate_call_slots(value: list[str] | None) -> list[str] | None:
    """Проверка `["10:00","11:00",...]`: каждый — HH:MM, отсортированы по
    возрастанию, без дубликатов, длина 1..10. None — без кастомного графика.
    """
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("call_slots must be a list of HH:MM strings")
    if not (1 <= len(value) <= 10):
        raise ValueError("call_slots must contain 1 to 10 entries")
    for slot in value:
        if not isinstance(slot, str) or not _HHMM_RE.match(slot):
            raise ValueError(f"slot '{slot}' is not in HH:MM format (00:00–23:59)")
    if len(set(value)) != len(value):
        raise ValueError("call_slots must not contain duplicates")
    sorted_slots = sorted(value)
    if value != sorted_slots:
        raise ValueError("call_slots must be sorted ascending (e.g. 10:00, 11:00, 14:00)")
    return value


_NOTIFY_ON_ALLOWED = {"all", "pass_review", "pass_only", "off"}


def _validate_notify_on(value: str) -> str:
    if value not in _NOTIFY_ON_ALLOWED:
        raise ValueError(
            f"notify_on must be one of: {sorted(_NOTIFY_ON_ALLOWED)}"
        )
    return value


def _validate_notify_emails(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("notify_emails must be a list of email strings")
    if len(value) > 10:
        raise ValueError("notify_emails: не более 10 адресов")
    cleaned: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            raise ValueError("notify_emails: каждый адрес должен быть строкой")
        s = raw.strip()
        if not s:
            continue
        # Лёгкая проверка — pydantic EmailStr строже, но мы принимаем
        # уже отфильтрованный список из UI.
        if "@" not in s or "." not in s.split("@")[-1]:
            raise ValueError(f"некорректный email: {s}")
        cleaned.append(s)
    return cleaned or None


class VacancyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    scenario_name: str = Field(..., min_length=1, max_length=100)
    pass_score: float = Field(default=6.0, ge=0.0, le=10.0)
    call_slots: list[str] | None = None


class VacancyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    scenario_name: str | None = Field(default=None, min_length=1, max_length=100)
    pass_score: float | None = Field(default=None, ge=0.0, le=10.0)
    active: bool | None = None
    dispatch_paused: bool | None = None
    call_slots: list[str] | None = None
    notify_emails: list[str] | None = None
    notify_on: str | None = None
    sms_enabled: bool | None = None
    sms_template: str | None = None
    sms_lead_minutes: int | None = Field(default=None, ge=1, le=720)


async def _validate_scenario_name(name: str, client_id: int, session: AsyncSession) -> str:
    name = name.strip()
    allowed = await available_scenarios(client_id, session)
    if name not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"сценарий «{name}» не найден. Доступные: {allowed}",
        )
    return name


class VacancyOut(BaseModel):
    id: int
    client_id: int
    title: str
    scenario_name: str
    pass_score: float
    active: bool
    dispatch_paused: bool
    call_slots: list[str] | None = None
    notify_emails: list[str] | None = None
    notify_on: str = "pass_review"
    sms_enabled: bool = False
    sms_template: str | None = None
    sms_lead_minutes: int = 15
    created_at: datetime


def _to_vacancy_out(v: Vacancy) -> "VacancyOut":
    return VacancyOut(
        id=v.id,
        client_id=v.client_id,
        title=v.title,
        scenario_name=v.scenario_name,
        pass_score=v.pass_score,
        active=v.active,
        dispatch_paused=v.dispatch_paused,
        call_slots=v.call_slots,
        notify_emails=v.notify_emails,
        notify_on=v.notify_on,
        sms_enabled=v.sms_enabled,
        sms_template=v.sms_template,
        sms_lead_minutes=v.sms_lead_minutes,
        created_at=v.created_at,
    )


@router.post("", response_model=VacancyOut, status_code=201)
async def create_vacancy(
    payload: VacancyCreate,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> VacancyOut:
    scenario_slug = await _validate_scenario_name(
        payload.scenario_name, client.id, session
    )
    try:
        slots = _validate_call_slots(payload.call_slots)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    vacancy = Vacancy(
        client_id=client.id,
        title=payload.title.strip(),
        scenario_name=scenario_slug,
        pass_score=payload.pass_score,
        active=True,
        call_slots=slots,
    )
    session.add(vacancy)
    await session.commit()
    await session.refresh(vacancy)

    log.info(
        "vacancy_created",
        client_id=client.id,
        vacancy_id=vacancy.id,
        scenario_name=vacancy.scenario_name,
    )
    return _to_vacancy_out(vacancy)


@router.get("", response_model=list[VacancyOut])
async def list_vacancies(
    active: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[VacancyOut]:
    stmt = select(Vacancy).where(Vacancy.client_id == client.id)
    if active is not None:
        stmt = stmt.where(Vacancy.active == active)
    stmt = stmt.order_by(Vacancy.id.desc()).limit(limit)
    result = await session.execute(stmt)
    return [_to_vacancy_out(v) for v in result.scalars().all()]


@router.get("/{vacancy_id}", response_model=VacancyOut)
async def get_vacancy(
    vacancy_id: int,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> VacancyOut:
    vacancy = await session.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.client_id != client.id:
        raise HTTPException(status_code=404, detail="vacancy not found")
    return _to_vacancy_out(vacancy)


@router.patch("/{vacancy_id}", response_model=VacancyOut)
async def update_vacancy(
    vacancy_id: int,
    payload: VacancyUpdate,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> VacancyOut:
    vacancy = await session.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.client_id != client.id:
        raise HTTPException(status_code=404, detail="vacancy not found")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="no fields to update")

    if "title" in changes:
        vacancy.title = changes["title"].strip()
    if "scenario_name" in changes:
        vacancy.scenario_name = await _validate_scenario_name(
            changes["scenario_name"], client.id, session
        )
    if "pass_score" in changes:
        vacancy.pass_score = changes["pass_score"]
    if "active" in changes:
        vacancy.active = changes["active"]
    if "dispatch_paused" in changes:
        vacancy.dispatch_paused = changes["dispatch_paused"]
    if "call_slots" in changes:
        try:
            vacancy.call_slots = _validate_call_slots(changes["call_slots"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "notify_emails" in changes:
        try:
            vacancy.notify_emails = _validate_notify_emails(changes["notify_emails"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "notify_on" in changes:
        try:
            vacancy.notify_on = _validate_notify_on(changes["notify_on"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "sms_enabled" in changes:
        vacancy.sms_enabled = bool(changes["sms_enabled"])
    if "sms_template" in changes:
        tpl = changes["sms_template"]
        vacancy.sms_template = (tpl.strip() if isinstance(tpl, str) and tpl.strip() else None)
    if "sms_lead_minutes" in changes:
        vacancy.sms_lead_minutes = int(changes["sms_lead_minutes"])

    await session.commit()
    await session.refresh(vacancy)

    log.info(
        "vacancy_updated",
        client_id=client.id,
        vacancy_id=vacancy.id,
        fields=list(changes.keys()),
    )
    return _to_vacancy_out(vacancy)


@router.delete("/{vacancy_id}", status_code=204)
async def deactivate_vacancy(
    vacancy_id: int,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> Response:
    vacancy = await session.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.client_id != client.id:
        raise HTTPException(status_code=404, detail="vacancy not found")

    if vacancy.active:
        vacancy.active = False
        await session.commit()
        log.info("vacancy_deactivated", client_id=client.id, vacancy_id=vacancy.id)

    return Response(status_code=204)


class VacancyReport(BaseModel):
    vacancy_id: int
    title: str
    candidates_total: int
    calls_total: int           # звонки с finished_at
    calls_with_score: int      # из них с проставленным score
    by_decision: dict[str, int]
    avg_score: float | None    # усреднение по calls_with_score, либо null


@router.get("/{vacancy_id}/report", response_model=VacancyReport)
async def vacancy_report(
    vacancy_id: int,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> VacancyReport:
    vacancy = await session.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.client_id != client.id:
        raise HTTPException(status_code=404, detail="vacancy not found")

    candidates_total = (
        await session.execute(
            select(func.count(Candidate.id)).where(Candidate.vacancy_id == vacancy_id)
        )
    ).scalar_one()

    calls_q = (
        select(Call)
        .join(Candidate, Call.candidate_id == Candidate.id)
        .where(Candidate.vacancy_id == vacancy_id)
    )

    calls_total = (
        await session.execute(
            select(func.count()).select_from(calls_q.where(Call.finished_at.is_not(None)).subquery())
        )
    ).scalar_one()

    scored_q = calls_q.where(Call.score.is_not(None))
    calls_with_score = (
        await session.execute(select(func.count()).select_from(scored_q.subquery()))
    ).scalar_one()

    avg_score_raw = (
        await session.execute(
            select(func.avg(Call.score))
            .join(Candidate, Call.candidate_id == Candidate.id)
            .where(Candidate.vacancy_id == vacancy_id, Call.score.is_not(None))
        )
    ).scalar_one()
    avg_score = round(float(avg_score_raw), 2) if avg_score_raw is not None else None

    decision_rows = (
        await session.execute(
            select(Call.decision, func.count())
            .join(Candidate, Call.candidate_id == Candidate.id)
            .where(Candidate.vacancy_id == vacancy_id, Call.decision.is_not(None))
            .group_by(Call.decision)
        )
    ).all()
    by_decision = {decision: count for decision, count in decision_rows}

    return VacancyReport(
        vacancy_id=vacancy.id,
        title=vacancy.title,
        candidates_total=candidates_total,
        calls_total=calls_total,
        calls_with_score=calls_with_score,
        by_decision=by_decision,
        avg_score=avg_score,
    )


class DispatchResult(BaseModel):
    vacancy_id: int
    enqueued: int
    skipped_already_called: int
    skipped_archived: int
    deferred_to: str | None = None


@router.post("/{vacancy_id}/dispatch", response_model=DispatchResult, status_code=202)
async def dispatch_vacancy(
    vacancy_id: int,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> DispatchResult:
    """Массовый запуск обзвона: ставит в очередь всех активных кандидатов
    вакансии, у которых ещё не было звонка.
    """
    vacancy = await session.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.client_id != client.id:
        raise HTTPException(status_code=404, detail="vacancy not found")
    if not vacancy.active:
        raise HTTPException(status_code=400, detail="вакансия не активна")
    if vacancy.dispatch_paused:
        raise HTTPException(
            status_code=409,
            detail="обзвон по вакансии приостановлен — снимите паузу, чтобы запустить",
        )

    cand_rows = (
        await session.execute(
            select(Candidate).where(Candidate.vacancy_id == vacancy_id)
        )
    ).scalars().all()

    # Кандидаты с финальным результатом (pass/reject/review) или статусом
    # done/exhausted в bulk не попадают. Кандидат с одним только not_reached
    # звонком и attempts_count<max — попадёт (это его вторая/третья попытка).
    finalized_rows = (
        await session.execute(
            select(Call.candidate_id)
            .join(Candidate, Call.candidate_id == Candidate.id)
            .where(
                Candidate.vacancy_id == vacancy_id,
                Call.decision.in_(("pass", "reject", "review")),
            )
            .distinct()
        )
    ).scalars().all()
    finalized_set = set(finalized_rows)

    now = datetime.utcnow()
    # Eta зависит от настроек вакансии: если call_slots задан — первая
    # попытка идёт в slots[0], иначе — в ближайший момент окна.
    eta = schedule_next_attempt(vacancy.call_slots, attempts_count=0, after_utc=now)
    if eta is None:
        # Может произойти только если call_slots=[] (пустой список) — это
        # валидно как «не звонить вообще», но bulk при этом пуст.
        raise HTTPException(
            status_code=400,
            detail="у вакансии не задано ни одного слота обзвона",
        )
    deferred = eta > now
    max_attempts = effective_max_attempts(vacancy.call_slots)

    enqueued = 0
    skipped_called = 0
    skipped_archived = 0
    for c in cand_rows:
        if not c.active:
            skipped_archived += 1
            continue
        if c.status in ("exhausted", "done", "in_progress"):
            # Звонок уже идёт или кандидат закрыт — пропускаем.
            skipped_called += 1
            continue
        if c.next_attempt_at is not None:
            # Уже стоит запланированная задача (от прошлого нажатия или
            # retry-цикла). Защищает от двойных нажатий bulk-кнопки.
            skipped_called += 1
            continue
        if c.id in finalized_set:
            skipped_called += 1
            continue
        if c.attempts_count >= max_attempts:
            skipped_called += 1
            continue
        initiate_call.apply_async(
            args=[c.id], kwargs={"expect_scheduled": True}, eta=eta,
        )
        schedule_sms_for_attempt(candidate_id=c.id, vacancy=vacancy, eta=eta)
        c.next_attempt_at = eta
        enqueued += 1

    if enqueued > 0:
        await session.commit()

    log.info(
        "vacancy_dispatched",
        client_id=client.id,
        vacancy_id=vacancy_id,
        enqueued=enqueued,
        skipped_already_called=skipped_called,
        skipped_archived=skipped_archived,
        deferred=deferred,
    )
    return DispatchResult(
        vacancy_id=vacancy_id,
        enqueued=enqueued,
        skipped_already_called=skipped_called,
        skipped_archived=skipped_archived,
        deferred_to=iso_utc(eta) if deferred else None,
    )


@router.get("/{vacancy_id}/export.xlsx")
async def export_candidates_xlsx(
    vacancy_id: int,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> FastAPIResponse:
    """Excel-выгрузка кандидатов вакансии: один кандидат — одна строка,
    данные дополнены последним звонком (score/decision/summary/recording).
    """
    vacancy = await session.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.client_id != client.id:
        raise HTTPException(status_code=404, detail="vacancy not found")

    cand_rows = (
        await session.execute(
            select(Candidate)
            .options(selectinload(Candidate.calls))
            .where(Candidate.vacancy_id == vacancy_id)
            .order_by(Candidate.id.asc())
        )
    ).scalars().all()

    rows: list[dict] = []
    for c in cand_rows:
        last = max(
            (call for call in c.calls if call.started_at is not None),
            key=lambda x: x.started_at,
            default=None,
        )
        recording_ext = None
        call_card_url = None
        if last is not None:
            # Прямая ссылка на нашу прокси-ручку записи (требует cookie-auth).
            if last.recording_url:
                recording_ext = f"https://voxscreen.ru/api/v1/calls/{last.id}/recording"
            call_card_url = f"https://app.voxscreen.ru/calls/{last.id}"
        rows.append({
            "fio": c.fio,
            "phone": c.phone,
            "source": c.source,
            "status": c.status,
            "attempts_count": c.attempts_count,
            "last_started_at": last.started_at if last else None,
            "last_duration": last.duration if last else None,
            "last_score": last.score if last else None,
            "last_decision": last.decision if last else None,
            "last_reasoning": last.score_reasoning if last else None,
            "last_summary": last.summary if last else None,
            "recording_url": recording_ext,
            "call_card_url": call_card_url,
        })

    body = build_candidates_xlsx(rows)
    # ASCII-fallback (для старых клиентов) + UTF-8 версия по RFC 5987 для
    # кириллических названий вакансий. Без filename*=UTF-8'' Starlette
    # пытается закодировать имя файла в latin-1 и падает на кириллице.
    from urllib.parse import quote
    ascii_title = "".join(
        ch if (ch.isascii() and (ch.isalnum() or ch in "-_."))
        else "_" for ch in vacancy.title
    )[:60].strip("_") or "vacancy"
    ascii_filename = f"candidates_{vacancy.id}_{ascii_title}.xlsx"
    utf8_filename = f"candidates_{vacancy.id}_{vacancy.title}.xlsx"
    encoded_utf8 = quote(utf8_filename, safe="")

    log.info(
        "vacancy_exported_xlsx",
        client_id=client.id,
        vacancy_id=vacancy.id,
        rows=len(rows),
    )
    return FastAPIResponse(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_filename}"; '
                f"filename*=UTF-8''{encoded_utf8}"
            ),
            "Cache-Control": "no-store",
        },
    )
