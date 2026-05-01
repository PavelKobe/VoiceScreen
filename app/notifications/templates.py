"""Шаблоны SMS и email-уведомлений.

Никакого Jinja — обычный str.format(). Минимум зависимостей, простая
проверка глазами. Если шаблоны разрастутся — мигрируем на Jinja.
"""

from __future__ import annotations

from html import escape

# --- SMS перед звонком --------------------------------------------------------

# Дефолтный шаблон, если у вакансии не задан кастомный (Vacancy.sms_template).
DEFAULT_SMS_BEFORE_CALL = (
    "Здравствуйте, {fio}! Через ~{minutes} мин вам позвонит {company} "
    "по вакансии «{vacancy}». Если неудобно — игнорируйте звонок."
)


def render_sms_before_call(
    template: str | None,
    *,
    fio: str,
    minutes: int,
    company: str,
    vacancy: str,
) -> str:
    tpl = template or DEFAULT_SMS_BEFORE_CALL
    # Берём только первое слово ФИО, чтобы SMS был короче и личнее.
    first_name = fio.strip().split()[0] if fio.strip() else "коллега"
    try:
        return tpl.format(
            fio=first_name,
            minutes=minutes,
            company=company,
            vacancy=vacancy,
        )
    except (KeyError, IndexError):
        # Шаблон испорчен — fallback на дефолтный.
        return DEFAULT_SMS_BEFORE_CALL.format(
            fio=first_name, minutes=minutes, company=company, vacancy=vacancy,
        )


# --- Email с итогом скрининга --------------------------------------------------

_DECISION_LABEL_RU = {
    "pass": "Подходит",
    "reject": "Не подходит",
    "review": "Требует ручного просмотра",
    "not_reached": "Не дозвонились",
}


def render_call_result_email(
    *,
    fio: str,
    phone: str,
    vacancy_title: str,
    decision: str | None,
    score: float | None,
    reasoning: str | None,
    summary: str | None,
    recording_url: str | None,
    call_card_url: str,
) -> tuple[str, str, str]:
    """Возвращает (subject, text_body, html_body)."""
    decision_ru = _DECISION_LABEL_RU.get(decision or "", decision or "—")
    score_str = f"{score:.1f}" if isinstance(score, (int, float)) else "—"

    subject = f"Скрининг: {fio} → {vacancy_title} — {decision_ru}"

    lines = [
        f"Кандидат: {fio}",
        f"Телефон: {phone}",
        f"Вакансия: {vacancy_title}",
        f"Решение: {decision_ru}",
        f"Балл: {score_str} / 10",
    ]
    if reasoning:
        lines += ["", f"Обоснование: {reasoning}"]
    if summary:
        lines += ["", "Резюме разговора:", summary]
    lines += ["", f"Карточка звонка: {call_card_url}"]
    if recording_url:
        lines += [f"Запись: {recording_url}"]
    text_body = "\n".join(lines)

    html_body = f"""\
<!doctype html>
<html lang="ru">
<body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#111;max-width:560px;margin:0 auto;padding:16px">
  <h2 style="margin:0 0 12px;font-size:18px">Скрининг завершён</h2>
  <table style="border-collapse:collapse;width:100%;font-size:14px">
    <tr><td style="padding:4px 8px;color:#666">Кандидат</td><td style="padding:4px 8px"><b>{escape(fio)}</b></td></tr>
    <tr><td style="padding:4px 8px;color:#666">Телефон</td><td style="padding:4px 8px">{escape(phone)}</td></tr>
    <tr><td style="padding:4px 8px;color:#666">Вакансия</td><td style="padding:4px 8px">{escape(vacancy_title)}</td></tr>
    <tr><td style="padding:4px 8px;color:#666">Решение</td><td style="padding:4px 8px"><b>{escape(decision_ru)}</b></td></tr>
    <tr><td style="padding:4px 8px;color:#666">Балл</td><td style="padding:4px 8px">{escape(score_str)} / 10</td></tr>
  </table>
"""
    if summary:
        html_body += (
            f'<h3 style="font-size:15px;margin:16px 0 4px">Резюме разговора</h3>'
            f'<p style="margin:0;line-height:1.5">{escape(summary)}</p>'
        )
    if reasoning:
        html_body += (
            f'<h3 style="font-size:15px;margin:16px 0 4px">Обоснование оценки</h3>'
            f'<p style="margin:0;line-height:1.5">{escape(reasoning)}</p>'
        )
    html_body += (
        f'<p style="margin:20px 0 4px"><a href="{escape(call_card_url)}" '
        f'style="display:inline-block;padding:8px 14px;background:#111;color:#fff;'
        f'text-decoration:none;border-radius:6px">Открыть карточку звонка</a></p>'
    )
    if recording_url:
        html_body += (
            f'<p style="margin:8px 0;font-size:13px">'
            f'<a href="{escape(recording_url)}">Скачать запись (mp3)</a></p>'
        )
    html_body += "</body></html>"

    return subject, text_body, html_body
