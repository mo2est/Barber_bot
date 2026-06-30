# Бот записи к барберу

Telegram-бот для онлайн-записи в барбершоп. Полный цикл: запись клиента,
напоминания, админ-панель внутри бота, миграции БД, тесты, докер-инфра
для прода с бэкапами, метриками и health-check.

## Возможности

**Для клиента (в Telegram):**
- Запись на услугу: выбор услуги → мастера → даты → свободного слота → подтверждение
- Просмотр своих активных записей, отмена записи
- Напоминание за 1 час до визита (APScheduler, переживает перезапуск бота)
- Лимит — не больше 3 активных записей одновременно у одного клиента

**Для администратора (`/admin`, доступ по ADMIN_IDS):**
- Список активных записей на сегодня
- Включение/выключение мастеров и услуг
- Блокировка времени мастера (отпуск, обед и т.п.) текстовой командой
- Просмотр и удаление уже созданных блокировок

Нетехническая инструкция для администратора салона — [ADMIN_GUIDE.md](ADMIN_GUIDE.md).

## Надёжность и эксплуатация

- Защита от двойного бронирования слота — логическая проверка + частичный
  уникальный индекс в БД (`uq_active_master_slot`) на случай гонки двух
  почти одновременных подтверждений. Проверено тестом конкурентных запросов.
- Throttling-middleware — защита от спама кликами/командами (не чаще раза в 0.7с на пользователя).
- Ошибки Telegram API при отправке напоминания (блокировка бота и т.п.)
  логируются и не валят шедулер.
- Напоминания в персистентном jobstore (`./data/jobs.sqlite3`),
  восстанавливаются при старте бота — переживают перезапуск процесса.
- `GET /health` — для docker healthcheck и внешнего мониторинга.
- `GET /metrics` — метрики Prometheus: созданные/отменённые брони,
  отклонённые попытки записи по причине, отправленные/упавшие напоминания.
- Логи — текстом или JSON (`LOG_JSON=true`), с ротацией файла (`LOG_FILE`),
  опционально Sentry (`SENTRY_DSN`).
- Автоматические бэкапы Postgres (сервис `backup` в docker-compose) с
  ретеншеном — см. раздел «Бэкапы» ниже.
- Бизнес-логика (слоты, брони, блокировки времени) вынесена в
  `bot/services/*`, покрыта тестами без поднятия aiogram.

## Принятые допущения

- **Админка — это команды в самом боте, не отдельная Django-админка.**
  Решение принято для скорости — бот — единственный интерфейс
  администратора в этом масштабе проекта.
- **Шаг сетки слотов — 15 минут**, лид-тайм записи — 1 час, лимит активных
  записей на клиента — 3. Константы в `bot/services/slots.py` и `bot/services/booking.py`.
- **Throttling — простой in-memory**, без Redis. Подходит для одного
  процесса бота; для горизontального масштабирования на несколько
  инстансов понадобится общий стейт.
- **⚠️ Безопасность:** в `.env.example` ранее был закоммичен настоящий
  токен бота — заменён на плейсхолдер, но токен всё ещё есть в истории
  git. Если репозиторий когда-либо уходил в публичный/общий remote —
  обязательно отозвать токен через @BotFather (`/revoke`) и выписать
  новый, прежде чем использовать бота где-либо публично.

## Стек

- **Бот:** aiogram 3.x (async), FSM-сценарии
- **ORM:** SQLAlchemy 2.x (async) + Alembic-миграции
- **БД:** SQLite (дев/демо) или Postgres (прод, через asyncpg) — переключается `DATABASE_URL`
- **Планировщик:** APScheduler с персистентным jobstore
- **Тесты:** pytest + pytest-asyncio, изолированная in-memory БД на тест, CI на GitHub Actions
- **Мониторинг:** Prometheus-метрики, health-check, опционально Sentry, JSON-логи

## Запуск (дев, SQLite, polling)

```bash
git clone <repo-url> barber_bot
cd barber_bot

python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env
# отредактировать .env: вписать BOT_TOKEN и ADMIN_IDS

python -m alembic upgrade head
python -m db.seed

python -m bot.main
```

## Тесты

```bash
pytest
```

Гоняются и в CI (`.github/workflows/tests.yml`) на каждый push/PR: pytest
+ компиляция всех модулей + сборка Docker-образа.

## Прод-запуск через Docker (Postgres + webhook)

```bash
cp .env.example .env
# заполнить BOT_TOKEN, ADMIN_IDS, WEBHOOK_URL (публичный https-домен),
# WEBHOOK_SECRET (случайная строка), USE_WEBHOOK=true

docker compose up -d --build
```

Поднимает три сервиса: `db` (Postgres), `bot`, `backup` (автоматический
pg_dump). Миграции применяются автоматически при старте бота
(`docker-entrypoint.sh`). Тестовые данные — вручную при необходимости:

```bash
docker compose exec bot python -m db.seed
```

Если `USE_WEBHOOK=false` (по умолчанию) — бот работает через polling даже
в контейнере, без публичного домена; `WEBHOOK_URL`/`WEBHOOK_SECRET` можно
не заполнять. `/health` и `/metrics` доступны в обоих режимах на
`WEB_SERVER_PORT` (по умолчанию 8080).

## Бэкапы и восстановление

Сервис `backup` в `docker-compose.yml` раз в `BACKUP_INTERVAL_SECONDS`
(по умолчанию сутки) делает `pg_dump` в volume `backups`, сжимает gzip'ом
и удаляет файлы старше `BACKUP_RETENTION_DAYS` (по умолчанию 7 дней).

Восстановление из бэкапа на новый/пустой Postgres:

```bash
# Список файлов внутри volume
docker compose exec backup ls -la /backups

# Распаковать и применить дамп
docker compose exec backup sh -c "gunzip -c /backups/barber_bot_ИМЯ.sql.gz" > restore.sql
docker compose exec -T db psql -U barber -d barber_bot < restore.sql
```

Процедура проверена вручную: бэкап реальной БД с тестовыми данными
успешно восстановлен в чистый контейнер Postgres, все таблицы и записи
(включая кириллицу) на месте.

## Структура

```
bot/         — Telegram-бот: handlers, keyboards, FSM, бизнес-логика (services/), health, metrics
db/          — SQLAlchemy модели, сессии, сидирование тестовых данных
alembic/     — миграции схемы БД
backup/      — скрипт автоматического pg_dump (сервис backup в docker-compose)
tests/       — pytest-тесты bot/services/*
.github/     — CI workflow
```

## Лицензия

Учебный проект, MIT.
