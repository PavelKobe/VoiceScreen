"""Dialog orchestrator — manages the conversation flow for a single call."""

import structlog

from app.core.llm import get_next_reply
from app.core.scenario import build_system_prompt, load_scenario

log = structlog.get_logger()


class DialogSession:
    """Manages one screening conversation."""

    def __init__(self, scenario_name: str):
        self.scenario = load_scenario(scenario_name)
        self.system_prompt = build_system_prompt(self.scenario)
        self.history: list[dict[str, str]] = []
        self.turn_count = 0

    async def get_greeting(self) -> str:
        """Generate the opening phrase (includes recording notice)."""
        reply = await get_next_reply(self.system_prompt, self.history)
        self.history.append({"role": "assistant", "content": reply})
        self.turn_count += 1
        return reply

    async def process_candidate_reply(self, text: str) -> str | None:
        """Process candidate's speech and return the next agent reply.

        Returns None if the conversation is complete.
        """
        self.history.append({"role": "user", "content": text})
        self.turn_count += 1

        max_turns = self.scenario.get("max_turns", 20)
        if self.turn_count >= max_turns:
            farewell = "Спасибо за ваши ответы! Мы свяжемся с вами. До свидания!"
            self.history.append({"role": "assistant", "content": farewell})
            return farewell

        reply = await get_next_reply(self.system_prompt, self.history)
        self.history.append({"role": "assistant", "content": reply})
        self.turn_count += 1

        log.info("dialog_turn", turn=self.turn_count, candidate_text=text[:50])
        return reply

    def get_transcript(self) -> list[dict[str, str]]:
        """Return full conversation transcript."""
        return list(self.history)
