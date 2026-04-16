"""LLM client via OpenRouter (OpenAI-compatible API)."""

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

log = structlog.get_logger()

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def get_next_reply(
    system_prompt: str,
    conversation_history: list[dict[str, str]],
) -> str:
    """Get next agent reply from LLM based on conversation history."""
    client = _get_client()
    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    response = await client.chat.completions.create(
        model=settings.openrouter_model,
        messages=messages,
        temperature=0.3,
        max_tokens=300,
    )
    reply = response.choices[0].message.content or ""
    log.info("llm_reply", model=settings.openrouter_model, reply_length=len(reply))
    return reply
