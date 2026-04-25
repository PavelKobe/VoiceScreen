"""Vacancy CRUD scoped to the calling client."""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_client
from app.db.models import Client, Vacancy
from app.db.session import get_session

router = APIRouter()
log = structlog.get_logger()


class VacancyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    scenario_name: str = Field(..., min_length=1, max_length=100)
    pass_score: float = Field(default=6.0, ge=0.0, le=10.0)


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
    client: Client = Depends(get_current_client),
    session: AsyncSession = Depends(get_session),
) -> VacancyOut:
    vacancy = Vacancy(
        client_id=client.id,
        title=payload.title.strip(),
        scenario_name=payload.scenario_name.strip(),
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
    client: Client = Depends(get_current_client),
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
    client: Client = Depends(get_current_client),
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
