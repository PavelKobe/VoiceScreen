"""Shared FastAPI dependencies (auth, etc.)."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Client, User
from app.db.session import get_session


async def get_current_client(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> Client:
    """Resolve the calling Client from X-API-Key header.

    Raises 401 if header missing/empty, 403 if key unknown or client inactive.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing X-API-Key header",
        )
    result = await session.execute(select(Client).where(Client.api_key == x_api_key))
    client = result.scalar_one_or_none()
    if client is None or not client.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid api key",
        )
    return client


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the calling User from session cookie.

    Raises 401 if нет валидной session, 403 если юзер деактивирован.
    """
    user_id = request.session.get("user_id") if hasattr(request, "session") else None
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
        )
    user = await session.get(User, user_id)
    if user is None or not user.active:
        # Чистим протухшую/невалидную сессию.
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user inactive or not found",
        )
    return user


async def get_current_principal(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> Client:
    """Resolve calling Client either via session-cookie или X-API-Key.

    Cookie имеет приоритет — если в session есть user_id, грузим его клиента.
    Иначе fallback на X-API-Key. Если ни того, ни другого нет — 401.
    """
    user_id = request.session.get("user_id") if hasattr(request, "session") else None
    if user_id:
        user = await session.get(User, user_id)
        if user is None or not user.active:
            request.session.clear()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="user inactive or not found",
            )
        client = await session.get(Client, user.client_id)
        if client is None or not client.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="client inactive",
            )
        return client

    return await get_current_client(x_api_key=x_api_key, session=session)


def require_admin(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    """Require the master admin key for provisioning endpoints."""
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="admin endpoints disabled (ADMIN_API_KEY not configured)",
        )
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid admin key",
        )
