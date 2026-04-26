"""Post-call scoring of a screening conversation.

LLM acts as a judge: takes the YAML scenario (questions + pass_criteria)
and the full transcript, returns structured answers, a score, and a
pass/fail decision.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.core.llm import _get_client
from app.config import settings

log = structlog.get_logger()


def _build_scoring_prompt(scenario: dict, transcript: list[dict[str, str]]) -> list[dict[str, str]]:
    questions = scenario.get("questions", [])
    pass_criteria = scenario.get("pass_criteria", {})

    # id вопроса — из YAML (старый формат) или порядковый номер (DB-сценарии).
    questions_block = "\n".join(
        f"- id={q.get('id') or f'q{i+1}'} (type={q.get('type', 'open')}"
        + (", required=true" if q.get("required") else "")
        + f"): {q.get('text', '')}"
        for i, q in enumerate(questions)
    )

    transcript_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in transcript
    )

    system = (
        "Ты строгий HR-аналитик. На входе — анкета со списком вопросов и "
        "транскрипт телефонного скрининга. На выходе — ТОЛЬКО JSON, "
        "без пояснений и без markdown-ограждений. "
        "Поля JSON: "
        "answers (object: id вопроса → краткий ответ кандидата или null если "
        "не отвечен/неясен), "
        "score (число от 0 до 10), "
        "decision (одно из: pass, reject, review), "
        "reasoning (одна-две фразы почему такое решение)."
    )

    user = (
        f"Вопросы анкеты:\n{questions_block}\n\n"
        f"pass_criteria: {json.dumps(pass_criteria, ensure_ascii=False)}\n\n"
        f"Транскрипт:\n{transcript_text}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def score_call(scenario: dict, transcript: list[dict[str, str]]) -> dict[str, Any]:
    """Judge the call via LLM. Returns dict with answers, score, decision, reasoning."""
    client = _get_client()
    messages = _build_scoring_prompt(scenario, transcript)

    response = await client.chat.completions.create(
        model=settings.openrouter_model,
        messages=messages,
        temperature=0,
        max_tokens=600,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("scoring_bad_json", raw=raw[:500])
        return {"answers": {}, "score": None, "decision": "review", "reasoning": "invalid LLM JSON"}

    log.info(
        "call_scored",
        score=result.get("score"),
        decision=result.get("decision"),
    )
    return result
