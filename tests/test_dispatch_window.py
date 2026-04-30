"""Tests for dispatch window logic (9:00–21:00 Europe/Moscow by default)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.dispatch_window import (
    effective_max_attempts,
    is_within_window,
    next_dispatch_time,
    schedule_next_attempt,
    slot_eta,
)


def _msk_to_utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    msk = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("Europe/Moscow"))
    return msk.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


# is_within_window ----------------------------------------------------------

def test_window_open_at_9am_msk():
    assert is_within_window(_msk_to_utc(2026, 5, 1, 9, 0)) is True


def test_window_closed_at_8_59_msk():
    assert is_within_window(_msk_to_utc(2026, 5, 1, 8, 59)) is False


def test_window_open_at_20_59_msk():
    assert is_within_window(_msk_to_utc(2026, 5, 1, 20, 59)) is True


def test_window_closed_at_21_00_msk():
    assert is_within_window(_msk_to_utc(2026, 5, 1, 21, 0)) is False


def test_window_closed_at_3am_msk():
    assert is_within_window(_msk_to_utc(2026, 5, 1, 3, 0)) is False


# next_dispatch_time --------------------------------------------------------

def test_returns_as_is_inside_window():
    inside = _msk_to_utc(2026, 5, 1, 14, 30)
    assert next_dispatch_time(inside) == inside


def test_morning_before_window_shifts_to_today_9am():
    early = _msk_to_utc(2026, 5, 1, 7, 0)
    expected = _msk_to_utc(2026, 5, 1, 9, 0)
    assert next_dispatch_time(early) == expected


def test_late_evening_shifts_to_next_day_9am():
    late = _msk_to_utc(2026, 5, 1, 22, 30)
    expected = _msk_to_utc(2026, 5, 2, 9, 0)
    assert next_dispatch_time(late) == expected


def test_just_at_window_close_shifts_to_next_day():
    closing = _msk_to_utc(2026, 5, 1, 21, 0)
    expected = _msk_to_utc(2026, 5, 2, 9, 0)
    assert next_dispatch_time(closing) == expected


def test_around_msk_midnight_shifts_correctly():
    """01:30 МСК — окно ещё закрыто, следующее открытие — 09:00 того же дня."""
    after_midnight = _msk_to_utc(2026, 5, 1, 1, 30)
    expected = _msk_to_utc(2026, 5, 1, 9, 0)
    assert next_dispatch_time(after_midnight) == expected


# slot_eta + schedule_next_attempt -----------------------------------------

def test_slot_eta_today_when_in_future():
    """Если 14:00 МСК ещё впереди — берём сегодня."""
    now = _msk_to_utc(2026, 5, 1, 9, 30)
    expected = _msk_to_utc(2026, 5, 1, 14, 0)
    assert slot_eta("14:00", now) == expected


def test_slot_eta_tomorrow_when_in_past():
    """Если слот уже прошёл сегодня — берём завтра."""
    now = _msk_to_utc(2026, 5, 1, 15, 0)
    expected = _msk_to_utc(2026, 5, 2, 14, 0)
    assert slot_eta("14:00", now) == expected


def test_schedule_with_slots_first_attempt():
    """Первая попытка (attempts_count=0) → slots[0]."""
    now = _msk_to_utc(2026, 5, 1, 9, 0)
    eta = schedule_next_attempt(["10:00", "11:00", "14:00"], 0, now)
    assert eta == _msk_to_utc(2026, 5, 1, 10, 0)


def test_schedule_with_slots_second_attempt():
    """После первой попытки (attempts_count=1) → slots[1]."""
    now = _msk_to_utc(2026, 5, 1, 10, 30)
    eta = schedule_next_attempt(["10:00", "11:00", "14:00"], 1, now)
    assert eta == _msk_to_utc(2026, 5, 1, 11, 0)


def test_schedule_with_slots_exhausted():
    """attempts_count >= len(slots) → None (нет следующей попытки)."""
    now = _msk_to_utc(2026, 5, 1, 14, 0)
    assert schedule_next_attempt(["10:00", "11:00", "14:00"], 3, now) is None


def test_schedule_fallback_first_attempt():
    """Без слотов первая попытка идёт через next_dispatch_time."""
    now = _msk_to_utc(2026, 5, 1, 10, 0)  # внутри окна
    assert schedule_next_attempt(None, 0, now) == now


def test_schedule_fallback_retry_uses_backoff():
    """Без слотов retry получает backoff."""
    now = _msk_to_utc(2026, 5, 1, 10, 0)
    eta = schedule_next_attempt(None, 1, now)
    expected = _msk_to_utc(2026, 5, 1, 10, 30)  # +30 мин
    assert eta == expected


def test_schedule_fallback_exhausted():
    """Без слотов после max_attempts → None."""
    assert schedule_next_attempt(None, 3, _msk_to_utc(2026, 5, 1, 10, 0)) is None


def test_effective_max_attempts():
    """С слотами лимит = их количество, без слотов — глобальный (3)."""
    assert effective_max_attempts(["10:00", "11:00"]) == 2
    assert effective_max_attempts(["10:00", "11:00", "14:00", "16:00"]) == 4
    assert effective_max_attempts(None) == 3
