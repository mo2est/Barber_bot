"""Тесты парсинга блокировок времени (bot/services/timeoff.py)."""

from __future__ import annotations

import pytest

from bot.services.timeoff import (
    TimeoffParseError,
    TimeoffRangeError,
    create_timeoff,
    parse_timeoff_text,
)


def test_parse_valid_text():
    start, end, reason = parse_timeoff_text("2026-06-25 14:00 16:00 Обед")
    assert start.hour == 14 and end.hour == 16
    assert reason == "Обед"


def test_parse_garbage_raises():
    with pytest.raises(TimeoffParseError):
        parse_timeoff_text("это не похоже на формат")


def test_parse_end_before_start_raises():
    with pytest.raises(TimeoffRangeError):
        parse_timeoff_text("2026-06-25 16:00 14:00 Обед")


async def test_create_timeoff_converts_to_utc(session, master):
    import datetime as dt

    start_local = dt.datetime(2026, 6, 25, 14, 0)
    end_local = dt.datetime(2026, 6, 25, 16, 0)

    timeoff = await create_timeoff(
        session, master_id=master.id, start_local=start_local, end_local=end_local,
        tz_name="Europe/Moscow", reason="Обед",
    )
    # Москва летом UTC+3 -> 14:00 локал = 11:00 UTC
    assert timeoff.start_at.hour == 11
    assert timeoff.end_at.hour == 13
