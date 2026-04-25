"""HTTP API for viewing screening call results."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_client
from app.db.models import Call, Candidate, Client, Vacancy
from app.db.session import get_session

router = APIRouter()


def _serialize_call(call: Call, include_turns: bool = False) -> dict:
    data = {
        "id": call.id,
        "candidate_id": call.candidate_id,
        "voximplant_call_id": call.voximplant_call_id,
        "started_at": call.started_at.isoformat() if call.started_at else None,
        "finished_at": call.finished_at.isoformat() if call.finished_at else None,
        "duration": call.duration,
        "score": call.score,
        "decision": call.decision,
        "score_reasoning": call.score_reasoning,
        "answers": call.answers,
        "attempt": call.attempt,
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
    client: Client = Depends(get_current_client),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List calls (newest first) for the calling client; optional candidate_id filter."""
    stmt = _scoped_call_stmt(client.id).order_by(Call.id.desc()).limit(limit).offset(offset)
    if candidate_id is not None:
        stmt = stmt.where(Call.candidate_id == candidate_id)
    result = await session.execute(stmt)
    calls = result.scalars().all()
    return {"items": [_serialize_call(c) for c in calls], "limit": limit, "offset": offset}


@router.get("/{call_id}")
async def get_call(
    call_id: int,
    client: Client = Depends(get_current_client),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get call details including all turns and transcript."""
    stmt = (
        _scoped_call_stmt(client.id)
        .options(selectinload(Call.turns))
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
    client: Client = Depends(get_current_client),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return recording URL (stub — S3 signed URLs are a TODO)."""
    stmt = _scoped_call_stmt(client.id).where(Call.id == call_id)
    result = await session.execute(stmt)
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail="call not found")
    return {"call_id": call_id, "recording_url": call.recording_url}
