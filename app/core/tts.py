"""Yandex SpeechKit TTS client."""

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

log = structlog.get_logger()

SYNTHESIZE_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def synthesize_speech(text: str, voice: str = "alena") -> bytes:
    """Synthesize speech from text using Yandex SpeechKit.

    Returns audio bytes (OGG).
    """
    headers = {"Authorization": f"Api-Key {settings.yandex_cloud_api_key}"}
    data = {
        "folderId": settings.yandex_cloud_folder_id,
        "text": text,
        "lang": "ru-RU",
        "voice": voice,
        "format": "oggopus",
        "sampleRateHertz": 48000,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(SYNTHESIZE_URL, headers=headers, data=data)
        response.raise_for_status()

    log.info("tts_synthesized", text_length=len(text), audio_size=len(response.content))
    return response.content
