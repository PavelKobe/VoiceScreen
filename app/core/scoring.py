"""Post-call scoring of a screening conversation.

LLM acts as a judge: takes the YAML scenario (questions + pass_criteria)
and the full transcript, returns structured answers, a score, a
pass/fail decision, краткое резюме и обоснование.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.core.anonymize import anonymize_transcript
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
        "reasoning (одна-две фразы почему такое решение), "
        "summary (2–3 предложения по-русски: кто кандидат с точки зрения вакансии, "
        "что сказал по ключевым вопросам, общее впечатление; нейтрально, без оценочных "
        "ярлыков). В транскрипте ФИО, телефоны и email могут быть скрыты "
        "плейсхолдерами вида [КАНДИДАТ]/[ТЕЛЕФОН]/[EMAIL] — это нормально, "
        "обращайся к человеку как «кандидат»."
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


async def score_call(
    scenario: dict,
    transcript: list[dict[str, str]],
    candidate_fio: str | None = None,
) -> dict[str, Any]:
    """Judge the call via LLM. Returns dict with answers, score, decision, reasoning, summary.

    Перед отправкой в LLM маскирует ФИО кандидата, телефоны и email-адреса
    в транскрипте (см. app.core.anonymize).
    """
    client = _get_client()
    safe_transcript, _replacements = anonymize_transcript(transcript, candidate_fio)
    messages = _build_scoring_prompt(scenario, safe_transcript)

    response = await client.chat.completions.create(
        model=settings.openrouter_model,
        messages=messages,
        temperature=0,
        max_tokens=800,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("scoring_bad_json", raw=raw[:500])
        return {
            "answers": {},
            "score": None,
            "decision": "review",
            "reasoning": "invalid LLM JSON",
            "summary": None,
        }

    log.info(
        "call_scored",
        score=result.get("score"),
        decision=result.get("decision"),
        has_summary=bool(result.get("summary")),
    )
    return result
