"""Клавиатуры для клиентских сценариев."""

from __future__ import annotations

from datetime import date, datetime, timedelta

_WEEKDAYS_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.callbacks import (
    CancelBookingCb,
    ConfirmCb,
    DateCb,
    MasterCb,
    ServiceCb,
    SlotCb,
)
from bot.texts import (
    BTN_BOOK,
    BTN_CANCEL,
    BTN_CANCEL_BOOKING,
    BTN_CONFIRM_NO,
    BTN_CONFIRM_YES,
    BTN_INFO,
    BTN_MY_BOOKINGS,
)
from bot.services.format import to_local
from db.models import Booking, Master, Service

DATE_PICKER_DAYS = 7


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню — постоянная клавиатура внизу экрана."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BOOK)],
            [KeyboardButton(text=BTN_MY_BOOKINGS), KeyboardButton(text=BTN_CANCEL)],
            [KeyboardButton(text=BTN_INFO)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def services_kb(services: list[Service]) -> InlineKeyboardMarkup:
    """Список услуг для выбора при записи."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"{s.name} ({s.duration_minutes} мин)",
                callback_data=ServiceCb(service_id=s.id).pack(),
            )
        ]
        for s in services
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def masters_kb(masters: list[Master]) -> InlineKeyboardMarkup:
    """Список мастеров, оказывающих выбранную услугу."""
    rows = [
        [
            InlineKeyboardButton(
                text=m.name, callback_data=MasterCb(master_id=m.id).pack()
            )
        ]
        for m in masters
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dates_kb() -> InlineKeyboardMarkup:
    """Кнопки с датами на ближайшие DATE_PICKER_DAYS дней."""
    today = date.today()
    rows = []
    for i in range(DATE_PICKER_DAYS):
        d = today + timedelta(days=i)
        label = f"{d.strftime('%d.%m')} ({_WEEKDAYS_RU[d.weekday()]})"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label, callback_data=DateCb(date_iso=d.isoformat()).pack()
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def slots_kb(slots_utc: list[datetime], tz_name: str) -> InlineKeyboardMarkup:
    """Кнопки свободных слотов. slots_utc — наивные datetime в UTC."""
    rows = []
    for start_utc in slots_utc:
        local = to_local(start_utc, tz_name)
        rows.append(
            [
                InlineKeyboardButton(
                    text=local.strftime("%H:%M"),
                    callback_data=SlotCb(start_ts=int(start_utc.timestamp())).pack(),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb() -> InlineKeyboardMarkup:
    """Кнопки подтверждения/отмены записи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_CONFIRM_YES, callback_data=ConfirmCb(action="yes").pack()
                ),
                InlineKeyboardButton(
                    text=BTN_CONFIRM_NO, callback_data=ConfirmCb(action="no").pack()
                ),
            ]
        ]
    )


def my_bookings_kb(bookings: list[Booking], tz_name: str) -> InlineKeyboardMarkup:
    """Кнопка отмены под каждой активной записью."""
    rows = []
    for b in bookings:
        local = to_local(b.start_at, tz_name)
        when = local.strftime("%d.%m %H:%M")
        rows.append(
            [
                InlineKeyboardButton(
                    text=BTN_CANCEL_BOOKING.format(when=when),
                    callback_data=CancelBookingCb(booking_id=b.id).pack(),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
