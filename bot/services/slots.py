"""Расчёт свободных слотов записи для мастера на конкретный день.

Алгоритм: берём рабочие часы мастера на день недели (WorkingHours),
вычитаем перерывы/отпуска (TimeOff) и уже существующие активные брони
(Booking), нарезаем остаток сеткой по SLOT_STEP_MINUTES и оставляем
только те слоты, куда услуга целиком помещается до конца рабочего дня.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Booking, BookingStatus, TimeOff, WorkingHours

SLOT_STEP_MINUTES = 15
MIN_LEAD_MINUTES = 60  # нельзя записаться позже чем за час до начала

_WEEKDAY_CODES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _intervals_overlap(
    a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime
) -> bool:
    return a_start < b_end and b_start < a_end


async def get_free_slots(
    session: AsyncSession,
    master_id: int,
    duration_minutes: int,
    target_date: date,
    tz_name: str,
) -> list[datetime]:
    """Вернуть список свободных стартов слотов (UTC, naive) для мастера на дату."""
    tz = ZoneInfo(tz_name)

    weekday_code = _WEEKDAY_CODES[target_date.weekday()]
    working_hours = await session.scalar(
        select(WorkingHours).where(
            WorkingHours.master_id == master_id,
            WorkingHours.weekday == weekday_code,
        )
    )
    if working_hours is None:
        return []  # выходной

    work_start_local = datetime.combine(
        target_date, working_hours.start_time, tzinfo=tz
    )
    work_end_local = datetime.combine(target_date, working_hours.end_time, tzinfo=tz)

    # Окно дня в UTC (naive, как храним в БД) — для выборки перекрывающихся записей.
    day_start_utc = work_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    day_end_utc = work_end_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    busy: list[tuple[datetime, datetime]] = []

    time_offs = await session.scalars(
        select(TimeOff).where(
            TimeOff.master_id == master_id,
            TimeOff.start_at < day_end_utc,
            TimeOff.end_at > day_start_utc,
        )
    )
    busy.extend((t.start_at, t.end_at) for t in time_offs)

    bookings = await session.scalars(
        select(Booking).where(
            Booking.master_id == master_id,
            Booking.status == BookingStatus.ACTIVE,
            Booking.start_at < day_end_utc,
            Booking.end_at > day_start_utc,
        )
    )
    busy.extend((b.start_at, b.end_at) for b in bookings)

    now_utc = datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)
    earliest_allowed = now_utc + timedelta(minutes=MIN_LEAD_MINUTES)

    slots: list[datetime] = []
    cursor_local = work_start_local
    step = timedelta(minutes=SLOT_STEP_MINUTES)
    service_len = timedelta(minutes=duration_minutes)

    while cursor_local + service_len <= work_end_local:
        slot_start_utc = cursor_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        slot_end_utc = slot_start_utc + service_len

        if slot_start_utc >= earliest_allowed and not any(
            _intervals_overlap(slot_start_utc, slot_end_utc, b_start, b_end)
            for b_start, b_end in busy
        ):
            slots.append(slot_start_utc)

        cursor_local += step

    return slots
