"""Mango Office telephony client."""

import hashlib
import hmac

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

log = structlog.get_logger()

MANGO_API_BASE = "https://app.mango-office.ru/vpbx"


def verify_signature(data: str, signature: str) -> bool:
    """Verify Mango webhook signature."""
    expected = hmac.new(
        settings.mango_api_secret.encode(),
        data.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def originate_call(to_number: str, webhook_url: str) -> dict:
    """Initiate an outbound call via Mango Office API.

    Returns Mango call object with call_id.
    """
    payload = {
        "command_id": "makeCall",
        "from": {"extension": settings.mango_from_number},
        "to_number": to_number,
        "webhook_url": webhook_url,
    }
    headers = {"Authorization": f"Bearer {settings.mango_api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{MANGO_API_BASE}/commands/callback",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        result = response.json()

    log.info("mango_call_originated", to=to_number, call_id=result.get("call_id"))
    return result


async def hangup_call(call_id: str) -> None:
    """Hang up an active call."""
    headers = {"Authorization": f"Bearer {settings.mango_api_key}"}
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{MANGO_API_BASE}/commands/hangup",
            json={"call_id": call_id},
            headers=headers,
        )
    log.info("mango_call_hangup", call_id=call_id)
