import structlog
from fastapi import APIRouter, Request

router = APIRouter()
log = structlog.get_logger()


@router.post("/mango/call-event")
async def mango_call_event(request: Request) -> dict:
    """Webhook from Mango Office on call state changes."""
    body = await request.json()
    log.info("mango_call_event", payload=body)
    # TODO: handle call state transitions (ringing, connected, completed)
    return {"status": "ok"}


@router.post("/mango/media-stream")
async def mango_media_stream(request: Request) -> dict:
    """Webhook/WebSocket for Mango media stream (audio chunks)."""
    # TODO: receive audio chunks, pipe to STT
    return {"status": "ok"}
