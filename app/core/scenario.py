"""Loader and prompt builder for screening scenarios.

Сценарии живут в БД (`scenarios`), скоупятся per-client. YAML-файлы в
`scenarios/*.yaml` остаются как **системные шаблоны** — на их основе клиент
может создать свой сценарий через UI. Если для клиента в БД ещё нет
запрошенного `slug`, но YAML-шаблон существует — мы лениво копируем его
в БД для этого клиента (lazy seed).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scenario

SCENARIOS_DIR = Path(__file__).resolve().parent.parent.parent / "scenarios"


# === System YAML templates ===

def template_files() -> list[Path]:
    if not SCENARIOS_DIR.exists():
        return []
    return sorted(SCENARIOS_DIR.glob("*.yaml"))


def load_template_yaml(slug: str) -> dict | None:
    """Прочитать YAML-шаблон по slug. None если файла нет."""
    path = SCENARIOS_DIR / f"{slug}.yaml"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_templates() -> list[dict[str, Any]]:
    """Список системных шаблонов с краткой инфой для UI."""
    out: list[dict[str, Any]] = []
    for p in template_files():
        try:
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            continue
        out.append(
            {
                "slug": p.stem,
                "title": data.get("vacancy_title", p.stem),
                "company_name": data.get("company_name", ""),
                "questions_count": len(data.get("questions", []) or []),
            }
        )
    return out


# === DB-backed scenarios ===

async def available_scenarios(client_id: int, db: AsyncSession) -> list[str]:
    """Slugs активных сценариев клиента."""
    rows = await db.execute(
        select(Scenario.slug).where(
            Scenario.client_id == client_id, Scenario.active.is_(True)
        )
    )
    return sorted(rows.scalars().all())


async def load_scenario(slug: str, client_id: int, db: AsyncSession) -> dict:
    """Загрузить сценарий клиента в формате dict (для build_system_prompt).

    Если в БД нет — пытаемся посеять из YAML-шаблона.
    Иначе FileNotFoundError.
    """
    row = await db.execute(
        select(Scenario).where(Scenario.client_id == client_id, Scenario.slug == slug)
    )
    scenario = row.scalar_one_or_none()
    if scenario is None:
        # Lazy seed из YAML.
        template = load_template_yaml(slug)
        if template is None:
            raise FileNotFoundError(f"scenario '{slug}' not found for client {client_id}")
        scenario = Scenario(
            client_id=client_id,
            slug=slug,
            title=template.get("vacancy_title", slug),
            agent_role=template.get("agent_role", "HR-помощник"),
            company_name=template.get("company_name", "компания"),
            vacancy_title=template.get("vacancy_title", "вакансия"),
            questions=template.get("questions", []) or [],
            active=True,
        )
        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)

    return _scenario_to_dict(scenario)


def _scenario_to_dict(s: Scenario) -> dict:
    return {
        "slug": s.slug,
        "agent_role": s.agent_role,
        "company_name": s.company_name,
        "vacancy_title": s.vacancy_title,
        "questions": s.questions or [],
    }


_SLASH_FRACTIONS = {
    "5/2": "пятидневка",
    "2/2": "два через два",
    "3/3": "три через три",
    "1/3": "один через три",
    "24/7": "круглосуточно",
}


def _humanize_options(opt: str) -> str:
    """Заменить численные дроби и косые черты на естественную речь."""
    s = opt
    for k, v in _SLASH_FRACTIONS.items():
        s = s.replace(k, v)
    # Любая оставшаяся «X / Y» → «X или Y».
    s = " ".join(part.strip() for part in s.split("/")) if "/" in s else s
    return s


def build_system_prompt(scenario: dict) -> str:
    """Собрать system prompt для LLM из dict сценария."""
    role = scenario.get("agent_role", "HR-помощник")
    company = scenario.get("company_name", "компания")
    vacancy = scenario.get("vacancy_title", "вакансия")
    questions = scenario.get("questions", [])

    def _fmt_question(i: int, q: dict) -> str:
        line = f"{i+1}. {q['text']}"
        qtype = q.get("type")
        if qtype == "confirm":
            line += " — ожидаешь ответ да или нет."
        elif qtype == "choice" and q.get("options"):
            humanized = [_humanize_options(o) for o in q["options"]]
            opts = " или ".join(humanized) if len(humanized) <= 2 else (
                ", ".join(humanized[:-1]) + " или " + humanized[-1]
            )
            line += f" — естественно предложи кандидату выбрать: {opts}."
        return line

    questions_text = "\n".join(_fmt_question(i, q) for i, q in enumerate(questions))

    return f"""Ты — {role} компании «{company}». Проводишь телефонный скрининг на позицию «{vacancy}».

В самом начале разговора предупреди, что разговор записывается, и спроси согласие.

Задай кандидату следующие вопросы по порядку:
{questions_text}

ПРАВИЛА РЕЧИ:
- Говори кратко, дружелюбно, естественной разговорной речью.
- Представляйся только как «{role} компании «{company}»» — НЕ называй личное имя, НЕ вставляй плейсхолдеры вида «[имя]» или «[ваше имя]».
- Цифровые дроби (5/2, 2/2, 3/3, 24/7) ВСЕГДА озвучивай словами: «пять на два», «два через два», «три через три», «двадцать четыре на семь». Никогда не говори «дробь».
- Когда у вопроса есть варианты — НЕ говори слово «варианты» буквально. Сформулируй естественно: «Полный день, пятидневка или сменный график два через два — что вам больше подходит?»

ПРАВИЛА ВЕДЕНИЯ ДИАЛОГА:
- Если кандидат ответил непонятно — переспроси один раз и переходи дальше.
- Если кандидат отказывается отвечать — переходи к следующему вопросу.
- Не повторяй уже заданные вопросы.

ЗАВЕРШЕНИЕ:
- Когда задал ВСЕ вопросы из списка — поблагодари кандидата одной короткой репликой («Спасибо за ответы, мы свяжемся с вами в ближайшее время. Хорошего дня!») и ВСЁ.
- Категорически НЕ начинай задавать вопросы заново после финальной реплики.
- Категорически НЕ задавай новые вопросы вне списка.

ФОРМАТ ОТВЕТА:
- Отвечай ТОЛЬКО следующую реплику агента вслух, одной фразой.
- Без пометок, без комментариев, без markdown."""
