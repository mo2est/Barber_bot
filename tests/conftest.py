"""Общие фикстуры тестов: изолированная in-memory БД на каждый тест."""

from __future__ import annotations

from datetime import time

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db.models import Base, Client, Master, Salon, Service, Weekday, WorkingHours


@pytest_asyncio.fixture
async def session():
    """Чистая in-memory SQLite БД со схемой на каждый тест — без побочных эффектов между тестами."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def salon(session):
    s = Salon(name="Test Salon", timezone="Europe/Moscow")
    session.add(s)
    await session.flush()
    return s


@pytest_asyncio.fixture
async def master(session, salon):
    """Мастер, работающий Пн-Сб 10:00-20:00."""
    m = Master(salon_id=salon.id, name="Тестовый мастер", is_active=True)
    session.add(m)
    await session.flush()

    for wd in (Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI, Weekday.SAT):
        session.add(
            WorkingHours(master_id=m.id, weekday=wd, start_time=time(10, 0), end_time=time(20, 0))
        )
    await session.commit()
    return m


@pytest_asyncio.fixture
async def service(session, salon):
    s = Service(
        salon_id=salon.id, name="Стрижка", duration_minutes=45, base_price_kopecks=150000
    )
    session.add(s)
    await session.commit()
    return s


@pytest_asyncio.fixture
async def client(session):
    c = Client(telegram_id=1, username="tester", first_name="Test")
    session.add(c)
    await session.commit()
    return c
