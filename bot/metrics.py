"""Метрики Prometheus: сколько записей создаётся/отменяется/напоминаний шлётся.

Счётчики растут в течение жизни процесса — это нормально для Prometheus
(он сам считает rate() по разнице между опросами), не нужно сбрасывать.
"""

from __future__ import annotations

from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

bookings_created_total = Counter(
    "bookings_created_total", "Успешно созданные брони"
)
bookings_cancelled_total = Counter(
    "bookings_cancelled_total", "Отменённые клиентом брони"
)
bookings_rejected_total = Counter(
    "bookings_rejected_total", "Отклонённые попытки записи", ["reason"]
)
reminders_sent_total = Counter(
    "reminders_sent_total", "Успешно отправленные напоминания"
)
reminders_failed_total = Counter(
    "reminders_failed_total", "Напоминания, которые не удалось отправить (ошибка Telegram API)"
)


def register_metrics_routes(app: web.Application) -> None:
    """Добавить GET /metrics в aiohttp-приложение (формат — Prometheus exposition)."""

    async def metrics(request: web.Request) -> web.Response:
        # aiohttp не принимает content_type со встроенным "; charset=..." —
        # CONTENT_TYPE_LATEST его содержит, поэтому отдаём через заголовок напрямую.
        return web.Response(body=generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})

    app.router.add_get("/metrics", metrics)
