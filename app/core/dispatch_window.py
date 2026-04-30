"""Dispatch-window helpers — соблюдаем окно 9:00–21:00 локального времени.

Все функции принимают и возвращают **naive UTC datetime'ы** — это контракт
проекта для timestamp'ов в БД и Celery `eta`. Локальная зона берётся из
`settings.call_timezone` (по умолчанию Europe/Moscow).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings


def _zone() -> ZoneInfo:
    return ZoneInfo(settings.call_timezone)


def is_within_window(now_utc: datetime) -> bool:
    """Открыто ли окно для исходящего звонка прямо сейчас."""
    local = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(_zone())
    return settings.call_window_start_hour <= local.hour < settings.call_window_end_hour


def next_dispatch_time(after_utc: datetime) -> datetime:
    """Ближайший разрешённый момент для звонка не раньше `after_utc`.

    Если `after_utc` уже внутри окна — возвращает его как есть. Иначе
    сдвигает на ближайшие `call_window_start_hour:00` локального времени
    (сегодня, если ещё не дошли до начала окна, иначе завтра).
    """
    if is_within_window(after_utc):
        return after_utc

    zone = _zone()
    local = after_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(zone)
    start_today = local.replace(
        hour=settings.call_window_start_hour, minute=0, second=0, microsecond=0
    )
    if local.hour < settings.call_window_start_hour:
        target_local = start_today
    else:
        target_local = start_today + timedelta(days=1)

    return target_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def slot_eta(hhmm: str, after_utc: datetime) -> datetime:
    """Ближайшее `HH:MM` локального времени строго не раньше `after_utc`.

    Если момент уже прошёл сегодня — берём завтра. Возвращает naive UTC.
    """
    zone = _zone()
    local = after_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(zone)
    h, m = (int(x) for x in hhmm.split(":"))
    candidate = local.replace(hour=h, minute=m, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def schedule_next_attempt(
    call_slots: list[str] | None,
    attempts_count: int,
    after_utc: datetime,
) -> datetime | None:
    """Eta для попытки № `attempts_count + 1`. Возвращает None, если попытки
    исчерпаны (для exhausted-перехода).

    `call_slots` — кастомное расписание вакансии (`["10:00","11:00",...]`)
    или None для глобального fallback'а. `attempts_count` — сколько попыток
    уже было сделано (после-инкрементальное значение).

    Кастомные слоты:
      - индекс следующей попытки = attempts_count;
      - если attempts_count >= len(slots) — попыток больше нет, None.
    Fallback (когда slots=None):
      - первая попытка (attempts_count=0): `next_dispatch_time(now)`.
      - retry: `next_dispatch_time(now + backoff[idx])`.
      - после `settings.call_max_attempts` — None.
    """
    if call_slots:
        if attempts_count >= len(call_slots):
            return None
        return slot_eta(call_slots[attempts_count], after_utc)

    if attempts_count >= settings.call_max_attempts:
        return None
    if attempts_count == 0:
        return next_dispatch_time(after_utc)
    backoff = settings.call_retry_backoff_minutes
    idx = min(attempts_count - 1, len(backoff) - 1)
    delay_min = backoff[max(idx, 0)]
    return next_dispatch_time(after_utc + timedelta(minutes=delay_min))


def effective_max_attempts(call_slots: list[str] | None) -> int:
    """Эффективный лимит попыток для вакансии."""
    if call_slots:
        return len(call_slots)
    return settings.call_max_attempts
