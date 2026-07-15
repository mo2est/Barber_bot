"""Смоук-тесты уровня хендлеров: модули импортируются, роутеры собираются.

Ловит целый класс ошибок, невидимых для юнит-тестов сервисного слоя:
битые импорты, опечатки в декораторах, затенение имён (регрессия ниже).
"""

from __future__ import annotations

import os

# bot.config требует BOT_TOKEN при импорте — в CI нет .env, задаём заглушку.
os.environ.setdefault("BOT_TOKEN", "0000000000:TEST_TOKEN_FOR_IMPORT_ONLY")
os.environ.setdefault("ADMIN_IDS", "1")


def test_root_router_builds():
    """Все хендлеры импортируются и собираются в корневой роутер."""
    from bot.handlers import get_root_router

    root = get_root_router()
    names = {r.name for r in root.sub_routers}
    assert names == {"admin", "booking", "my_bookings", "start"}


def test_cancel_handler_does_not_shadow_service():
    """Регрессия: хендлер отмены раньше назывался cancel_booking и затенял
    одноимённую сервисную функцию — кнопка отмены падала с TypeError,
    рекурсивно вызывая сам хендлер вместо сервиса."""
    from bot.handlers import my_bookings
    from bot.services.booking import cancel_booking

    assert my_bookings.cancel_booking_service is cancel_booking
    assert my_bookings.cancel_booking_handler is not cancel_booking
