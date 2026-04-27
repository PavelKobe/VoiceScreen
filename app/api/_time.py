"""Datetime serialisation helpers for API responses.

Все timestamp'ы в БД хранятся как naive UTC (мы пишем `datetime.utcnow()`).
При сериализации в JSON ISO нужно добавлять `Z`, чтобы фронт корректно
интерпретировал значение как UTC и отрендерил в локальной зоне (МСК).
"""

from __future__ import annotations

from datetime import datetime


def iso_utc(dt: datetime | None) -> str | None:
    """Сериализовать naive UTC datetime как ISO с суффиксом Z."""
    if dt is None:
        return None
    return f"{dt.isoformat()}Z"
