"""Страховочный хендлер для устаревших инлайн-кнопок.

Подключается последним: сюда попадают только колбэки, которые не подошли
ни одному хендлеру выше (например, кнопка шага записи после того, как
сценарий завершён или состояние сброшено). Без него пользователь получал
бы вечные «часики» на кнопке.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from bot import texts

router = Router(name="fallback")


@router.callback_query()
async def stale_callback(callback: CallbackQuery) -> None:
    """Ответить на клик по устаревшей кнопке и снять клавиатуру с сообщения."""
    await callback.answer(texts.STALE_BUTTON, show_alert=True)
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass  # сообщение удалено/устарело — клавиатуры и так уже нет
