"""FSM-сценарий записи: услуга → мастер → дата → слот → подтверждение."""

from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot import texts
from bot.callbacks import ConfirmCb, DateCb, MasterCb, ServiceCb, SlotCb
from bot.config import settings
from bot.keyboards.client import (
    confirm_kb,
    dates_kb,
    main_menu_kb,
    masters_kb,
    services_kb,
    slots_kb,
)
from bot.services.booking import (
    ClientNotFoundError,
    SlotTakenError,
    TooManyActiveBookingsError,
    create_booking,
)
from bot.services.format import format_price, format_when
from bot.services.reminders import schedule_reminder
from bot.services.slots import get_free_slots
from bot.states import BookingStates
from db.models import Master, MasterService, Service
from db.session import async_session_factory

router = Router(name="booking")


@router.message(F.text == texts.BTN_BOOK)
async def start_booking(message: Message, state: FSMContext) -> None:
    """Кнопка «Записаться» — показываем список услуг."""
    async with async_session_factory() as session:
        services = list(
            await session.scalars(
                select(Service).where(Service.is_active.is_(True)).order_by(Service.id)
            )
        )

    if not services:
        await message.answer(texts.NOT_IMPLEMENTED)
        return

    await state.set_state(BookingStates.choosing_service)
    await message.answer(texts.CHOOSE_SERVICE, reply_markup=services_kb(services))


@router.callback_query(BookingStates.choosing_service, ServiceCb.filter())
async def choose_service(
    callback: CallbackQuery, callback_data: ServiceCb, state: FSMContext
) -> None:
    """Услуга выбрана — показываем мастеров, которые её оказывают."""
    async with async_session_factory() as session:
        service = await session.get(Service, callback_data.service_id)
        if service is None or not service.is_active:
            await callback.answer(texts.BOOKING_NOT_FOUND, show_alert=True)
            return

        masters = list(
            await session.scalars(
                select(Master)
                .join(MasterService, MasterService.master_id == Master.id)
                .where(
                    MasterService.service_id == service.id,
                    Master.is_active.is_(True),
                )
                .order_by(Master.id)
            )
        )

    if not masters:
        await callback.answer()
        await callback.message.edit_text(texts.NO_MASTERS_FOR_SERVICE)
        await state.clear()
        return

    await state.update_data(service_id=service.id, service_name=service.name)
    await state.set_state(BookingStates.choosing_master)
    await callback.answer()
    await callback.message.edit_text(texts.CHOOSE_MASTER, reply_markup=masters_kb(masters))


@router.callback_query(BookingStates.choosing_master, MasterCb.filter())
async def choose_master(
    callback: CallbackQuery, callback_data: MasterCb, state: FSMContext
) -> None:
    """Мастер выбран — показываем даты."""
    data = await state.get_data()

    async with async_session_factory() as session:
        master = await session.get(Master, callback_data.master_id)
        link = await session.scalar(
            select(MasterService)
            .options(selectinload(MasterService.service))
            .where(
                MasterService.master_id == callback_data.master_id,
                MasterService.service_id == data["service_id"],
            )
        )
        if master is None or link is None:
            await callback.answer(texts.BOOKING_NOT_FOUND, show_alert=True)
            return

        price_kopecks = link.effective_price_kopecks
        duration_minutes = link.effective_duration_minutes

    await state.update_data(
        master_id=master.id,
        master_name=master.name,
        price_kopecks=price_kopecks,
        duration_minutes=duration_minutes,
    )
    await state.set_state(BookingStates.choosing_date)
    await callback.answer()
    try:
        await callback.message.edit_text(texts.CHOOSE_DATE, reply_markup=dates_kb())
    except TelegramBadRequest:
        pass


@router.callback_query(BookingStates.choosing_date, DateCb.filter())
async def choose_date(
    callback: CallbackQuery, callback_data: DateCb, state: FSMContext
) -> None:
    """Дата выбрана — показываем свободные слоты."""
    data = await state.get_data()
    target_date = date_cls.fromisoformat(callback_data.date_iso)

    async with async_session_factory() as session:
        slots = await get_free_slots(
            session=session,
            master_id=data["master_id"],
            duration_minutes=data["duration_minutes"],
            target_date=target_date,
            tz_name=settings.timezone,
        )

    await callback.answer()
    if not slots:
        await callback.message.edit_text(
            texts.NO_SLOTS_FOR_DATE, reply_markup=dates_kb()
        )
        return

    await state.update_data(date_iso=callback_data.date_iso)
    await state.set_state(BookingStates.choosing_slot)
    await callback.message.edit_text(
        texts.CHOOSE_SLOT.format(date=target_date.strftime("%d.%m.%Y")),
        reply_markup=slots_kb(slots, settings.timezone),
    )


@router.callback_query(BookingStates.choosing_slot, SlotCb.filter())
async def choose_slot(
    callback: CallbackQuery, callback_data: SlotCb, state: FSMContext
) -> None:
    """Слот выбран — показываем подтверждение."""
    start_utc = datetime.utcfromtimestamp(callback_data.start_ts)
    data = await state.get_data()

    await state.update_data(start_ts=callback_data.start_ts)
    await state.set_state(BookingStates.confirming)

    text = texts.BOOKING_CONFIRM.format(
        service=data["service_name"],
        master=data["master_name"],
        when=format_when(start_utc, settings.timezone),
        price=format_price(data["price_kopecks"]),
    )
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=confirm_kb())


@router.callback_query(BookingStates.confirming, ConfirmCb.filter())
async def confirm_booking(
    callback: CallbackQuery,
    callback_data: ConfirmCb,
    state: FSMContext,
    scheduler: AsyncIOScheduler,
) -> None:
    """Финальное подтверждение: создаём бронь или отменяем сценарий."""
    if callback_data.action != "yes":
        await state.clear()
        await callback.answer()
        await callback.message.edit_text(texts.BOOKING_FLOW_CANCELLED)
        return

    data = await state.get_data()
    # Очищаем состояние сразу: повторный клик «Подтвердить» (двойной тап,
    # повтор после таймаута сети) больше не пройдёт фильтр по состоянию
    # и не попадёт в этот хендлер второй раз.
    await state.clear()

    start_utc = datetime.utcfromtimestamp(data["start_ts"])
    duration_minutes = data["duration_minutes"]
    end_utc = start_utc + timedelta(minutes=duration_minutes)

    try:
        async with async_session_factory() as session:
            booking = await create_booking(
                session,
                telegram_id=callback.from_user.id,
                master_id=data["master_id"],
                service_id=data["service_id"],
                start_at=start_utc,
                end_at=end_utc,
                price_kopecks=data["price_kopecks"],
            )
    except ClientNotFoundError:
        await callback.answer(texts.BOOKING_NOT_FOUND, show_alert=True)
        return
    except SlotTakenError:
        await callback.answer()
        await callback.message.edit_text(texts.NO_SLOTS_FOR_DATE)
        return
    except TooManyActiveBookingsError:
        await callback.answer()
        await callback.message.edit_text(texts.TOO_MANY_ACTIVE_BOOKINGS)
        return

    await callback.answer()
    await callback.message.edit_text(
        texts.BOOKING_CREATED.format(
            service=data["service_name"],
            master=data["master_name"],
            when=format_when(start_utc, settings.timezone),
        )
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_kb())

    await schedule_reminder(scheduler, callback.bot, booking.id, start_utc)
