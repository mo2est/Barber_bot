"""Тесты сервисного слоя bookings (bot/services/booking.py)."""

from __future__ import annotations

import datetime as dt

import pytest

from bot.services.booking import (
    MAX_ACTIVE_BOOKINGS_PER_CLIENT,
    BookingNotFoundError,
    ClientNotFoundError,
    SlotTakenError,
    TooManyActiveBookingsError,
    cancel_booking,
    create_booking,
)
from db.models import BookingStatus


def _slot():
    start = dt.datetime(2030, 1, 7, 12, 0)  # понедельник, далёкое будущее — без коллизий с "сейчас"
    end = start + dt.timedelta(minutes=45)
    return start, end


async def test_create_booking_success(session, master, service, client):
    start, end = _slot()
    booking = await create_booking(
        session,
        telegram_id=client.telegram_id,
        master_id=master.id,
        service_id=service.id,
        start_at=start,
        end_at=end,
        price_kopecks=150000,
    )
    assert booking.id is not None
    assert booking.status == BookingStatus.ACTIVE
    assert booking.client_id == client.id


async def test_create_booking_overlap_rejected(session, master, service, client):
    start, end = _slot()
    await create_booking(
        session, telegram_id=client.telegram_id, master_id=master.id,
        service_id=service.id, start_at=start, end_at=end, price_kopecks=150000,
    )

    with pytest.raises(SlotTakenError):
        await create_booking(
            session, telegram_id=client.telegram_id, master_id=master.id,
            service_id=service.id, start_at=start, end_at=end, price_kopecks=150000,
        )


async def test_create_booking_unknown_client_raises(session, master, service):
    start, end = _slot()
    with pytest.raises(ClientNotFoundError):
        await create_booking(
            session, telegram_id=999999, master_id=master.id,
            service_id=service.id, start_at=start, end_at=end, price_kopecks=150000,
        )


async def test_cancel_booking_success(session, master, service, client):
    start, end = _slot()
    booking = await create_booking(
        session, telegram_id=client.telegram_id, master_id=master.id,
        service_id=service.id, start_at=start, end_at=end, price_kopecks=150000,
    )

    cancelled = await cancel_booking(session, telegram_id=client.telegram_id, booking_id=booking.id)
    assert cancelled.status == BookingStatus.CANCELLED_CLIENT


async def test_cancel_booking_frees_slot_for_rebooking(session, master, service, client):
    start, end = _slot()
    booking = await create_booking(
        session, telegram_id=client.telegram_id, master_id=master.id,
        service_id=service.id, start_at=start, end_at=end, price_kopecks=150000,
    )
    await cancel_booking(session, telegram_id=client.telegram_id, booking_id=booking.id)

    # после отмены тот же слот можно забронировать снова
    rebooked = await create_booking(
        session, telegram_id=client.telegram_id, master_id=master.id,
        service_id=service.id, start_at=start, end_at=end, price_kopecks=150000,
    )
    assert rebooked.status == BookingStatus.ACTIVE


async def test_cancel_booking_wrong_client_raises(session, master, service, client):
    from db.models import Client

    other = Client(telegram_id=2, username="other", first_name="Other")
    session.add(other)
    await session.commit()

    start, end = _slot()
    booking = await create_booking(
        session, telegram_id=client.telegram_id, master_id=master.id,
        service_id=service.id, start_at=start, end_at=end, price_kopecks=150000,
    )

    with pytest.raises(BookingNotFoundError):
        await cancel_booking(session, telegram_id=other.telegram_id, booking_id=booking.id)


async def test_cancel_already_cancelled_raises(session, master, service, client):
    start, end = _slot()
    booking = await create_booking(
        session, telegram_id=client.telegram_id, master_id=master.id,
        service_id=service.id, start_at=start, end_at=end, price_kopecks=150000,
    )
    await cancel_booking(session, telegram_id=client.telegram_id, booking_id=booking.id)

    with pytest.raises(BookingNotFoundError):
        await cancel_booking(session, telegram_id=client.telegram_id, booking_id=booking.id)


async def test_too_many_active_bookings_rejected(session, master, service, client):
    base_start, _ = _slot()
    for i in range(MAX_ACTIVE_BOOKINGS_PER_CLIENT):
        start = base_start + dt.timedelta(days=i)
        end = start + dt.timedelta(minutes=45)
        await create_booking(
            session, telegram_id=client.telegram_id, master_id=master.id,
            service_id=service.id, start_at=start, end_at=end, price_kopecks=150000,
        )

    overflow_start = base_start + dt.timedelta(days=MAX_ACTIVE_BOOKINGS_PER_CLIENT)
    overflow_end = overflow_start + dt.timedelta(minutes=45)
    with pytest.raises(TooManyActiveBookingsError):
        await create_booking(
            session, telegram_id=client.telegram_id, master_id=master.id,
            service_id=service.id, start_at=overflow_start, end_at=overflow_end,
            price_kopecks=150000,
        )
