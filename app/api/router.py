from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.calls import router as calls_router
from app.api.candidates import router as candidates_router
from app.api.clients import router as clients_router
from app.api.scenarios import router as scenarios_router
from app.api.team import router as team_router
from app.api.users import router as users_router
from app.api.vacancies import router as vacancies_router
from app.api.webhooks import router as webhooks_router
from app.api.ws import router as ws_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(clients_router, prefix="/clients", tags=["clients"])
api_router.include_router(
    users_router, prefix="/clients/{client_id}/users", tags=["users"]
)
api_router.include_router(team_router, prefix="/team", tags=["team"])
api_router.include_router(scenarios_router, prefix="/scenarios", tags=["scenarios"])
api_router.include_router(vacancies_router, prefix="/vacancies", tags=["vacancies"])
api_router.include_router(candidates_router, prefix="/candidates", tags=["candidates"])
api_router.include_router(calls_router, prefix="/calls", tags=["calls"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(ws_router, prefix="/ws", tags=["ws"])
