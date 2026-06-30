"""
Настройки приложения.

Грузятся из .env через pydantic-settings. Все обязательные поля,
не указанные в .env, вызовут падение при импорте — это специально,
чтобы не упасть в рантайме на пустом токене.
"""

from __future__ import annotations

from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфиг приложения. Читается из .env при первом обращении."""

    bot_token: str = Field(..., description="Токен от BotFather")

    # pydantic-settings 2.x пытается парсить list-поля как JSON ДО валидаторов
    # и тихо падает на простой строке "1,2,3". Поэтому читаем как строку,
    # а наружу отдаём список через property admin_ids.
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")

    database_url: str = "sqlite+aiosqlite:///./bot.db"
    timezone: str = "Europe/Moscow"

    # ── Webhook (прод) vs polling (дев, по умолчанию) ───────────────────
    use_webhook: bool = False
    webhook_url: str = ""          # публичный https-адрес, напр. https://example.com
    webhook_path: str = "/webhook"
    webhook_secret: str = ""       # секрет для проверки заголовка X-Telegram-Bot-Api-Secret-Token
    web_server_host: str = "0.0.0.0"
    # В webhook-режиме здесь и сам вебхук, и /health. В polling — только /health.
    web_server_port: int = 8080

    # ── Наблюдаемость ────────────────────────────────────────────────────
    log_file: str = ""             # путь к файлу лога; пусто — лог только в консоль
    log_json: bool = False         # true — структурированные JSON-логи (для ELK/Loki и т.п.)
    sentry_dsn: str = ""           # пусто — Sentry не инициализируется

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @cached_property
    def admin_ids(self) -> list[int]:
        """ADMIN_IDS из .env — строка через запятую, например '123,456'."""
        raw = self.admin_ids_raw.strip()
        if not raw:
            return []
        return [int(x.strip()) for x in raw.split(",") if x.strip()]


# Единый инстанс на всё приложение
settings = Settings()
