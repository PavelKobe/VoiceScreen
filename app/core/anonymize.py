"""Маскирование персональных данных в транскрипте перед отправкой в LLM.

Что маскируем:
  * ФИО кандидата — берём слова из Candidate.fio и заменяем на [КАНДИДАТ]
    (case-insensitive, по границам слов).
  * Телефонные номера — российские форматы (+7/8 + 10 цифр в любых разделителях).
  * Email-адреса — стандартный regex.

Адреса/паспорта/прочее — не покрываем (требует NER, отложено).

Зачем: финальный scoring уходит в зарубежный LLM (OpenRouter → OpenAI и т.п.),
а персональные данные кандидатов под 152-ФЗ. На итог скоринга маскирование
влияет минимально: LLM всё равно опирается на ответы по существу, а не на
имя.
"""

from __future__ import annotations

import re

# Российские номера. Покрывает +7/8 + (xxx) xxx-xx-xx с любыми разделителями.
_PHONE_RE = re.compile(
    r"(?:\+7|\b8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _fio_words(fio: str | None) -> list[str]:
    if not fio:
        return []
    # Берём слова длиной >= 3, чтобы не словить «Ра», «Ан» и т.п.
    return [w for w in re.split(r"\s+", fio.strip()) if len(w) >= 3]


def anonymize_text(text: str, fio_words: list[str]) -> str:
    """Замаскировать одну строку. Порядок: телефоны → email → ФИО."""
    if not text:
        return text
    out = _PHONE_RE.sub("[ТЕЛЕФОН]", text)
    out = _EMAIL_RE.sub("[EMAIL]", out)
    for word in fio_words:
        out = re.sub(rf"\b{re.escape(word)}\b", "[КАНДИДАТ]", out, flags=re.IGNORECASE)
    return out


def anonymize_transcript(
    transcript: list[dict[str, str]],
    candidate_fio: str | None = None,
) -> tuple[list[dict[str, str]], int]:
    """Возвращает (анонимизированный transcript, количество сделанных замен).

    Не мутирует исходный список — звонок и БД продолжают видеть оригинал.
    """
    fio_words = _fio_words(candidate_fio)
    out: list[dict[str, str]] = []
    replaced = 0
    for msg in transcript:
        original = msg.get("content", "")
        masked = anonymize_text(original, fio_words)
        if masked != original:
            replaced += 1
        out.append({**msg, "content": masked})
    return out, replaced
