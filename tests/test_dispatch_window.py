"""Tests for dispatch window logic (9:00–21:00 Europe/Moscow by default)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.dispatch_window import is_within_window, next_dispatch_time


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
