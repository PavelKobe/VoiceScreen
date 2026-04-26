"""Admin endpoints для управления пользователями клиента."""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import hash_password
from app.api.deps import require_admin
from app.db.models import Client, User
from app.db.session import get_session

router = APIRouter()
log = structlog.get_logger()


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="client_admin", max_length=30)


class UserOut(BaseModel):
    id: int
    client_id: int
    email: str
    role: str
    active: bool
    created_at: datetime


@router.post(
    "",
    response_model=UserOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
async def create_user(
    client_id: int,
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    user = User(
        client_id=client_id,
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
        raise HTTPException(status_code=409, detail="email already exists") from None
    await session.refresh(user)

    log.info("user_created", user_id=user.id, client_id=client_id, email=user.email)
    return UserOut(
        id=user.id,
        client_id=user.client_id,
        email=user.email,
        role=user.role,
        active=user.active,
        created_at=user.created_at,
    )


@router.get(
    "",
    response_model=list[UserOut],
    dependencies=[Depends(require_admin)],
)
async def list_users(
    client_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[UserOut]:
    result = await session.execute(
        select(User)
        .where(User.client_id == client_id)
        .order_by(User.id.desc())
        .limit(limit)
    )
    users = result.scalars().all()
    return [
        UserOut(
            id=u.id,
            client_id=u.client_id,
            email=u.email,
            role=u.role,
            active=u.active,
            created_at=u.created_at,
        )
        for u in users
    ]
