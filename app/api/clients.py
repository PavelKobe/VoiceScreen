"""Admin endpoints for client provisioning."""

from __future__ import annotations

import secrets
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
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


class ClientOut(BaseModel):
    id: int
    name: str
    tariff: str
    active: bool
    created_at: datetime


@router.get(
    "",
    response_model=list[ClientOut],
    dependencies=[Depends(require_admin)],
)
async def list_clients(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[ClientOut]:
    result = await session.execute(select(Client).order_by(Client.id.desc()).limit(limit))
    clients = result.scalars().all()
    return [
        ClientOut(
            id=c.id,
            name=c.name,
            tariff=c.tariff,
            active=c.active,
            created_at=c.created_at,
        )
        for c in clients
    ]


class ApiKeyRotated(BaseModel):
    id: int
    api_key: str  # returned ONCE on rotation; previous key is invalidated immediately


@router.post(
    "/{client_id}/rotate-key",
    response_model=ApiKeyRotated,
    dependencies=[Depends(require_admin)],
)
async def rotate_client_api_key(
    client_id: int,
    session: AsyncSession = Depends(get_session),
) -> ApiKeyRotated:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    new_key = secrets.token_urlsafe(32)
    client.api_key = new_key
    await session.commit()

    log.info("client_api_key_rotated", client_id=client.id)
    return ApiKeyRotated(id=client.id, api_key=new_key)
