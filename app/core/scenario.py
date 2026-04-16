"""YAML scenario loader for screening questionnaires."""

from pathlib import Path

import yaml

SCENARIOS_DIR = Path(__file__).resolve().parent.parent.parent / "scenarios"


def load_scenario(scenario_name: str) -> dict:
    """Load a YAML scenario file by name.

    Returns parsed dict with questions, branching, and criteria.
    """
    path = SCENARIOS_DIR / f"{scenario_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scenario '{scenario_name}' not found at {path}")

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_system_prompt(scenario: dict) -> str:
    """Build LLM system prompt from scenario config."""
    role = scenario.get("agent_role", "HR-помощник")
    company = scenario.get("company_name", "компания")
    vacancy = scenario.get("vacancy_title", "вакансия")
    questions = scenario.get("questions", [])

    questions_text = "\n".join(
        f"{i+1}. {q['text']}" for i, q in enumerate(questions)
    )

    return f"""Ты — {role} компании «{company}». Проводишь телефонный скрининг на позицию «{vacancy}».

ВАЖНО: В самом начале разговора предупреди, что разговор записывается, и спроси согласие.

Задай кандидату следующие вопросы по порядку:
{questions_text}

Правила:
- Говори кратко и дружелюбно.
- Если кандидат ответил непонятно — переспроси один раз.
- Если кандидат отказывается отвечать — переходи к следующему вопросу.
- После всех вопросов поблагодари и попрощайся.
- Отвечай ТОЛЬКО следующую реплику агента, без пометок и комментариев."""
