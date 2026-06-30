"""Клавиатуры админ-панели."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.callbacks import (
    AdminDeleteTimeoffCb,
    AdminMenuCb,
    AdminTimeoffMasterCb,
    AdminToggleMasterCb,
    AdminToggleServiceCb,
)
from bot.services.format import to_local
from bot.texts import (
    ADMIN_STATE_OFF,
    ADMIN_STATE_ON,
    ADMIN_TIMEOFF_LIST_LINE,
    BTN_ADMIN_MASTERS,
    BTN_ADMIN_SERVICES,
    BTN_ADMIN_TIMEOFF,
    BTN_ADMIN_TIMEOFF_LIST,
    BTN_ADMIN_TODAY,
)
from db.models import Master, Service, TimeOff


def admin_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_ADMIN_TODAY, callback_data=AdminMenuCb(action="today").pack())],
            [InlineKeyboardButton(text=BTN_ADMIN_MASTERS, callback_data=AdminMenuCb(action="masters").pack())],
            [InlineKeyboardButton(text=BTN_ADMIN_SERVICES, callback_data=AdminMenuCb(action="services").pack())],
            [InlineKeyboardButton(text=BTN_ADMIN_TIMEOFF, callback_data=AdminMenuCb(action="timeoff").pack())],
            [InlineKeyboardButton(text=BTN_ADMIN_TIMEOFF_LIST, callback_data=AdminMenuCb(action="timeoff_list").pack())],
        ]
    )


def admin_masters_kb(masters: list[Master]) -> InlineKeyboardMarkup:
    """Список мастеров с переключателем активности."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"{ADMIN_STATE_ON if m.is_active else ADMIN_STATE_OFF} {m.name}",
                callback_data=AdminToggleMasterCb(master_id=m.id).pack(),
            )
        ]
        for m in masters
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_services_kb(services: list[Service]) -> InlineKeyboardMarkup:
    """Список услуг с переключателем активности."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"{ADMIN_STATE_ON if s.is_active else ADMIN_STATE_OFF} {s.name}",
                callback_data=AdminToggleServiceCb(service_id=s.id).pack(),
            )
        ]
        for s in services
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_timeoff_masters_kb(masters: list[Master]) -> InlineKeyboardMarkup:
    """Выбор мастера для блокировки времени."""
    rows = [
        [
            InlineKeyboardButton(
                text=m.name, callback_data=AdminTimeoffMasterCb(master_id=m.id).pack()
            )
        ]
        for m in masters
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_timeoff_list_kb(
    timeoffs: list[TimeOff], masters_by_id: dict[int, Master], tz_name: str
) -> InlineKeyboardMarkup:
    """Список будущих блокировок — клик по строке удаляет её."""
    rows = []
    for t in timeoffs:
        master = masters_by_id.get(t.master_id)
        label = ADMIN_TIMEOFF_LIST_LINE.format(
            master=master.name if master else "?",
            start=to_local(t.start_at, tz_name).strftime("%d.%m %H:%M"),
            end=to_local(t.end_at, tz_name).strftime("%H:%M"),
            reason=t.reason or "—",
        )
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=AdminDeleteTimeoffCb(timeoff_id=t.id).pack())]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
