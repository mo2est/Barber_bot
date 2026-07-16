"""Админ-панель: записи на сегодня, управление мастерами/услугами, блокировка времени.

Доступ — только для telegram_id из settings.admin_ids. Реализована как
команды/инлайн-кнопки в самом боте (без отдельной Django-админки) —
быстрее для портфолио-демо и не требует поднимать второй сервис.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot import texts
from bot.callbacks import (
    AdminDeleteTimeoffCb,
    AdminMenuCb,
    AdminTimeoffMasterCb,
    AdminToggleMasterCb,
    AdminToggleServiceCb,
)
from bot.config import settings
from bot.keyboards.admin import (
    admin_masters_kb,
    admin_menu_kb,
    admin_services_kb,
    admin_timeoff_list_kb,
    admin_timeoff_masters_kb,
)
from bot.services.format import to_local
from bot.services.timeoff import (
    TimeoffParseError,
    TimeoffRangeError,
    create_timeoff,
    parse_timeoff_text,
)
from bot.services.ui import remove_inline_kb
from bot.states import AdminStates
from db.models import Booking, BookingStatus, Master, Service, TimeOff
from db.session import async_session_factory

router = Router(name="admin")


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


@router.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext) -> None:
    """`/admin` — открыть админ-панель (только для ADMIN_IDS)."""
    if not _is_admin(message.from_user.id):
        await message.answer(texts.ADMIN_ONLY)
        return

    # Незавершённый сценарий блокировки: снимаем клавиатуру со старого
    # промпта, чтобы кнопки выбора мастера не остались висеть в чате.
    data = await state.get_data()
    await remove_inline_kb(message.bot, message.chat.id, data.get("prompt_msg_id"))
    await state.clear()
    await message.answer(texts.ADMIN_MENU, reply_markup=admin_menu_kb())


async def _render_today(session) -> str:
    tz = ZoneInfo(settings.timezone)
    today_local = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    day_start_utc = today_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    day_end_utc = (today_local + timedelta(days=1)).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    bookings = list(
        await session.scalars(
            select(Booking)
            .options(
                selectinload(Booking.master),
                selectinload(Booking.service),
                selectinload(Booking.client),
            )
            .where(
                Booking.status == BookingStatus.ACTIVE,
                Booking.start_at >= day_start_utc,
                Booking.start_at < day_end_utc,
            )
            .order_by(Booking.start_at)
        )
    )
    if not bookings:
        return texts.ADMIN_NO_BOOKINGS_TODAY

    lines = [texts.ADMIN_TODAY_HEADER]
    for b in bookings:
        lines.append(
            texts.ADMIN_BOOKING_LINE.format(
                time=to_local(b.start_at, settings.timezone).strftime("%H:%M"),
                service=b.service.name if b.service else "?",
                master=b.master.name if b.master else "?",
                client=(b.client.first_name or b.client.username or b.client.telegram_id) if b.client else "?",
            )
        )
    return "\n".join(lines)


@router.callback_query(AdminMenuCb.filter())
async def admin_menu_action(
    callback: CallbackQuery, callback_data: AdminMenuCb, state: FSMContext
) -> None:
    """Обработка пунктов главного меню админ-панели."""
    if not _is_admin(callback.from_user.id):
        await callback.answer(texts.ADMIN_ONLY, show_alert=True)
        return

    await callback.answer()

    if callback_data.action == "today":
        async with async_session_factory() as session:
            text = await _render_today(session)
        await callback.message.edit_text(text)
        return

    if callback_data.action == "masters":
        async with async_session_factory() as session:
            masters = list(await session.scalars(select(Master).order_by(Master.id)))
        await callback.message.edit_text(
            texts.ADMIN_MASTERS_HEADER, reply_markup=admin_masters_kb(masters)
        )
        return

    if callback_data.action == "services":
        async with async_session_factory() as session:
            services = list(await session.scalars(select(Service).order_by(Service.id)))
        await callback.message.edit_text(
            texts.ADMIN_SERVICES_HEADER, reply_markup=admin_services_kb(services)
        )
        return

    if callback_data.action == "timeoff":
        async with async_session_factory() as session:
            masters = list(
                await session.scalars(
                    select(Master).where(Master.is_active.is_(True)).order_by(Master.id)
                )
            )
        if not masters:
            await callback.message.edit_text(texts.ADMIN_NO_BOOKINGS_TODAY)
            return
        await state.set_state(AdminStates.timeoff_choosing_master)
        await state.update_data(prompt_msg_id=callback.message.message_id)
        await callback.message.edit_text(
            texts.ADMIN_TIMEOFF_CHOOSE_MASTER, reply_markup=admin_timeoff_masters_kb(masters)
        )
        return

    if callback_data.action == "timeoff_list":
        async with async_session_factory() as session:
            text, kb = await _render_timeoff_list(session)
        if kb is None:
            await callback.message.edit_text(text)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
        return


async def _render_timeoff_list(session):
    now_utc = datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)
    timeoffs = list(
        await session.scalars(
            select(TimeOff).where(TimeOff.end_at > now_utc).order_by(TimeOff.start_at)
        )
    )
    if not timeoffs:
        return texts.ADMIN_TIMEOFF_LIST_EMPTY, None

    masters = list(await session.scalars(select(Master)))
    masters_by_id = {m.id: m for m in masters}
    return texts.ADMIN_TIMEOFF_LIST_HEADER, admin_timeoff_list_kb(
        timeoffs, masters_by_id, settings.timezone
    )


@router.callback_query(AdminToggleMasterCb.filter())
async def toggle_master(callback: CallbackQuery, callback_data: AdminToggleMasterCb) -> None:
    """Включить/выключить мастера (is_active)."""
    if not _is_admin(callback.from_user.id):
        await callback.answer(texts.ADMIN_ONLY, show_alert=True)
        return

    async with async_session_factory() as session:
        master = await session.get(Master, callback_data.master_id)
        if master is None:
            await callback.answer(texts.BOOKING_NOT_FOUND, show_alert=True)
            return
        master.is_active = not master.is_active
        await session.commit()

        masters = list(await session.scalars(select(Master).order_by(Master.id)))

    await callback.answer(
        texts.ADMIN_TOGGLED_MASTER.format(
            name=master.name,
            state=texts.ADMIN_STATE_ON if master.is_active else texts.ADMIN_STATE_OFF,
        )
    )
    await callback.message.edit_text(
        texts.ADMIN_MASTERS_HEADER, reply_markup=admin_masters_kb(masters)
    )


@router.callback_query(AdminToggleServiceCb.filter())
async def toggle_service(callback: CallbackQuery, callback_data: AdminToggleServiceCb) -> None:
    """Включить/выключить услугу (is_active)."""
    if not _is_admin(callback.from_user.id):
        await callback.answer(texts.ADMIN_ONLY, show_alert=True)
        return

    async with async_session_factory() as session:
        service = await session.get(Service, callback_data.service_id)
        if service is None:
            await callback.answer(texts.BOOKING_NOT_FOUND, show_alert=True)
            return
        service.is_active = not service.is_active
        await session.commit()

        services = list(await session.scalars(select(Service).order_by(Service.id)))

    await callback.answer(
        texts.ADMIN_TOGGLED_SERVICE.format(
            name=service.name,
            state=texts.ADMIN_STATE_ON if service.is_active else texts.ADMIN_STATE_OFF,
        )
    )
    await callback.message.edit_text(
        texts.ADMIN_SERVICES_HEADER, reply_markup=admin_services_kb(services)
    )


@router.callback_query(AdminDeleteTimeoffCb.filter())
async def delete_timeoff(callback: CallbackQuery, callback_data: AdminDeleteTimeoffCb) -> None:
    """Удалить блокировку времени из списка."""
    if not _is_admin(callback.from_user.id):
        await callback.answer(texts.ADMIN_ONLY, show_alert=True)
        return

    async with async_session_factory() as session:
        timeoff = await session.get(TimeOff, callback_data.timeoff_id)
        if timeoff is not None:
            await session.delete(timeoff)
            await session.commit()

        text, kb = await _render_timeoff_list(session)

    await callback.answer(texts.ADMIN_TIMEOFF_DELETED)
    if kb is None:
        await callback.message.edit_text(text)
    else:
        await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(AdminStates.timeoff_choosing_master, AdminTimeoffMasterCb.filter())
async def timeoff_choose_master(
    callback: CallbackQuery, callback_data: AdminTimeoffMasterCb, state: FSMContext
) -> None:
    """Мастер для блокировки выбран — просим прислать диапазон текстом."""
    await state.update_data(master_id=callback_data.master_id)
    await state.set_state(AdminStates.timeoff_entering_range)
    await callback.answer()
    await callback.message.edit_text(
        texts.ADMIN_TIMEOFF_ENTER_RANGE.format(tz=settings.timezone)
    )


@router.message(AdminStates.timeoff_entering_range, F.text)
async def timeoff_enter_range(message: Message, state: FSMContext) -> None:
    """Текст с диапазоном получен — парсим и создаём TimeOff."""
    if not _is_admin(message.from_user.id):
        return

    try:
        start_local, end_local, reason = parse_timeoff_text(message.text)
    except (TimeoffParseError, TimeoffRangeError):
        await message.answer(texts.ADMIN_TIMEOFF_BAD_FORMAT)
        return

    data = await state.get_data()
    async with async_session_factory() as session:
        master = await session.get(Master, data["master_id"])
        await create_timeoff(
            session,
            master_id=data["master_id"],
            start_local=start_local,
            end_local=end_local,
            tz_name=settings.timezone,
            reason=reason,
        )

    await state.clear()
    await message.answer(
        texts.ADMIN_TIMEOFF_CREATED.format(
            master=master.name if master else "?",
            start=start_local.strftime("%d.%m.%Y %H:%M"),
            end=end_local.strftime("%H:%M"),
            reason=reason,
        )
    )
