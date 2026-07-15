"""Просмотр и отмена активных записей клиента."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot import texts
from bot.callbacks import CancelBookingCb
from bot.config import settings
from bot.keyboards.client import my_bookings_kb
from bot.services.booking import BookingNotFoundError
from bot.services.booking import cancel_booking as cancel_booking_service
from bot.services.format import format_price, format_when
from bot.services.reminders import cancel_reminder
from db.models import Booking, BookingStatus, Client
from db.session import async_session_factory

router = Router(name="my_bookings")


async def _active_bookings(session, telegram_id: int) -> list[Booking]:
    client = await session.scalar(select(Client).where(Client.telegram_id == telegram_id))
    if client is None:
        return []
    return list(
        await session.scalars(
            select(Booking)
            .options(selectinload(Booking.master), selectinload(Booking.service))
            .where(Booking.client_id == client.id, Booking.status == BookingStatus.ACTIVE)
            .order_by(Booking.start_at)
        )
    )


@router.message(F.text.in_({texts.BTN_MY_BOOKINGS, texts.BTN_CANCEL}))
async def list_bookings(message: Message) -> None:
    """Показать активные записи клиента с кнопками отмены."""
    async with async_session_factory() as session:
        bookings = await _active_bookings(session, message.from_user.id)
        if not bookings:
            await message.answer(texts.NO_ACTIVE_BOOKINGS)
            return

        lines = [texts.MY_BOOKINGS_HEADER, ""]
        for b in bookings:
            lines.append(
                texts.BOOKING_LINE.format(
                    when=format_when(b.start_at, settings.timezone),
                    service=b.service.name if b.service else "?",
                    master=b.master.name if b.master else "?",
                    price=format_price(b.price_kopecks),
                )
            )

    await message.answer(
        "\n".join(lines), reply_markup=my_bookings_kb(bookings, settings.timezone)
    )


@router.callback_query(CancelBookingCb.filter())
async def cancel_booking_handler(
    callback: CallbackQuery,
    callback_data: CancelBookingCb,
    scheduler: AsyncIOScheduler,
) -> None:
    """Отменить запись по кнопке под списком «Мои записи»."""
    try:
        async with async_session_factory() as session:
            booking = await cancel_booking_service(
                session,
                telegram_id=callback.from_user.id,
                booking_id=callback_data.booking_id,
            )
    except BookingNotFoundError:
        await callback.answer(texts.BOOKING_NOT_FOUND, show_alert=True)
        return

    # reminder_job_id не трогается при отмене — берём его из уже отменённой брони
    cancel_reminder(scheduler, booking.reminder_job_id)

    when = format_when(booking.start_at, settings.timezone)
    await callback.answer()
    await callback.message.edit_text(texts.BOOKING_CANCELLED.format(when=when))
