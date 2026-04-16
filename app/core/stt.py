"""Yandex SpeechKit STT client (streaming recognition)."""

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

log = structlog.get_logger()

RECOGNIZE_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def recognize_audio(audio_data: bytes, sample_rate: int = 8000) -> str:
    """Recognize speech from audio bytes using Yandex SpeechKit.

    Returns recognized text.
    """
    headers = {"Authorization": f"Api-Key {settings.yandex_cloud_api_key}"}
    params = {
        "folderId": settings.yandex_cloud_folder_id,
        "lang": "ru-RU",
        "sampleRateHertz": sample_rate,
        "format": "lpcm",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            RECOGNIZE_URL, headers=headers, params=params, content=audio_data
        )
        response.raise_for_status()
        result = response.json()

    text = result.get("result", "")
    log.info("stt_recognized", text_length=len(text))
    return text
