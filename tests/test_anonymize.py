"""Tests for transcript anonymization before LLM."""

from __future__ import annotations

from app.core.anonymize import anonymize_text, anonymize_transcript


def test_phone_plus7_with_brackets():
    out = anonymize_text("Звоните +7 (495) 123-45-67", [])
    assert out == "Звоните [ТЕЛЕФОН]"


def test_phone_8_no_separators():
    out = anonymize_text("мой 89991234567", [])
    assert "[ТЕЛЕФОН]" in out
    assert "89991234567" not in out


def test_phone_with_dashes():
    out = anonymize_text("8-999-123-45-67", [])
    assert out == "[ТЕЛЕФОН]"


def test_email_replaced():
    out = anonymize_text("Пишите на ivan.petrov+work@mail.ru, жду", [])
    assert "[EMAIL]" in out
    assert "ivan.petrov" not in out


def test_fio_replaced_case_insensitive():
    out = anonymize_text("Здравствуйте, иванов иван иванович", ["Иванов", "Иван", "Иванович"])
    assert "иванов" not in out.lower()
    assert out.count("[КАНДИДАТ]") == 3


def test_short_fio_word_skipped():
    # Слова < 3 символов не маскируются (избегаем «Ан», «Ра» и т.п. в обычном тексте).
    out = anonymize_text("Ан и Бо приехали", ["Ан", "Бо"])
    assert out == "Ан и Бо приехали"


def test_fio_does_not_match_substring():
    # «Иван» внутри «Иванова» не должен маскироваться целиком —
    # мы используем \b границы.
    out = anonymize_text("Ивановой передали посылку", ["Иван"])
    assert out == "Ивановой передали посылку"


def test_anonymize_transcript_preserves_roles():
    transcript = [
        {"role": "assistant", "content": "Здравствуйте, Иван!"},
        {"role": "user", "content": "Да, телефон 89991234567"},
    ]
    out, replaced = anonymize_transcript(transcript, candidate_fio="Иван Петров")
    assert replaced == 2
    assert out[0]["role"] == "assistant"
    assert "[КАНДИДАТ]" in out[0]["content"]
    assert "[ТЕЛЕФОН]" in out[1]["content"]
    # Оригинал не мутирован.
    assert "Иван" in transcript[0]["content"]


def test_anonymize_no_fio():
    transcript = [{"role": "user", "content": "Просто текст"}]
    out, replaced = anonymize_transcript(transcript, candidate_fio=None)
    assert replaced == 0
    assert out[0]["content"] == "Просто текст"
