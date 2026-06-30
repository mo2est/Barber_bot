"""Обработчик команды /start и кнопок главного меню."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select

from bot import texts
from bot.keyboards.client import main_menu_kb
from db.models import Client
from db.session import async_session_factory

router = Router(name="start")


async def _get_or_create_client(message: Message) -> tuple[Client, bool]:
    """Найти клиента в БД по telegram_id или создать нового.

    Возвращает кортеж (client, is_new).
    """
    user = message.from_user
    assert user is not None  # в Message от пользователя всегда есть from_user

    async with async_session_factory() as session:
        client = await session.scalar(
            select(Client).where(Client.telegram_id == user.id)
        )
        is_new = client is None

        if is_new:
            client = Client(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
            )
            session.add(client)
            await session.commit()
            await session.refresh(client)
        else:
            # Обновим username/first_name, если поменялись в Telegram
            changed = False
            if client.username != user.username:
                client.username = user.username
                changed = True
            if client.first_name != user.first_name:
                client.first_name = user.first_name
                changed = True
            if changed:
                await session.commit()

        return client, is_new


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Приветствие при /start. Создаёт клиента в БД, если его ещё нет."""
    client, is_new = await _get_or_create_client(message)
    name = client.first_name or "друг"

    template = texts.WELCOME if is_new else texts.WELCOME_BACK
    await message.answer(
        template.format(name=name),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


# ── Кнопки главного меню (заглушки на этом этапе) ────────────────────────────


@router.message(F.text == texts.BTN_INFO)
async def show_info(message: Message) -> None:
    """О салоне."""
    await message.answer(texts.INFO, parse_mode="HTML")
