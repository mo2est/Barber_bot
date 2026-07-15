"""Защита от спама кликами/командами: не более 1 события на пользователя за THROTTLE_WINDOW.

Простой in-memory throttle — для масштаба одного барбершопа (один процесс,
не распределённая система) этого достаточно; для нескольких инстансов
бота понадобился бы общий стейт (Redis), но это сильно за пределами
текущего скоупа.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

THROTTLE_WINDOW_SECONDS = 0.7
# Записи старше этого возраста уже не влияют на троттлинг — их можно выкидывать,
# иначе словарь _last_seen растёт бесконечно (по записи на каждого пользователя за всю жизнь процесса).
CLEANUP_INTERVAL_SECONDS = 300.0


class ThrottlingMiddleware(BaseMiddleware):
    """Если пользователь шлёт события чаще, чем раз в THROTTLE_WINDOW_SECONDS — событие дропается."""

    def __init__(self) -> None:
        self._last_seen: dict[int, float] = {}
        self._last_cleanup = time.monotonic()

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < CLEANUP_INTERVAL_SECONDS:
            return
        self._last_cleanup = now
        threshold = now - THROTTLE_WINDOW_SECONDS
        self._last_seen = {
            uid: ts for uid, ts in self._last_seen.items() if ts > threshold
        }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        now = time.monotonic()
        self._cleanup(now)
        last = self._last_seen.get(user.id)
        self._last_seen[user.id] = now

        if last is not None and (now - last) < THROTTLE_WINDOW_SECONDS:
            if isinstance(event, CallbackQuery):
                await event.answer()  # гасим "часики" на кнопке, без сообщения
            return None  # тихо игнорируем, не вызывая хендлер

        return await handler(event, data)
