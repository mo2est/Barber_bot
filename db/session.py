"""
Подключение к базе данных через SQLAlchemy в async-режиме.

Использование:
    from db.session import async_session_factory
    async with async_session_factory() as session:
        ...
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Грузим .env при импорте модуля
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

# echo=False — иначе в консоль будут литься все SQL-запросы.
# Поставь True временно для отладки.
engine = create_async_engine(DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # объекты остаются доступны после commit
)
