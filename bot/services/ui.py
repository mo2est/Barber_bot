"""Утилиты для поддержания чистоты интерфейса в чате."""

from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest


async def remove_inline_kb(bot: Bot, chat_id: int, message_id: int | None) -> None:
    """Снять инлайн-клавиатуру с сообщения, если она ещё есть.

    Ошибки Telegram глотаем: сообщение могло быть удалено пользователем,
    устареть (>48ч) или клавиатура уже снята — во всех случаях цель
    («в чате нет активной кнопки») уже достигнута.
    """
    if not message_id:
        return
    try:
        await bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=message_id, reply_markup=None
        )
    except TelegramBadRequest:
        pass
