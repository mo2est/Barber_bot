"""Напоминания клиентам за час до визита через APScheduler."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from bot import texts
from bot.metrics import reminders_failed_total, reminders_sent_total
from db.models import Booking, BookingStatus, Client, Master, Service
from db.session import async_session_factory

log = logging.getLogger("bot.reminders")

REMINDER_LEAD = timedelta(hours=1)


def _job_id(booking_id: int) -> str:
    return f"reminder_{booking_id}"


async def schedule_reminder(
    scheduler: AsyncIOScheduler, bot: Bot, booking_id: int, start_at_utc: datetime
) -> None:
    """Поставить задачу напоминания и запомнить её id в брони."""
    run_date = start_at_utc.replace(tzinfo=timezone.utc) - REMINDER_LEAD
    if run_date <= datetime.now(timezone.utc):
        return  # запись слишком близко — напоминание не успеет сработать

    job_id = _job_id(booking_id)
    scheduler.add_job(
        send_reminder,
        trigger="date",
        run_date=run_date,
        args=[bot, booking_id],
        id=job_id,
        replace_existing=True,
    )

    async with async_session_factory() as session:
        booking = await session.get(Booking, booking_id)
        if booking is not None:
            booking.reminder_job_id = job_id
            await session.commit()


def cancel_reminder(scheduler: AsyncIOScheduler, job_id: str | None) -> None:
    """Снять задачу напоминания, если она была поставлена."""
    if not job_id:
        return
    job = scheduler.get_job(job_id)
    if job is not None:
        job.remove()


async def send_reminder(bot: Bot, booking_id: int) -> None:
    """Отправить клиенту напоминание о записи (вызывается APScheduler'ом)."""
    async with async_session_factory() as session:
        booking = await session.get(Booking, booking_id)
        if booking is None or booking.status != BookingStatus.ACTIVE:
            return

        client = await session.get(Client, booking.client_id)
        master = await session.get(Master, booking.master_id)
        service = await session.get(Service, booking.service_id)

        if client is None or master is None or service is None:
            return

    try:
        await bot.send_message(
            client.telegram_id,
            texts.REMINDER_TEXT.format(service=service.name, master=master.name),
        )
        reminders_sent_total.inc()
    except TelegramAPIError:
        # Клиент заблокировал бота / удалил чат / другая ошибка Telegram —
        # это не повод класть весь шедулер падением необработанного исключения.
        reminders_failed_total.inc()
        log.warning(
            "Не удалось отправить напоминание booking_id=%s telegram_id=%s",
            booking_id, client.telegram_id, exc_info=True,
        )


async def resync_reminders(scheduler: AsyncIOScheduler, bot: Bot) -> int:
    """Восстановить напоминания для будущих активных броней при старте бота.

    Нужно на случай, если jobstore не персистентный (in-memory) или был
    потерян: без этого вызова брони, созданные до перезапуска, остались
    бы без напоминания. Если задача уже есть в шедулере (персистентный
    jobstore) — add_job с replace_existing просто её обновит тем же id.

    Возвращает количество восстановленных задач (для лога при старте).
    """
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    restored = 0

    async with async_session_factory() as session:
        bookings = list(
            await session.scalars(
                select(Booking).where(
                    Booking.status == BookingStatus.ACTIVE,
                    Booking.start_at > now_utc,
                )
            )
        )

    for booking in bookings:
        run_date = booking.start_at.replace(tzinfo=timezone.utc) - REMINDER_LEAD
        if run_date <= datetime.now(timezone.utc):
            continue
        await schedule_reminder(scheduler, bot, booking.id, booking.start_at)
        restored += 1

    return restored
