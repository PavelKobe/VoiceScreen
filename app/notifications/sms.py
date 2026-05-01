"""SMS-отправка через Voximplant SendSmsMessage.

Используем тот же номер, с которого совершаются звонки
(`settings.voximplant_from_number`) — кандидат видит знакомый номер в
SMS и в звонке. Это требует, чтобы для номера была включена услуга SMS
в кабинете Voximplant (по умолчанию у российских DID отключена).
"""

from __future__ import annotations

from typing import Any

import structlog

from app.config import settings
from app.telephony.voximplant import send_sms as _vox_send_sms

log = structlog.get_logger()


async def send_sms(to_e164: str, text: str) -> dict[str, Any]:
    """Отправить одно SMS. to_e164 в формате +7XXXXXXXXXX."""
    if not settings.voximplant_from_number:
        log.warning("sms_skipped_no_from_number", to=to_e164)
        return {"status": "SKIPPED", "reason": "no_from_number"}
    if not settings.voximplant_api_key:
        log.warning("sms_skipped_no_voximplant_key", to=to_e164)
        return {"status": "SKIPPED", "reason": "no_voximplant_key"}
    return await _vox_send_sms(to_e164, text)
