from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter()


@router.get("/{call_id}")
async def get_call(
    call_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get call details with transcript and score."""
    # TODO: query call + call_turns
    return {"call_id": call_id}


@router.get("/{call_id}/recording")
async def get_call_recording(call_id: int) -> dict:
    """Get signed URL for call recording."""
    # TODO: generate signed URL from Object Storage
    return {"call_id": call_id, "recording_url": None}
