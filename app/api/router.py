from fastapi import APIRouter

from app.api.candidates import router as candidates_router
from app.api.calls import router as calls_router
from app.api.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(candidates_router, prefix="/candidates", tags=["candidates"])
api_router.include_router(calls_router, prefix="/calls", tags=["calls"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
