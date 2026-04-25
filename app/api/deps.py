"""Shared FastAPI dependencies (auth, etc.)."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Client
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
