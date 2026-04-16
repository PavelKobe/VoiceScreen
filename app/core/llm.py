"""LLM client for dialog decisions."""

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

log = structlog.get_logger()

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def get_next_reply(
    system_prompt: str,
    conversation_history: list[dict[str, str]],
) -> str:
    """Get next agent reply from LLM based on conversation history.

    Returns the agent's next phrase to speak.
    """
    client = _get_openai_client()
    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=300,
    )
    reply = response.choices[0].message.content or ""
    log.info("llm_reply", reply_length=len(reply))
    return reply
