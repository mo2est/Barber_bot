"""Сборка всех роутеров проекта."""

from __future__ import annotations

from aiogram import Router

from bot.handlers.admin import router as admin_router
from bot.handlers.booking import router as booking_router
from bot.handlers.my_bookings import router as my_bookings_router
from bot.handlers.start import router as start_router


def get_root_router() -> Router:
    """Собрать главный роутер со всеми подроутерами."""
    root = Router(name="root")
    root.include_router(admin_router)
    root.include_router(booking_router)
    root.include_router(my_bookings_router)
    root.include_router(start_router)
    return root
