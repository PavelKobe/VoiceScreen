"""Admin endpoints for client provisioning."""

from __future__ import annotations

import secrets

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.models import Client
from app.db.session import get_session

router = APIRouter()
log = structlog.get_logger()


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tg_chat_id: str | None = Field(default=None, max_length=50)
    tariff: str = Field(default="start", max_length=50)


class ClientCreated(BaseModel):
    id: int
    name: str
    tariff: str
    api_key: str  # returned ONCE on creation


@router.post(
    "",
    response_model=ClientCreated,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
async def create_client(
    payload: ClientCreate,
    session: AsyncSession = Depends(get_session),
) -> ClientCreated:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    api_key = secrets.token_urlsafe(32)
    client = Client(
        name=name,
        tg_chat_id=payload.tg_chat_id,
        tariff=payload.tariff,
        api_key=api_key,
        active=True,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)

    log.info("client_created", client_id=client.id, name=client.name, tariff=client.tariff)
    return ClientCreated(id=client.id, name=client.name, tariff=client.tariff, api_key=api_key)
