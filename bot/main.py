"""
Точка входа Telegram-бота.

Запуск (polling, дефолт для дев/демо):
    python -m bot.main

Запуск веб-хуком (прод, USE_WEBHOOK=true в .env):
    python -m bot.main
    (тот же вызов — режим переключается конфигом, не аргументом CLI)

База должна быть уже накачена миграциями: `python -m alembic upgrade head`,
тестовые данные — `python -m db.seed`.
"""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import settings
from bot.handlers import get_root_router
from bot.health import build_health_app, register_health_routes
from bot.logging_config import JsonFormatter
from bot.metrics import register_metrics_routes
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.services.reminders import resync_reminders


def setup_logging() -> None:
    """Логирование в консоль и, опционально, в файл с ротацией (LOG_FILE в .env).

    LOG_JSON=true переключает формат на одну JSON-строку на запись —
    удобно, если логи потом парсит ELK/Loki/CloudWatch и т.п.
    """
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        # Консоль Windows по умолчанию в cp1251 — кириллица в логах иначе не печатается.
        sys.stdout.reconfigure(encoding="utf-8")

    if settings.log_json:
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if settings.log_file:
        handlers.append(
            logging.handlers.RotatingFileHandler(
                settings.log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
        )
    for h in handlers:
        h.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=handlers)


def setup_sentry() -> None:
    """Sentry активируется только если задан SENTRY_DSN — иначе no-op."""
    if not settings.sentry_dsn:
        return
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.0)


def build_scheduler() -> AsyncIOScheduler:
    """APScheduler с персистентным jobstore — напоминания переживают перезапуск процесса.

    Файл лежит в ./data/ независимо от драйвера основной БД (sqlite/postgres) —
    шедулеру не нужен sync postgres-драйвер только из-за этого.
    """
    import os

    os.makedirs("data", exist_ok=True)
    return AsyncIOScheduler(
        timezone=settings.timezone,
        jobstores={"default": SQLAlchemyJobStore(url="sqlite:///./data/jobs.sqlite3")},
    )


async def _run_polling(bot: Bot, dp: Dispatcher, scheduler: AsyncIOScheduler) -> None:
    from aiohttp import web

    health_app = build_health_app(scheduler)
    register_metrics_routes(health_app)
    runner = web.AppRunner(health_app)
    await runner.setup()
    site = web.TCPSite(runner, settings.web_server_host, settings.web_server_port)
    await site.start()

    try:
        await dp.start_polling(
            bot, allowed_updates=dp.resolve_used_update_types(), scheduler=scheduler
        )
    finally:
        await runner.cleanup()
        scheduler.shutdown(wait=False)
        await bot.session.close()


async def _run_webhook(bot: Bot, dp: Dispatcher, scheduler: AsyncIOScheduler) -> None:
    from aiohttp import web

    if not settings.webhook_url:
        raise RuntimeError("USE_WEBHOOK=true, но WEBHOOK_URL не задан в .env")

    dp["scheduler"] = scheduler  # для webhook-режима workflow data передаётся так, не через start_polling
    await bot.set_webhook(
        url=f"{settings.webhook_url}{settings.webhook_path}",
        secret_token=settings.webhook_secret or None,
        allowed_updates=dp.resolve_used_update_types(),
    )

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp, bot=bot, secret_token=settings.webhook_secret or None
    ).register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)
    register_health_routes(app, scheduler)
    register_metrics_routes(app)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.web_server_host, settings.web_server_port)
    await site.start()

    # asyncio.Event().wait() сам по себе НЕ перехватывает SIGTERM (это не
    # KeyboardInterrupt) — без явного signal-handler'а процесс убивался бы
    # мгновенно, finally не успевал бы снять вебхук с Telegram. Поймано и
    # исправлено на живом тесте: после `docker compose down` вебхук
    # оставался висеть зарегистрированным на стороне Telegram.
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGTERM, stop_event.set)
        loop.add_signal_handler(signal.SIGINT, stop_event.set)
    except NotImplementedError:
        pass  # Windows: add_signal_handler не поддерживается, остаётся обработка по KeyboardInterrupt

    try:
        await stop_event.wait()
    finally:
        await bot.delete_webhook()
        scheduler.shutdown(wait=False)
        await runner.cleanup()
        await bot.session.close()


async def on_error(event: ErrorEvent) -> None:
    """Глобальный обработчик необработанных исключений в хендлерах.

    Логирует ошибку (и отдаёт её в Sentry, если он подключён) и отвечает
    пользователю нейтральным сообщением — иначе клиент остаётся с вечными
    «часиками» на кнопке и не понимает, что что-то пошло не так.
    """
    logging.getLogger("bot.errors").exception(
        "Необработанная ошибка в хендлере: %s", event.exception, exc_info=event.exception
    )
    try:
        if event.update.callback_query is not None:
            await event.update.callback_query.answer(
                "Что-то пошло не так. Попробуйте ещё раз.", show_alert=True
            )
        elif event.update.message is not None:
            await event.update.message.answer("Что-то пошло не так. Попробуйте ещё раз.")
    except Exception:  # noqa: BLE001 — уведомление best-effort, падать из-за него нельзя
        pass


async def main() -> None:
    setup_logging()
    setup_sentry()
    log = logging.getLogger("bot")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.errors.register(on_error)
    dp.include_router(get_root_router())

    scheduler = build_scheduler()
    scheduler.start()

    me = await bot.get_me()
    log.info("Бот запущен: @%s (id=%s), режим=%s", me.username, me.id,
              "webhook" if settings.use_webhook else "polling")
    log.info("Админы: %s", settings.admin_ids or "не заданы")

    restored = await resync_reminders(scheduler, bot)
    if restored:
        log.info("Восстановлено напоминаний после старта: %s", restored)

    if settings.use_webhook:
        await _run_webhook(bot, dp, scheduler)
    else:
        await _run_polling(bot, dp, scheduler)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nБот остановлен.")
