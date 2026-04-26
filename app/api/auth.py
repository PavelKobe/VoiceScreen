"""Session-based auth для веб-кабинета (SPA на app.voxscreen.ru)."""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Client, User
from app.db.session import get_session

router = APIRouter()
log = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    active: bool
    client_id: int
    created_at: datetime


class ClientBrief(BaseModel):
    id: int
    name: str
    tariff: str
    active: bool


class MeOut(BaseModel):
    user: UserOut
    client: ClientBrief


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginPayload,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    request.session["user_id"] = user.id
    request.session["client_id"] = user.client_id

    log.info("user_login", user_id=user.id, client_id=user.client_id)
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        active=user.active,
        client_id=user.client_id,
        created_at=user.created_at,
    )


@router.post("/logout", status_code=204)
async def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@router.get("/me", response_model=MeOut)
async def me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MeOut:
    client = await session.get(Client, user.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    return MeOut(
        user=UserOut(
            id=user.id,
            email=user.email,
            role=user.role,
            active=user.active,
            client_id=user.client_id,
            created_at=user.created_at,
        ),
        client=ClientBrief(
            id=client.id,
            name=client.name,
            tariff=client.tariff,
            active=client.active,
        ),
    )
