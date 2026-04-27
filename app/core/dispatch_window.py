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
