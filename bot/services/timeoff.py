"""Парсинг и создание блокировок времени (TimeOff) администратором."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TimeOff

_PATTERN = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})\s+(\d{1,2}:\d{2})\s+(.+?)\s*$"
)


class TimeoffParseError(Exception):
    """Текст не соответствует ожидаемому формату."""


class TimeoffRangeError(Exception):
    """Конец интервала раньше или равен началу."""


def parse_timeoff_text(raw: str) -> tuple[datetime, datetime, str]:
    """'2026-06-25 14:00 16:00 Обед' -> (naive start, naive end, 'Обед').

    Возвращаемые datetime — наивные, в часовом поясе салона (конвертация
    в UTC делается отдельно в create_timeoff, где известен tz_name).
    """
    match = _PATTERN.match(raw)
    if not match:
        raise TimeoffParseError(raw)

    date_str, start_str, end_str, reason = match.groups()
    try:
        start = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M")
        end = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise TimeoffParseError(raw) from exc

    if end <= start:
        raise TimeoffRangeError(raw)

    return start, end, reason


async def create_timeoff(
    session: AsyncSession,
    *,
    master_id: int,
    start_local: datetime,
    end_local: datetime,
    tz_name: str,
    reason: str,
) -> TimeOff:
    """Создать блокировку времени, переведя локальное время салона в UTC."""
    tz = ZoneInfo(tz_name)
    start_utc = start_local.replace(tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    end_utc = end_local.replace(tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    timeoff = TimeOff(master_id=master_id, start_at=start_utc, end_at=end_utc, reason=reason)
    session.add(timeoff)
    await session.commit()
    await session.refresh(timeoff)
    return timeoff
