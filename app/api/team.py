"""Self-service управление командой клиента: текущий юзер видит/приглашает коллег."""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import hash_password
from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_session

router = APIRouter()
log = structlog.get_logger()


class TeammateInvite(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="client_admin", max_length=30)


class TeammateOut(BaseModel):
    id: int
    email: str
    role: str
    active: bool
    created_at: datetime


@router.get("", response_model=list[TeammateOut])
async def list_teammates(
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TeammateOut]:
    """Список пользователей того же клиента, что и текущий юзер."""
    rows = await session.execute(
        select(User).where(User.client_id == current.client_id).order_by(User.id.desc())
    )
    return [
        TeammateOut(
            id=u.id,
            email=u.email,
            role=u.role,
            active=u.active,
            created_at=u.created_at,
        )
        for u in rows.scalars().all()
    ]


@router.post("", response_model=TeammateOut, status_code=201)
async def invite_teammate(
    payload: TeammateInvite,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TeammateOut:
    """Пригласить коллегу в свой клиент.

    Доступно только пользователям с ролью `client_admin`.
    """
    if current.role != "client_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="недостаточно прав для приглашения",
        )

    user = User(
        client_id=current.client_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        active=True,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="email уже занят") from None
    await session.refresh(user)

    log.info(
        "teammate_invited",
        invited_by=current.id,
        new_user_id=user.id,
        client_id=current.client_id,
    )
    return TeammateOut(
        id=user.id,
        email=user.email,
        role=user.role,
        active=user.active,
        created_at=user.created_at,
    )
