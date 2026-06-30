"""Сервисный слой создания/отмены брони.

Вынесен из хендлеров, чтобы:
- покрыть юнит-тестами без aiogram Callback/Message объектов;
- держать в одном месте защиту от двойного бронирования слота.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.metrics import bookings_cancelled_total, bookings_created_total, bookings_rejected_total
from db.models import Booking, BookingStatus, Client

MAX_ACTIVE_BOOKINGS_PER_CLIENT = 3


class SlotTakenError(Exception):
    """Слот занят — либо уже забронирован, либо забронирован прямо во время этого запроса."""


class ClientNotFoundError(Exception):
    """В БД нет клиента с таким telegram_id (теоретически не должно случаться после /start)."""


class BookingNotFoundError(Exception):
    """Брони с таким id нет, либо она принадлежит другому клиенту, либо уже не активна."""


class TooManyActiveBookingsError(Exception):
    """У клиента уже MAX_ACTIVE_BOOKINGS_PER_CLIENT активных записей — защита от заполнения расписания одним человеком."""


async def create_booking(
    session: AsyncSession,
    *,
    telegram_id: int,
    master_id: int,
    service_id: int,
    start_at: datetime,
    end_at: datetime,
    price_kopecks: int,
) -> Booking:
    """Создать активную бронь. Бросает SlotTakenError, если слот уже занят.

    Защита двухуровневая: сначала логический overlap-чек (даёт быстрый и
    понятный ответ в большинстве случаев), затем БД-уникальный индекс
    (`uq_active_master_slot`) как последняя линия защиты от гонки между
    двумя почти одновременными подтверждениями на один и тот же слот.
    """
    client = await session.scalar(select(Client).where(Client.telegram_id == telegram_id))
    if client is None:
        bookings_rejected_total.labels(reason="client_not_found").inc()
        raise ClientNotFoundError(telegram_id)

    active_count = await session.scalar(
        select(func.count())
        .select_from(Booking)
        .where(Booking.client_id == client.id, Booking.status == BookingStatus.ACTIVE)
    )
    if active_count >= MAX_ACTIVE_BOOKINGS_PER_CLIENT:
        bookings_rejected_total.labels(reason="too_many_active").inc()
        raise TooManyActiveBookingsError(client.id, active_count)

    overlap = await session.scalar(
        select(Booking).where(
            Booking.master_id == master_id,
            Booking.status == BookingStatus.ACTIVE,
            Booking.start_at < end_at,
            Booking.end_at > start_at,
        )
    )
    if overlap is not None:
        bookings_rejected_total.labels(reason="slot_taken").inc()
        raise SlotTakenError(master_id, start_at)

    booking = Booking(
        client_id=client.id,
        master_id=master_id,
        service_id=service_id,
        start_at=start_at,
        end_at=end_at,
        price_kopecks=price_kopecks,
        status=BookingStatus.ACTIVE,
    )
    session.add(booking)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        bookings_rejected_total.labels(reason="slot_taken_race").inc()
        raise SlotTakenError(master_id, start_at) from exc

    await session.refresh(booking)
    bookings_created_total.inc()
    return booking


async def cancel_booking(
    session: AsyncSession, *, telegram_id: int, booking_id: int
) -> Booking:
    """Отменить активную бронь клиента. Возвращает обновлённую бронь.

    Бросает BookingNotFoundError, если брони нет, она не активна или
    принадлежит другому клиенту (намеренно не различаем эти случаи в
    ответе пользователю — не даём enumerate чужие booking_id).
    """
    booking = await session.get(Booking, booking_id)
    client = await session.scalar(select(Client).where(Client.telegram_id == telegram_id))

    if (
        booking is None
        or client is None
        or booking.client_id != client.id
        or booking.status != BookingStatus.ACTIVE
    ):
        raise BookingNotFoundError(booking_id)

    booking.status = BookingStatus.CANCELLED_CLIENT
    await session.commit()
    await session.refresh(booking)
    bookings_cancelled_total.inc()
    return booking
