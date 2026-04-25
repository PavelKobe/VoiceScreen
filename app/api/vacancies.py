"""Vacancy CRUD scoped to the calling client."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
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
    )
