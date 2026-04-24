"""Voximplant telephony client (Management API v2)."""

import json
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

log = structlog.get_logger()

VOXIMPLANT_API_BASE = "https://api.voximplant.com/platform_api"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def originate_call(to_number: str, custom_data: dict[str, Any] | None = None) -> dict:
    """Trigger an outbound screening call via Voximplant.

    Voximplant flow: StartScenarios fires the VoxEngine scenario bound to
    ``rule_id``; the scenario itself originates the PSTN call and opens the
    WebSocket back to our backend. ``custom_data`` is passed into VoxEngine
    via ``VoxEngine.customData()``.

    Returns Voximplant response (contains ``media_session_access_url`` /
    ``call_session_history_id`` — we store the latter as call id).
    """
    payload: dict[str, Any] = {"to_number": to_number}
    if settings.public_ws_url:
        payload["ws_url"] = settings.public_ws_url
    if settings.voximplant_from_number:
        payload["from_number"] = settings.voximplant_from_number
    if settings.ws_auth_token:
        payload["ws_auth_token"] = settings.ws_auth_token
    payload.update(custom_data or {})
    script_custom_data = json.dumps(payload, ensure_ascii=False)
    params = {
        "account_id": settings.voximplant_account_id,
        "api_key": settings.voximplant_api_key,
        "rule_id": settings.voximplant_rule_id,
        "script_custom_data": script_custom_data,
    }
    if settings.voximplant_application_id:
        params["application_id"] = settings.voximplant_application_id
    elif settings.voximplant_application_name:
        params["application_name"] = settings.voximplant_application_name

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{VOXIMPLANT_API_BASE}/StartScenarios/", params=params)
        response.raise_for_status()
        result = response.json()

    if result.get("error"):
        raise RuntimeError(f"Voximplant StartScenarios error: {result['error']}")

    log.info(
        "voximplant_call_originated",
        to=to_number,
        session_id=result.get("call_session_history_id"),
        media_url=result.get("media_session_access_url"),
    )
    return result


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def hangup_call(call_session_history_id: str) -> None:
    """Stop an active VoxEngine session.

    Uses StopScenarios — terminates the session, which hangs up the call.
    """
    params = {
        "account_id": settings.voximplant_account_id,
        "api_key": settings.voximplant_api_key,
        "media_session_access_url": call_session_history_id,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{VOXIMPLANT_API_BASE}/StopScenarios/", params=params)
    log.info("voximplant_call_hangup", session_id=call_session_history_id)
