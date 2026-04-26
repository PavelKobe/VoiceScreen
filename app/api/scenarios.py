"""CRUD сценариев скрининга. Каждый клиент управляет своими."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_principal
from app.core.scenario import list_templates, load_template_yaml
from app.db.models import Client, Scenario
from app.db.session import get_session

router = APIRouter()
log = structlog.get_logger()

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,98}[a-z0-9]$")


class Question(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    type: Literal["open", "confirm", "choice"] = "open"
    options: list[str] | None = None


class ScenarioCreate(BaseModel):
    slug: str = Field(..., min_length=3, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    agent_role: str = Field(default="HR-помощник", max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    vacancy_title: str = Field(..., min_length=1, max_length=255)
    questions: list[Question] = Field(default_factory=list)


class ScenarioUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    agent_role: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    vacancy_title: str | None = Field(default=None, min_length=1, max_length=255)
    questions: list[Question] | None = None
    active: bool | None = None


class ScenarioBrief(BaseModel):
    id: int
    slug: str
    title: str
    company_name: str
    vacancy_title: str
    active: bool
    questions_count: int
    updated_at: datetime


class ScenarioOut(BaseModel):
    id: int
    slug: str
    title: str
    agent_role: str
    company_name: str
    vacancy_title: str
    questions: list[Question]
    active: bool
    created_at: datetime
    updated_at: datetime


class TemplateBrief(BaseModel):
    slug: str
    title: str
    company_name: str
    questions_count: int


def _validate_slug(slug: str) -> str:
    s = slug.strip().lower()
    if not SLUG_RE.match(s):
        raise HTTPException(
            status_code=400,
            detail="slug: только латиница, цифры, дефис и подчёркивание (3–100 символов)",
        )
    return s


def _validate_questions(questions: list[Question]) -> list[dict]:
    out: list[dict] = []
    for q in questions:
        if q.type == "choice":
            if not q.options or not all(o.strip() for o in q.options):
                raise HTTPException(
                    status_code=400,
                    detail=f"вопрос «{q.text}»: для типа choice нужно минимум один вариант",
                )
        out.append(q.model_dump())
    return out


def _to_out(s: Scenario) -> ScenarioOut:
    return ScenarioOut(
        id=s.id,
        slug=s.slug,
        title=s.title,
        agent_role=s.agent_role,
        company_name=s.company_name,
        vacancy_title=s.vacancy_title,
        questions=[Question(**q) for q in (s.questions or [])],
        active=s.active,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("/templates", response_model=list[TemplateBrief])
async def get_templates() -> list[TemplateBrief]:
    """Системные шаблоны (YAML в репе) — основа для нового сценария."""
    return [TemplateBrief(**t) for t in list_templates()]


@router.get("/templates/{slug}", response_model=ScenarioCreate)
async def get_template_detail(slug: str) -> ScenarioCreate:
    """Полный шаблон, чтобы UI предзаполнил форму при создании из шаблона."""
    data = load_template_yaml(slug)
    if data is None:
        raise HTTPException(status_code=404, detail="шаблон не найден")
    return ScenarioCreate(
        slug=slug,
        title=data.get("vacancy_title", slug),
        agent_role=data.get("agent_role", "HR-помощник"),
        company_name=data.get("company_name", ""),
        vacancy_title=data.get("vacancy_title", ""),
        questions=[Question(**q) for q in (data.get("questions") or [])],
    )


@router.get("", response_model=list[ScenarioBrief])
async def list_scenarios(
    active: bool | None = Query(default=None),
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[ScenarioBrief]:
    stmt = select(Scenario).where(Scenario.client_id == client.id)
    if active is not None:
        stmt = stmt.where(Scenario.active == active)
    stmt = stmt.order_by(Scenario.id.desc())
    rows = (await session.execute(stmt)).scalars().all()
    return [
        ScenarioBrief(
            id=s.id,
            slug=s.slug,
            title=s.title,
            company_name=s.company_name,
            vacancy_title=s.vacancy_title,
            active=s.active,
            questions_count=len(s.questions or []),
            updated_at=s.updated_at,
        )
        for s in rows
    ]


@router.get("/{slug}", response_model=ScenarioOut)
async def get_scenario(
    slug: str,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ScenarioOut:
    row = await session.execute(
        select(Scenario).where(Scenario.client_id == client.id, Scenario.slug == slug)
    )
    scenario = row.scalar_one_or_none()
    if scenario is None:
        raise HTTPException(status_code=404, detail="сценарий не найден")
    return _to_out(scenario)


@router.post("", response_model=ScenarioOut, status_code=201)
async def create_scenario(
    payload: ScenarioCreate,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ScenarioOut:
    slug = _validate_slug(payload.slug)
    questions = _validate_questions(payload.questions)

    scenario = Scenario(
        client_id=client.id,
        slug=slug,
        title=payload.title.strip(),
        agent_role=payload.agent_role.strip(),
        company_name=payload.company_name.strip(),
        vacancy_title=payload.vacancy_title.strip(),
        questions=questions,
        active=True,
    )
    session.add(scenario)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="сценарий с таким slug уже есть") from None
    await session.refresh(scenario)

    log.info("scenario_created", client_id=client.id, scenario_id=scenario.id, slug=slug)
    return _to_out(scenario)


@router.patch("/{slug}", response_model=ScenarioOut)
async def update_scenario(
    slug: str,
    payload: ScenarioUpdate,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ScenarioOut:
    row = await session.execute(
        select(Scenario).where(Scenario.client_id == client.id, Scenario.slug == slug)
    )
    scenario = row.scalar_one_or_none()
    if scenario is None:
        raise HTTPException(status_code=404, detail="сценарий не найден")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="нет полей для обновления")

    if "title" in changes:
        scenario.title = changes["title"].strip()
    if "agent_role" in changes:
        scenario.agent_role = changes["agent_role"].strip()
    if "company_name" in changes:
        scenario.company_name = changes["company_name"].strip()
    if "vacancy_title" in changes:
        scenario.vacancy_title = changes["vacancy_title"].strip()
    if "questions" in changes:
        scenario.questions = _validate_questions(
            [Question(**q) for q in changes["questions"]]
        )
    if "active" in changes:
        scenario.active = changes["active"]

    await session.commit()
    await session.refresh(scenario)

    log.info(
        "scenario_updated",
        client_id=client.id,
        scenario_id=scenario.id,
        fields=list(changes.keys()),
    )
    return _to_out(scenario)
