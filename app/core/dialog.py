"""Dialog orchestrator — manages the conversation flow for a single call."""

import structlog

from app.core.llm import get_next_reply
from app.core.scenario import build_system_prompt

log = structlog.get_logger()

# Слова и обороты, которые мы расцениваем как прощание агента.
# Если они появились в его реплике — диалог считается завершённым.
_FAREWELL_MARKERS = (
    "до свидания",
    "хорошего дня",
    "всего доброго",
    "всего хорошего",
    "хорошего вечера",
    "будем на связи",
    "свяжемся с вами",
    "до встречи",
)


def _looks_like_farewell(reply: str) -> bool:
    low = reply.lower()
    return any(marker in low for marker in _FAREWELL_MARKERS)


class DialogSession:
    """Manages one screening conversation."""

    def __init__(self, scenario: dict):
        self.scenario = scenario
        self.system_prompt = build_system_prompt(self.scenario)
        self.history: list[dict[str, str]] = []
        self.turn_count = 0
        self.finished = False

        # Лимит на круг диалога. Один вопрос — это пара (агент-вопрос, ответ
        # кандидата). Плюс приветствие и farewell. Запас на переспросы.
        n_questions = len(self.scenario.get("questions", []) or [])
        self.max_turns = max(self.scenario.get("max_turns", 0), n_questions * 2 + 6)

    async def get_greeting(self) -> str:
        """Generate the opening phrase (includes recording notice)."""
        reply = await get_next_reply(self.system_prompt, self.history)
        self.history.append({"role": "assistant", "content": reply})
        self.turn_count += 1
        return reply

    async def process_candidate_reply(self, text: str) -> str | None:
        """Process candidate's speech and return the next agent reply.

        Returns None если диалог уже закрыт (после farewell или по лимиту turns).
        ws.py при None должен послать `hangup`.
        """
        if self.finished:
            log.info("dialog_extra_input_after_finish", text=text[:50])
            return None

        self.history.append({"role": "user", "content": text})
        self.turn_count += 1

        # Жёсткий потолок: даже если LLM зациклился, не звоним вечно.
        if self.turn_count >= self.max_turns:
            farewell = "Спасибо за ваши ответы! Мы свяжемся с вами по результатам. Хорошего дня!"
            self.history.append({"role": "assistant", "content": farewell})
            self.finished = True
            log.info("dialog_capped_by_max_turns", turn=self.turn_count, max=self.max_turns)
            return farewell

        reply = await get_next_reply(self.system_prompt, self.history)
        self.history.append({"role": "assistant", "content": reply})
        self.turn_count += 1

        if _looks_like_farewell(reply):
            self.finished = True
            log.info("dialog_farewell_detected", turn=self.turn_count)

        log.info("dialog_turn", turn=self.turn_count, candidate_text=text[:50])
        return reply

    def get_transcript(self) -> list[dict[str, str]]:
        """Return full conversation transcript."""
        return list(self.history)
