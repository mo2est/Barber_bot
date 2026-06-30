"""
Создаёт схему БД и заливает тестовые данные:
- 1 салон ("Барбершоп на Тверской")
- 2 мастера: Иван (старший, дороже) и Пётр
- 3 услуги: стрижка, борода, комплекс
- Связки мастер↔услуга с переопределённой ценой у Ивана
- Рабочие часы: оба работают Пн-Сб

Запуск (схема БД должна быть уже накачена через Alembic):
    python -m alembic upgrade head
    python -m db.seed

⚠️ Только заливает данные, ничего не дропая. Если нужно начать с нуля —
    удали файл bot.db, снова прогони `alembic upgrade head` и этот скрипт.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    # Консоль Windows по умолчанию в cp1251 — эмодзи и кириллица иначе не печатаются.
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from db.models import (
    Master,
    MasterService,
    Salon,
    Service,
    Weekday,
    WorkingHours,
)
from db.session import async_session_factory


async def seed_data() -> None:
    """Залить тестовые данные, если их ещё нет."""
    async with async_session_factory() as session:
        # Проверяем, есть ли уже салон — если да, ничего не делаем
        existing = await session.scalar(select(Salon).limit(1))
        if existing:
            print("База уже содержит данные — пропускаю seed.")
            return

        # ── Салон ────────────────────────────────────────────
        salon = Salon(
            name="Барбершоп на Тверской",
            address="Тверская 15, Москва",
            timezone="Europe/Moscow",
        )
        session.add(salon)
        await session.flush()  # чтобы получить salon.id

        # ── Услуги ───────────────────────────────────────────
        haircut = Service(
            salon_id=salon.id,
            name="Стрижка",
            description="Мужская стрижка машинкой и ножницами",
            duration_minutes=45,
            base_price_kopecks=150000,  # 1500 ₽
        )
        beard = Service(
            salon_id=salon.id,
            name="Оформление бороды",
            description="Стрижка и моделирование бороды",
            duration_minutes=30,
            base_price_kopecks=100000,  # 1000 ₽
        )
        combo = Service(
            salon_id=salon.id,
            name="Комплекс: стрижка + борода",
            description="Полный уход",
            duration_minutes=75,
            base_price_kopecks=220000,  # 2200 ₽
        )
        session.add_all([haircut, beard, combo])
        await session.flush()

        # ── Мастера ──────────────────────────────────────────
        ivan = Master(
            salon_id=salon.id,
            name="Иван",
            description="Старший барбер, опыт 8 лет",
            is_active=True,
        )
        petr = Master(
            salon_id=salon.id,
            name="Пётр",
            description="Барбер, опыт 3 года",
            is_active=True,
        )
        session.add_all([ivan, petr])
        await session.flush()

        # ── Связки мастер↔услуга ─────────────────────────────
        # Иван — все услуги, но дороже на стрижке (старший)
        session.add_all([
            MasterService(master_id=ivan.id, service_id=haircut.id,
                          price_override_kopecks=200000),  # 2000 ₽ вместо 1500
            MasterService(master_id=ivan.id, service_id=beard.id),
            MasterService(master_id=ivan.id, service_id=combo.id,
                          price_override_kopecks=270000),  # 2700 ₽ вместо 2200
        ])
        # Пётр — все услуги по базовой цене
        session.add_all([
            MasterService(master_id=petr.id, service_id=haircut.id),
            MasterService(master_id=petr.id, service_id=beard.id),
            MasterService(master_id=petr.id, service_id=combo.id),
        ])

        # ── Рабочие часы: оба работают Пн-Сб 10:00-20:00 ─────
        weekdays_workdays = [Weekday.MON, Weekday.TUE, Weekday.WED,
                             Weekday.THU, Weekday.FRI, Weekday.SAT]
        for master in (ivan, petr):
            for wd in weekdays_workdays:
                session.add(WorkingHours(
                    master_id=master.id,
                    weekday=wd,
                    start_time=time(10, 0),
                    end_time=time(20, 0),
                ))

        await session.commit()
        print("✓ Тестовые данные созданы:")
        print(f"  - Салон: {salon.name}")
        print("  - Мастера: Иван, Пётр")
        print("  - Услуги: Стрижка, Борода, Комплекс")
        print("  - Расписание: Пн-Сб 10:00-20:00")


async def main() -> None:
    print("→ Заливаю тестовые данные...")
    await seed_data()


if __name__ == "__main__":
    asyncio.run(main())
