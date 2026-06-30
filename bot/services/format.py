"""Мелкие функции форматирования для сообщений бота."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def format_price(kopecks: int) -> str:
    """150000 -> '1500', 150050 -> '1500.50'."""
    rubles = kopecks / 100
    if rubles == int(rubles):
        return str(int(rubles))
    return f"{rubles:.2f}"


def to_local(dt_utc_naive: datetime, tz_name: str) -> datetime:
    """Наивный UTC datetime из БД -> datetime в часовом поясе салона."""
    return dt_utc_naive.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(tz_name))


def format_when(dt_utc_naive: datetime, tz_name: str) -> str:
    """Наивный UTC datetime -> 'дд.мм чч:мм' в локальном времени салона."""
    return to_local(dt_utc_naive, tz_name).strftime("%d.%m.%Y %H:%M")
