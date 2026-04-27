"""Tests for the scripted DialogSession FSM (no LLM in turn loop)."""

from __future__ import annotations

from app.core.dialog import (
    _CLARIFICATION_PROMPT,
    _CONSENT_REJECT_FAREWELL,
    _FAREWELL,
    _TRANSITION_PREFIX,
    DialogSession,
)


def _scenario() -> dict:
    return {
        "agent_role": "HR-помощник",
        "company_name": "Тест",
        "vacancy_title": "Курьер",
        "questions": [
            {
                "id": "consent",
                "text": "Разговор записывается. Продолжаем?",
                "type": "confirm",
                "on_reject": "end_call",
            },
            {"id": "experience", "text": "Был ли опыт работы курьером?", "type": "open"},
            {"id": "schedule", "text": "Какой график удобен?", "type": "open"},
        ],
    }


def test_greeting_includes_intro_and_first_question():
    s = DialogSession(_scenario())
    g = s.get_greeting()
    assert "HR-помощник" in g
    assert "Тест" in g
    assert "Курьер" in g
    # Первый вопрос (consent) встроен в открывающую реплику.
    assert "Разговор записывается" in g
    assert s.current_idx == 0


def test_walks_through_questions_in_order():
    s = DialogSession(_scenario())
    s.get_greeting()

    r1 = s.process_candidate_reply("да, согласен")
    assert r1 is not None
    assert s.current_idx == 1
    assert "Был ли опыт" in r1
    assert r1.startswith(_TRANSITION_PREFIX)

    r2 = s.process_candidate_reply("да, год работал")
    assert r2 is not None
    assert s.current_idx == 2
    assert "график" in r2

    r3 = s.process_candidate_reply("полная занятость")
    assert r3 == _FAREWELL
    assert s.finished is True


def test_extra_input_after_finish_returns_none():
    s = DialogSession(_scenario())
    s.get_greeting()
    s.process_candidate_reply("да")
    s.process_candidate_reply("опыт есть")
    s.process_candidate_reply("любой график")
    assert s.finished
    assert s.process_candidate_reply("ещё что-то") is None


def test_unclear_answer_triggers_one_clarification():
    s = DialogSession(_scenario())
    s.get_greeting()
    s.process_candidate_reply("да")
    # Невнятный ответ на вопрос про опыт.
    r = s.process_candidate_reply("")
    assert r == _CLARIFICATION_PROMPT
    assert s.current_idx == 1  # индекс не сдвинулся
    # Вторая попытка — даже если опять пустая, идём дальше с пометкой unclear.
    r2 = s.process_candidate_reply("")
    assert r2 is not None
    assert r2.startswith(_TRANSITION_PREFIX)
    assert s.current_idx == 2
    assert 1 in s.unclear_indices


def test_filler_only_answer_treated_as_unclear():
    s = DialogSession(_scenario())
    s.get_greeting()
    s.process_candidate_reply("да")
    r = s.process_candidate_reply("эээ ммм")
    assert r == _CLARIFICATION_PROMPT


def test_consent_rejection_ends_call():
    s = DialogSession(_scenario())
    s.get_greeting()
    r = s.process_candidate_reply("нет, не согласен")
    assert r == _CONSENT_REJECT_FAREWELL
    assert s.finished is True


def test_clarification_resets_per_question():
    """Повтор использован для Q1, на Q2 снова доступен."""
    s = DialogSession(_scenario())
    s.get_greeting()
    s.process_candidate_reply("да")
    # Q1 (experience): использовали повтор.
    s.process_candidate_reply("")
    s.process_candidate_reply("год работал")
    # Q2 (schedule): повтор должен сработать заново.
    r = s.process_candidate_reply("")
    assert r == _CLARIFICATION_PROMPT


def test_transcript_records_question_ids():
    s = DialogSession(_scenario())
    s.get_greeting()
    s.process_candidate_reply("да")
    s.process_candidate_reply("год работал")
    user_turns = [m for m in s.get_transcript() if m["role"] == "user"]
    assert user_turns[0].get("question_id") == "consent"
    assert user_turns[1].get("question_id") == "experience"


def test_choice_question_announces_options():
    scenario = {
        "agent_role": "HR",
        "company_name": "Х",
        "vacancy_title": "Курьер",
        "questions": [
            {"id": "consent", "text": "Согласны?", "type": "confirm",
             "on_reject": "end_call"},
            {"id": "schedule", "text": "Какой график удобен?", "type": "choice",
             "options": ["Полная занятость", "Подработка", "Любой"]},
        ],
    }
    s = DialogSession(scenario)
    s.get_greeting()
    r = s.process_candidate_reply("да")
    assert "Полная занятость" in r
    assert "Подработка" in r
    assert "Любой" in r
    assert "или" in r


def test_choice_in_first_position_announces_options_in_greeting():
    scenario = {
        "agent_role": "HR",
        "company_name": "Х",
        "vacancy_title": "Курьер",
        "questions": [
            {"id": "schedule", "text": "Какой график удобен?", "type": "choice",
             "options": ["Полная", "Подработка"]},
        ],
    }
    s = DialogSession(scenario)
    g = s.get_greeting()
    assert "Полная" in g and "Подработка" in g


def test_unclear_marker_in_history():
    s = DialogSession(_scenario())
    s.get_greeting()
    s.process_candidate_reply("да")
    s.process_candidate_reply("")  # clarify
    s.process_candidate_reply("")  # все ещё unclear -> зафиксировать
    user_turns = [m for m in s.get_transcript() if m["role"] == "user"]
    assert any("[не расслышано]" in m["content"] for m in user_turns)
