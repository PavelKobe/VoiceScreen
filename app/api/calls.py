"""HTTP API for viewing screening call results."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api._time import iso_utc
from app.api.deps import get_current_principal
from app.db.models import Call, Candidate, Client, Vacancy
from app.db.session import get_session
from app.storage.yos import YOS_PREFIX, presign_recording

router = APIRouter()


def _serialize_call(call: Call, include_turns: bool = False) -> dict:
    candidate = call.candidate
    data = {
        "id": call.id,
        "candidate_id": call.candidate_id,
        "candidate": {
            "id": candidate.id,
            "fio": candidate.fio,
            "phone": candidate.phone,
            "vacancy_id": candidate.vacancy_id,
        }
        if candidate is not None
        else None,
        "voximplant_call_id": call.voximplant_call_id,
        "started_at": iso_utc(call.started_at),
        "finished_at": iso_utc(call.finished_at),
        "duration": call.duration,
        "score": call.score,
        "decision": call.decision,
        "score_reasoning": call.score_reasoning,
        "answers": call.answers,
        "attempt": call.attempt,
        "has_recording": call.recording_url is not None
        and call.recording_url.startswith(YOS_PREFIX),
    }
    if include_turns:
        data["turns"] = [
            {"order": t.order, "speaker": t.speaker, "text": t.text}
            for t in sorted(call.turns, key=lambda x: x.order)
        ]
        data["transcript"] = call.transcript
    return data


def _scoped_call_stmt(client_id: int):
    """Base SELECT for Call rows owned by the given client (via candidate→vacancy)."""
    return (
        select(Call)
        .join(Candidate, Call.candidate_id == Candidate.id)
        .join(Vacancy, Candidate.vacancy_id == Vacancy.id)
        .where(Vacancy.client_id == client_id)
    )


@router.get("")
async def list_calls(
    limit: int = 20,
    offset: int = 0,
    candidate_id: int | None = None,
    vacancy_id: int | None = None,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List calls (newest first) for the calling client.

    Поддерживает фильтры candidate_id и vacancy_id (взаимодополняющие).
    """
    stmt = (
        _scoped_call_stmt(client.id)
        .options(selectinload(Call.candidate))
        .order_by(Call.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if candidate_id is not None:
        stmt = stmt.where(Call.candidate_id == candidate_id)
    if vacancy_id is not None:
        stmt = stmt.where(Candidate.vacancy_id == vacancy_id)
    result = await session.execute(stmt)
    calls = result.scalars().all()
    return {"items": [_serialize_call(c) for c in calls], "limit": limit, "offset": offset}


@router.get("/{call_id}")
async def get_call(
    call_id: int,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get call details including all turns and transcript."""
    stmt = (
        _scoped_call_stmt(client.id)
        .options(selectinload(Call.turns), selectinload(Call.candidate))
        .where(Call.id == call_id)
    )
    result = await session.execute(stmt)
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail="call not found")
    return _serialize_call(call, include_turns=True)


@router.get("/{call_id}/recording")
async def get_call_recording(
    call_id: int,
    client: Client = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Стримит mp3 записи звонка через бэкенд (без CORS-проблем).

    Раньше был редирект на presign URL Yandex Object Storage, но
    `<audio src>` тэг это переваривал, а wavesurfer.js (партия B)
    использует fetch — на YOS нет CORS-заголовков, и браузер блокировал.
    Server-side прокси решает это: клиент видит only-our-origin URL.
    """
    stmt = _scoped_call_stmt(client.id).where(Call.id == call_id)
    result = await session.execute(stmt)
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail="call not found")
    if not call.recording_url:
        raise HTTPException(status_code=404, detail="recording not ready")
    if not call.recording_url.startswith(YOS_PREFIX):
        raise HTTPException(
            status_code=410,
            detail="recording stored in legacy format; re-upload required",
        )

    signed = presign_recording(call.recording_url, expires_seconds=3600)

    async def stream() -> "AsyncIterator[bytes]":  # noqa: F821
        async with httpx.AsyncClient(timeout=60) as http:
            async with http.stream("GET", signed) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                    yield chunk

    return StreamingResponse(
        stream(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": f'inline; filename="call-{call_id}.mp3"',
        },
    )
