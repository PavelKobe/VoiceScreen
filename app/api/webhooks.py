import structlog
from fastapi import APIRouter, Request

router = APIRouter()
log = structlog.get_logger()


@router.post("/voximplant/call-event")
async def voximplant_call_event(request: Request) -> dict:
    """Webhook from Voximplant on call state changes (HTTP from VoxEngine)."""
    body = await request.json()
    log.info("voximplant_call_event", payload=body)
    # TODO: handle call state transitions (ringing, connected, completed)
    return {"status": "ok"}


@router.post("/voximplant/media-stream")
async def voximplant_media_stream(request: Request) -> dict:
    """HTTP fallback for media-stream metadata.

    The actual audio stream is handled via a WebSocket endpoint opened by the
    VoxEngine screening.js scenario — see app/api/ws.py (TODO).
    """
    # TODO: receive audio chunks, pipe to STT
    return {"status": "ok"}
