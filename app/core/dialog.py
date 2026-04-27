"""Dialog orchestrator — scripted FSM driving one screening call.

LLM is NOT used during the call: we walk through scenario.questions by
index and let final scoring (app/core/scoring.py) reason about answers
after the call ends. See plan: соft-hatching-flute.
"""

from __future__ import annotations

import structlog

from app.core.scenario import build_greeting

log = structlog.get_logger()

_FAREWELL = (
    "Спасибо за ваши ответы! Мы свяжемся с вами по результатам. Хорошего дня!"
)
_CLARIFICATION_PROMPT = "Извините, я вас не расслышал. Повторите, пожалуйста."
_CONSENT_REJECT_FAREWELL = (
    "Понял, спасибо за уделённое время. Хорошего дня!"
)
_TRANSITION_PREFIX = "Спасибо. Следующий вопрос: "

_FILLER_TOKENS = {"э", "ээ", "эээ", "м", "мм", "ммм", "а", "аа", "ну"}


def _looks_unclear(text: str) -> bool:
    t = (text or "").strip().lower()
    if len(t) < 2:
        return True
    # одни наполнители без смысловых слов
    tokens = [tok.strip(".,!?…») ") for tok in t.split()]
    tokens = [tok for tok in tokens if tok]
    if tokens and all(tok in _FILLER_TOKENS for tok in tokens):
        return True
    return False


def _is_negative_answer(text: str) -> bool:
    """Грубая эвристика «нет» для type=confirm с on_reject=end_call."""
    t = (text or "").strip().lower()
    if not t:
        return False
    # короткое «нет», «не согласен», «не хочу», «отказываюсь»
    return (
        t.startswith("нет")
        or t.startswith("не ")
        or t.startswith("не,")
        or "отказ" in t
        or "не согласен" in t
        or "не согласна" in t
    )


class DialogSession:
    """Manages one screening conversation as a scripted FSM."""

    def __init__(self, scenario: dict):
        self.scenario = scenario
        self.questions: list[dict] = scenario.get("questions", []) or []
        self.history: list[dict[str, str]] = []
        self.current_idx: int = 0
        self.clarification_used: dict[int, bool] = {}
        self.unclear_indices: set[int] = set()
        self.finished: bool = False

    # ---- Greeting --------------------------------------------------------

    def get_greeting(self) -> str:
        """Build opening utterance: intro + first scenario question.

        Synchronous — no LLM call.
        """
        intro = build_greeting(self.scenario)
        if self.questions:
            first_q = self.questions[0].get("text", "").strip()
            opening = f"{intro} {first_q}".strip()
        else:
            # Сценарий без вопросов — сразу прощание.
            opening = _FAREWELL
            self.finished = True
        self.history.append({"role": "assistant", "content": opening})
        return opening

    # ---- Turn handling ---------------------------------------------------

    def process_candidate_reply(self, text: str) -> str | None:
        """Process candidate's speech and return next agent reply.

        Returns None if dialog already finished — ws.py should send hangup.
        Synchronous — no LLM call in the per-turn path.
        """
        if self.finished:
            log.info("dialog_extra_input_after_finish", text=(text or "")[:50])
            return None

        idx = self.current_idx
        if idx >= len(self.questions):
            # На всякий случай: вопросы кончились, но finished не выставлен.
            self._say_and_finish(_FAREWELL)
            return _FAREWELL

        unclear = _looks_unclear(text)

        # Failsafe: одна попытка повтора, потом дальше с пометкой unclear.
        if unclear and not self.clarification_used.get(idx, False):
            self.clarification_used[idx] = True
            self.history.append({"role": "user", "content": text or ""})
            self.history.append(
                {"role": "assistant", "content": _CLARIFICATION_PROMPT}
            )
            log.info("dialog_clarify", idx=idx)
            return _CLARIFICATION_PROMPT

        # Записываем ответ кандидата (с маркером, если непонятно).
        recorded = (text or "").strip()
        if unclear:
            self.unclear_indices.add(idx)
            recorded = f"[не расслышано] {recorded}".strip()
        # Привязка к id вопроса для финального scoring'а.
        qid = self.questions[idx].get("id", f"q{idx}")
        self.history.append(
            {"role": "user", "content": recorded, "question_id": qid}
        )

        # Спец-кейс: consent с on_reject=end_call и явный отказ → завершаем звонок.
        q = self.questions[idx]
        if (
            q.get("type") == "confirm"
            and q.get("on_reject") == "end_call"
            and not unclear
            and _is_negative_answer(text)
        ):
            self._say_and_finish(_CONSENT_REJECT_FAREWELL)
            log.info("dialog_consent_rejected", idx=idx)
            return _CONSENT_REJECT_FAREWELL

        # Сдвигаем индекс к следующему вопросу.
        self.current_idx = idx + 1
        if self.current_idx >= len(self.questions):
            self._say_and_finish(_FAREWELL)
            log.info("dialog_completed", asked=len(self.questions))
            return _FAREWELL

        next_q_text = self.questions[self.current_idx].get("text", "").strip()
        reply = f"{_TRANSITION_PREFIX}{next_q_text}"
        self.history.append({"role": "assistant", "content": reply})
        log.info(
            "dialog_turn",
            idx=self.current_idx,
            unclear=unclear,
            qid=qid,
        )
        return reply

    def _say_and_finish(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})
        self.finished = True

    # ---- Output ----------------------------------------------------------

    def get_transcript(self) -> list[dict[str, str]]:
        """Return full conversation transcript for persistence and scoring."""
        return list(self.history)
