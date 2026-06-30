"""/health эндпоинт для docker healthcheck и внешнего мониторинга.

Работает в обоих режимах (polling и webhook) — в polling поднимается
отдельным aiohttp-сервером на WEB_SERVER_PORT, в webhook добавляется
роутом в уже существующее aiohttp-приложение.
"""

from __future__ import annotations

from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler


def register_health_routes(app: web.Application, scheduler: AsyncIOScheduler) -> None:
    """Добавить GET /health в существующее aiohttp-приложение."""

    async def health(request: web.Request) -> web.Response:
        if scheduler.running:
            return web.json_response({"status": "ok"})
        return web.json_response({"status": "degraded", "reason": "scheduler not running"}, status=503)

    app.router.add_get("/health", health)


def build_health_app(scheduler: AsyncIOScheduler) -> web.Application:
    """Самостоятельное aiohttp-приложение только с /health — для polling-режима."""
    app = web.Application()
    register_health_routes(app, scheduler)
    return app
