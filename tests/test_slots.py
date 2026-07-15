"""Тесты расчёта свободных слотов (bot/services/slots.py)."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from db.models import Booking, BookingStatus, Master, TimeOff
from bot.services.slots import get_free_slots, MIN_LEAD_MINUTES

TZ = "Europe/Moscow"


def _next_weekday(target_date: dt.date, weekday: int) -> dt.date:
    """Следующая дата с заданным dt.weekday() (0=Пн), начиная с target_date включительно."""
    delta = (weekday - target_date.weekday()) % 7
    return target_date + dt.timedelta(days=delta)


async def test_no_working_hours_returns_empty(session, salon, service):
    m = Master(salon_id=salon.id, name="Без графика", is_active=True)
    session.add(m)
    await session.commit()

    sunday = _next_weekday(dt.date.today() + dt.timedelta(days=14), 6)  # точно выходной
    slots = await get_free_slots(session, m.id, service.duration_minutes, sunday, TZ)
    assert slots == []


async def test_basic_slots_within_working_hours(session, master, service):
    workday = _next_weekday(dt.date.today() + dt.timedelta(days=14), 0)  # понедельник
    slots = await get_free_slots(session, master.id, service.duration_minutes, workday, TZ)

    assert len(slots) > 0
    tz = ZoneInfo(TZ)
    first_local = slots[0].replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    last_local = slots[-1].replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    assert first_local.hour == 10 and first_local.minute == 0
    # последний слот должен укладываться в рабочие часы целиком (до 20:00)
    assert (last_local + dt.timedelta(minutes=service.duration_minutes)).hour <= 20


async def test_timeoff_blocks_overlapping_slots(session, master, service):
    workday = _next_weekday(dt.date.today() + dt.timedelta(days=14), 0)
    tz = ZoneInfo(TZ)

    slots_before = await get_free_slots(session, master.id, service.duration_minutes, workday, TZ)

    block_start_local = dt.datetime.combine(workday, dt.time(10, 0), tzinfo=tz)
    block_end_local = dt.datetime.combine(workday, dt.time(20, 0), tzinfo=tz)
    session.add(
        TimeOff(
            master_id=master.id,
            start_at=block_start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None),
            end_at=block_end_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None),
            reason="full day blocked",
        )
    )
    await session.commit()

    slots_after = await get_free_slots(session, master.id, service.duration_minutes, workday, TZ)
    assert len(slots_before) > 0
    assert slots_after == []


async def test_existing_booking_blocks_overlapping_slot(session, master, service, client):
    workday = _next_weekday(dt.date.today() + dt.timedelta(days=14), 0)

    slots = await get_free_slots(session, master.id, service.duration_minutes, workday, TZ)
    target_slot = slots[0]
    end = target_slot + dt.timedelta(minutes=service.duration_minutes)

    session.add(
        Booking(
            client_id=client.id,
            master_id=master.id,
            service_id=service.id,
            start_at=target_slot,
            end_at=end,
            price_kopecks=service.base_price_kopecks,
            status=BookingStatus.ACTIVE,
        )
    )
    await session.commit()

    slots_after = await get_free_slots(session, master.id, service.duration_minutes, workday, TZ)
    assert target_slot not in slots_after


async def test_cancelled_booking_does_not_block_slot(session, master, service, client):
    workday = _next_weekday(dt.date.today() + dt.timedelta(days=14), 0)

    slots = await get_free_slots(session, master.id, service.duration_minutes, workday, TZ)
    target_slot = slots[0]
    end = target_slot + dt.timedelta(minutes=service.duration_minutes)

    session.add(
        Booking(
            client_id=client.id,
            master_id=master.id,
            service_id=service.id,
            start_at=target_slot,
            end_at=end,
            price_kopecks=service.base_price_kopecks,
            status=BookingStatus.CANCELLED_CLIENT,  # отменена — не должна блокировать
        )
    )
    await session.commit()

    slots_after = await get_free_slots(session, master.id, service.duration_minutes, workday, TZ)
    assert target_slot in slots_after


async def test_lead_time_excludes_too_soon_slots(session, master, service):
    """Сегодняшние слоты ближе MIN_LEAD_MINUTES к текущему моменту не предлагаются."""
    today = dt.date.today()
    # Подстрахуемся: если сегодня не рабочий день мастера — тест неприменим, выходим.
    if today.weekday() == 6:
        return

    slots = await get_free_slots(session, master.id, service.duration_minutes, today, TZ)

    earliest_allowed_utc = (
        dt.datetime.now(ZoneInfo("UTC")).replace(tzinfo=None) + dt.timedelta(minutes=MIN_LEAD_MINUTES)
    )
    for slot in slots:
        assert slot >= earliest_allowed_utc
