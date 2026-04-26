"""Vacancy CRUD scoped to the calling client."""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_principal
from app.core.scenario import available_scenarios
from app.db.models import Call, Candidate, Client, Vacancy
from app.db.session import get_session

router = APIRouter()
log = structlog.get_logger()


class VacancyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    scenario_name: str = Field(..., min_length=1, max_length=100)
    pass_score: float = Field(default=6.0, ge=0.0, le=10.0)


class VacancyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    scenario_name: str | None = Field(default=None, min_length=1, max_length=100)
    pass_score: float | None = Field(default=None, ge=0.0, le=10.0)
    active: bool | None = None


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
    created_at: datetime


@router.post("", response_model=VacancyOut, status_code=201)
async def create_vacancy(
    payload: VacancyCreate,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> VacancyOut:
    scenario_slug = await _validate_scenario_name(
        payload.scenario_name, client.id, session
    )
    vacancy = Vacancy(
        client_id=client.id,
        title=payload.title.strip(),
        scenario_name=scenario_slug,
        pass_score=payload.pass_score,
        active=True,
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
    return VacancyOut(
        id=vacancy.id,
        client_id=vacancy.client_id,
        title=vacancy.title,
        scenario_name=vacancy.scenario_name,
        pass_score=vacancy.pass_score,
        active=vacancy.active,
        created_at=vacancy.created_at,
    )


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
    return [
        VacancyOut(
            id=v.id,
            client_id=v.client_id,
            title=v.title,
            scenario_name=v.scenario_name,
            pass_score=v.pass_score,
            active=v.active,
            created_at=v.created_at,
        )
        for v in result.scalars().all()
    ]


@router.get("/{vacancy_id}", response_model=VacancyOut)
async def get_vacancy(
    vacancy_id: int,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> VacancyOut:
    vacancy = await session.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.client_id != client.id:
        raise HTTPException(status_code=404, detail="vacancy not found")
    return VacancyOut(
        id=vacancy.id,
        client_id=vacancy.client_id,
        title=vacancy.title,
        scenario_name=vacancy.scenario_name,
        pass_score=vacancy.pass_score,
        active=vacancy.active,
        created_at=vacancy.created_at,
    )


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

    await session.commit()
    await session.refresh(vacancy)

    log.info(
        "vacancy_updated",
        client_id=client.id,
        vacancy_id=vacancy.id,
        fields=list(changes.keys()),
    )
    return VacancyOut(
        id=vacancy.id,
        client_id=vacancy.client_id,
        title=vacancy.title,
        scenario_name=vacancy.scenario_name,
        pass_score=vacancy.pass_score,
        active=vacancy.active,
        created_at=vacancy.created_at,
    )


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
