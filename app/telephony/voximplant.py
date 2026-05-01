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


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
async def get_record_url(call_session_history_id: str) -> str | None:
    """Fetch recording URL for a completed VoxEngine session.

    Calls GetCallHistory with with_records=1. Returns the first record_url
    found or None if the session has no recordings yet / ever.
    """
    params = {
        "account_id": settings.voximplant_account_id,
        "api_key": settings.voximplant_api_key,
        "call_session_history_id": call_session_history_id,
        "with_records": "1",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{VOXIMPLANT_API_BASE}/GetCallHistory/", params=params
        )
        response.raise_for_status()
        data = response.json()
    for item in data.get("result", []):
        for rec in item.get("records", []) or []:
            url = rec.get("record_url")
            if url:
                return url
    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
async def send_sms(destination: str, text: str, source: str | None = None) -> dict:
    """Отправить SMS через Voximplant Management API (SendSms).

    `source` — номер-отправитель в формате без «+» (например "74951086575").
    По умолчанию берётся `settings.voximplant_from_number` — тот же номер,
    с которого мы звоним. Чтобы метод заработал, этот номер должен быть
    куплен в Voximplant и для него должна быть активирована услуга SMS.

    `destination` — номер получателя в международном формате (с «+» или без).

    Длинные сообщения тарифицируются как несколько SMS — Voximplant склеивает
    их автоматически.
    """
    src = (source or settings.voximplant_from_number or "").lstrip("+")
    if not src:
        raise RuntimeError("voximplant.send_sms: пустой source (нет VOXIMPLANT_FROM_NUMBER)")

    params = {
        "account_id": settings.voximplant_account_id,
        "api_key": settings.voximplant_api_key,
        "source": src,
        "destination": destination.lstrip("+"),
        "sms_body": text,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{VOXIMPLANT_API_BASE}/SendSmsMessage/", params=params)
        response.raise_for_status()
        result = response.json()

    if result.get("error"):
        # Самые типичные коды: 401 (невалидные ключи), 488 (SMS не подключены
        # на номер), 491 (некорректный destination). Бросаем — caller (Celery)
        # сделает retry для сетевых, или зафейлится для постоянных.
        raise RuntimeError(f"Voximplant SendSmsMessage error: {result['error']}")

    log.info(
        "voximplant_sms_sent",
        to=destination,
        source=src,
        message_id=result.get("message_id"),
        fragments=result.get("fragments_count"),
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
