import logging
import sys

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import api_router
from app.config import settings

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

app = FastAPI(
    title="VoiceScreen API",
    description="AI Voice Screening Agent for mass hiring",
    version="0.1.0",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

if settings.secret_key:
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        https_only=settings.cookie_secure,
        same_site="lax",
        domain=settings.cookie_domain or None,
        session_cookie="session",
    )

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
