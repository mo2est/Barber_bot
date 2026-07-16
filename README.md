# Barber Bot — Telegram-бот для записи в барбершоп

> Полноценная система онлайн-записи к мастеру прямо в Telegram: выбор услуги → мастера → даты → времени → подтверждение с напоминанием за 1 час.

**Стек:** Python 3.12 · aiogram 3 · SQLAlchemy 2 (async) · SQLite / PostgreSQL · APScheduler · Docker  
**Версия:** 1.0 · Клиент: Барбершоп «На Тверской»

---

## Содержание

1. [Возможности](#возможности)
2. [Запуск на Windows — пошагово с нуля](#запуск-на-windows--пошагово-с-нуля)
3. [Быстрый старт (macOS / Linux)](#быстрый-старт-macos--linux)
4. [Развёртывание на сервере (production)](#развёртывание-на-сервере-production)
5. [Конфигурация](#конфигурация)
6. [Структура проекта](#структура-проекта)
7. [Схема базы данных](#схема-базы-данных)
8. [Сценарии использования](#сценарии-использования)
9. [Настройка контента](#настройка-контента)
10. [Обновление и обслуживание](#обновление-и-обслуживание)
11. [Частые проблемы](#частые-проблемы)
12. [Лицензия](#лицензия)

---

## Возможности

### Для пользователей
- [x] Онлайн-запись: услуга → мастер → дата → свободный слот → подтверждение
- [x] Просмотр своих активных записей
- [x] Отмена записи в один клик
- [x] Напоминание в Telegram за 1 час до визита
- [x] Защита от случайного двойного нажатия (дубли исключены на уровне БД)
- [x] Лимит активных записей — не более 3 одновременно (защита от злоупотреблений)
- [x] Антиспам-троттлинг: не чаще 1 действия в 0.7 сек на пользователя, лишние клики тихо гасятся
- [x] Устаревшие кнопки не «зависают»: клик по кнопке завершённого сценария показывает подсказку и убирает клавиатуру
- [x] Напоминания переживают перезапуск бота (персистентное хранилище задач + восстановление при старте)
- [x] Глобальный обработчик ошибок: при любом сбое пользователь получает понятное сообщение, а не «зависшую» кнопку

### Для администраторов
- [x] Команда `/admin` — панель управления прямо в боте
- [x] Список всех записей на сегодня (время · услуга · мастер · клиент)
- [x] Включение / отключение мастеров (soft delete, история не ломается)
- [x] Включение / отключение услуг
- [x] Блокировка времени мастера (отпуск, обед, выходной) с FSM-диалогом
- [x] Просмотр и удаление активных блокировок
- [x] Доступ только для Telegram ID из списка `ADMIN_IDS`

---

## Запуск на Windows — пошагово с нуля

> Этот раздел написан для тех, кто никогда не запускал Python-проекты.  
> Выполняйте шаги по порядку — на каждом написано, что должно произойти.

### Шаг 1 — Создать бота в @BotFather

1. Откройте Telegram, найдите `@BotFather` и напишите `/start`.
2. Отправьте команду `/newbot`.
3. Придумайте имя бота (например, `Барбершоп На Тверской`) и логин (например, `mytver_barber_bot` — должен заканчиваться на `bot`).
4. BotFather пришлёт **токен** — длинная строка вида `7123456789:AAG...`. **Скопируйте её и сохраните** — она понадобится на шаге 8.

### Шаг 2 — Узнать свой Telegram ID

1. Найдите в Telegram бота `@userinfobot` и напишите ему `/start`.
2. Он пришлёт ваш **числовой ID** (например, `123456789`). Сохраните его.

> Этот ID нужно будет вписать в переменную `ADMIN_IDS` — именно ваш аккаунт получит доступ к `/admin`.

### Шаг 3 — Установить Python 3.12

1. Зайдите на [python.org/downloads](https://www.python.org/downloads/) и скачайте **Python 3.12** (или новее).
2. Запустите установщик.
3. **Важно:** на первом экране отметьте галку **«Add Python to PATH»** (добавить Python в PATH). Без неё ничего не заработает.
4. Нажмите **Install Now** и дождитесь завершения.
5. Проверка: откройте **Пуск → Командная строка** (cmd) и введите:
   ```
   python --version
   ```
   Должно появиться `Python 3.12.x`.

### Шаг 4 — Скачать код

**Вариант А — ZIP (проще):**
1. На странице репозитория нажмите **Code → Download ZIP**.
2. Распакуйте архив в удобное место, например `C:\barber_bot`.

**Вариант Б — git clone (если установлен Git):**
```cmd
git clone https://github.com/mo2est/barber_bot.git C:\barber_bot
```

### Шаг 5 — Открыть папку в командной строке

Самый простой способ:
1. Откройте папку с проектом в Проводнике.
2. Кликните на **адресную строку** (сверху, где написан путь к папке) — она выделится.
3. Напечатайте `cmd` и нажмите **Enter**.
4. Откроется командная строка уже внутри нужной папки.

Проверка — введите `dir` и убедитесь, что в списке есть файлы `requirements.txt` и `docker-compose.yml`.

### Шаг 6 — Создать виртуальное окружение

В командной строке выполните по очереди:

```cmd
python -m venv venv
venv\Scripts\activate
```

После активации в начале строки появится `(venv)` — это нормально, значит окружение работает.

**Если появится ошибка про PowerShell «execution policy»:**
1. Откройте **PowerShell от имени администратора** (Пуск → PowerShell → правая кнопка → «Запуск от имени администратора»).
2. Выполните:
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
3. Нажмите `Y` и Enter.
4. Вернитесь в обычную командную строку и повторите `venv\Scripts\activate`.

### Шаг 7 — Установить зависимости

```cmd
pip install -r requirements.txt
```

Это займёт 1–3 минуты. Должны скачаться пакеты aiogram, SQLAlchemy и другие. В конце напишет `Successfully installed ...`.

### Шаг 8 — Создать файл конфигурации .env

1. Скопируйте файл-шаблон:
   ```cmd
   copy .env.example .env
   ```
2. Откройте `.env` в Блокноте (или Notepad++, VS Code) и заполните обязательные поля:

   ```env
   BOT_TOKEN=7123456789:AAG...        ← токен из шага 1
   ADMIN_IDS=123456789                ← ваш Telegram ID из шага 2
   DATABASE_URL=sqlite+aiosqlite:///./bot.db   ← оставьте как есть для старта
   TIMEZONE=Europe/Moscow             ← часовой пояс заведения
   ```

3. Сохраните файл.

### Шаг 9 — Подготовить базу данных и запустить бота

```cmd
python -m alembic upgrade head
python -m db.seed
python -m bot.main
```

- Первая команда создаёт все таблицы в БД.
- Вторая команда заполняет тестовыми данными (мастера, услуги).
- Третья команда запускает бота.

Если всё хорошо, в консоли появится:
```
INFO | bot | Бот запущен: @mytver_barber_bot (id=...), режим=polling
INFO | bot | Админы: [123456789]
```

Откройте Telegram, найдите своего бота и напишите `/start`.

### Шаг 10 — Постоянная работа бота

Пока командная строка открыта — бот работает. Закрыли окно — бот остановился.

**Вариант А — .bat файл + автозагрузка Windows (простой):**

Создайте файл `start_bot.bat` в папке проекта:
```bat
@echo off
cd /d C:\barber_bot
call venv\Scripts\activate
python -m bot.main
```

Чтобы бот запускался при включении компьютера:
1. Нажмите `Win+R`, введите `shell:startup`, нажмите Enter.
2. Скопируйте ярлык `start_bot.bat` в открывшуюся папку автозагрузки.

**Вариант Б — VPS-сервер (надёжный, рекомендуется):**  
Смотрите раздел [Развёртывание на сервере](#развёртывание-на-сервере-production).

### Таблица ошибок Windows

| Симптом | Причина | Решение |
|---------|---------|---------|
| `'python' is not recognized as an internal or external command` | Python не добавлен в PATH | Переустановите Python, отметив «Add to PATH» |
| `ModuleNotFoundError: No module named 'aiogram'` | Виртуальное окружение не активировано | Выполните `venv\Scripts\activate` |
| `validation error for Settings` / `bot_token Field required` | Файл `.env` не создан или не заполнен | Выполните шаг 8 |
| `sqlite3.OperationalError: no such table` | Миграции не применены | Выполните `python -m alembic upgrade head` |
| `TelegramUnauthorizedError` | Неверный токен в `BOT_TOKEN` | Проверьте токен у @BotFather командой `/mybots` |

---

## Быстрый старт (macOS / Linux)

```bash
git clone https://github.com/mo2est/barber_bot.git && cd barber_bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # заполнить BOT_TOKEN и ADMIN_IDS
python -m alembic upgrade head
python -m db.seed
python -m bot.main
```

---

## Развёртывание на сервере (production)

### Требования к серверу

| Параметр | Минимум | Рекомендуется |
|----------|---------|---------------|
| ОС | Ubuntu 22.04 | Ubuntu 24.04 LTS |
| CPU | 1 vCPU | 2 vCPU |
| RAM | 512 МБ | 1 ГБ |
| Диск | 5 ГБ | 20 ГБ |
| Python | 3.12 | 3.12 |
| Открытые порты | 8080 | 443 (HTTPS через nginx) |

### Вариант А — systemd (без Docker)

```bash
# 1. Установить зависимости ОС
sudo apt update && sudo apt install -y python3.12 python3.12-venv git

# 2. Создать системного пользователя
sudo useradd -m -s /bin/bash barber

# 3. Скачать код
sudo -u barber git clone https://github.com/mo2est/barber_bot.git /home/barber/app
cd /home/barber/app

# 4. Установить Python-зависимости
sudo -u barber python3.12 -m venv venv
sudo -u barber venv/bin/pip install -r requirements.txt

# 5. Создать .env
sudo -u barber cp .env.example .env
sudo -u barber nano .env   # заполнить BOT_TOKEN, ADMIN_IDS, DATABASE_URL

# 6. Применить миграции и заполнить данными
sudo -u barber venv/bin/python -m alembic upgrade head
sudo -u barber venv/bin/python -m db.seed

# 7. Создать systemd-сервис
sudo tee /etc/systemd/system/barber-bot.service > /dev/null <<EOF
[Unit]
Description=Barber Bot Telegram
After=network.target postgresql.service

[Service]
User=barber
WorkingDirectory=/home/barber/app
EnvironmentFile=/home/barber/app/.env
ExecStart=/home/barber/app/venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable barber-bot
sudo systemctl start barber-bot

# 8. Проверить логи
sudo journalctl -u barber-bot -f
```

### Вариант Б — Docker (рекомендуется для прода)

```bash
# Клонировать репозиторий
git clone https://github.com/mo2est/barber_bot.git && cd barber_bot

# Заполнить .env (минимум: BOT_TOKEN, ADMIN_IDS, POSTGRES_PASSWORD)
cp .env.example .env && nano .env

# Запустить все сервисы (bot + postgres + backup)
docker compose up -d

# Просмотр логов
docker compose logs -f bot

# Остановить
docker compose down
```

**Что поднимает docker-compose:**
- `db` — PostgreSQL 16
- `bot` — сам бот (с healthcheck на `/health`)
- `backup` — автоматический pg_dump по расписанию

---

## Конфигурация

Все настройки задаются в файле `.env` (скопировать из `.env.example`).

| Переменная | Описание | По умолчанию |
|------------|----------|-------------|
| `BOT_TOKEN` | Токен бота от @BotFather | — (обязательно) |
| `ADMIN_IDS` | Telegram ID администраторов через запятую | — (обязательно) |
| `DATABASE_URL` | URL базы данных | `sqlite+aiosqlite:///./bot.db` |
| `TIMEZONE` | Часовой пояс заведения | `Europe/Moscow` |
| `USE_WEBHOOK` | Включить webhook вместо polling | `false` |
| `WEBHOOK_URL` | Публичный HTTPS-адрес сервера | — |
| `WEBHOOK_PATH` | Путь для webhook | `/webhook` |
| `WEBHOOK_SECRET` | Секрет для проверки запросов Telegram | — |
| `WEB_SERVER_HOST` | Хост HTTP-сервера | `0.0.0.0` |
| `WEB_SERVER_PORT` | Порт HTTP-сервера (`/health`, `/metrics`) | `8080` |
| `LOG_FILE` | Путь к файлу лога (пусто = только консоль) | — |
| `LOG_JSON` | JSON-формат логов (для ELK/Loki) | `false` |
| `SENTRY_DSN` | DSN проекта в Sentry (пусто = отключено) | — |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL для docker-compose | `barber` |
| `BACKUP_INTERVAL_SECONDS` | Интервал pg_dump в секундах | `86400` |
| `BACKUP_RETENTION_DAYS` | Сколько дней хранить бэкапы | `7` |

---

## Структура проекта

```
barber_bot/
│
├── bot/                        # Всё, что касается Telegram-бота
│   ├── handlers/               # Обработчики сообщений и callback-ов
│   │   ├── admin.py            # Админ-панель (/admin, FSM блокировок)
│   │   ├── booking.py          # FSM записи (услуга→мастер→дата→слот→OK)
│   │   ├── fallback.py         # Устаревшие инлайн-кнопки (подсказка + снятие клавиатуры)
│   │   ├── my_bookings.py      # Просмотр и отмена записей
│   │   └── start.py            # /start, главное меню
│   ├── keyboards/
│   │   ├── admin.py            # Inline-клавиатуры для админ-панели
│   │   └── client.py           # Reply/inline клавиатуры для пользователей
│   ├── middlewares/
│   │   └── throttling.py       # Антифлуд (rate limiting)
│   ├── services/
│   │   ├── booking.py          # Создание/отмена брони в БД
│   │   ├── format.py           # Форматирование дат, цен для отображения
│   │   ├── reminders.py        # Планирование напоминаний через APScheduler
│   │   ├── slots.py            # Генерация свободных временных слотов
│   │   ├── timeoff.py          # Создание блокировок времени мастера
│   │   └── ui.py               # Снятие инлайн-клавиатур со старых сообщений
│   ├── callbacks.py            # CallbackData-классы (aiogram 3)
│   ├── config.py               # Настройки через pydantic-settings
│   ├── health.py               # HTTP /health endpoint
│   ├── logging_config.py       # JSON-логгер
│   ├── main.py                 # Точка входа: polling / webhook
│   ├── metrics.py              # Prometheus /metrics endpoint
│   ├── states.py               # FSM-состояния (BookingStates, AdminStates)
│   └── texts.py                # Все тексты сообщений бота
│
├── db/                         # Слой базы данных
│   ├── models.py               # SQLAlchemy-модели (ORM)
│   ├── seed.py                 # Начальное заполнение БД тестовыми данными
│   └── session.py              # Фабрика async-сессий
│
├── alembic/                    # Миграции схемы БД
│   └── versions/
│       └── fd4968b2bcd4_initial_schema.py
│
├── tests/                      # Автотесты (pytest + pytest-asyncio)
│   ├── test_booking_service.py
│   ├── test_handlers_import.py
│   ├── test_keyboards.py
│   ├── test_slots.py
│   ├── test_throttling.py
│   └── test_timeoff_service.py
│
├── backup/
│   └── backup.sh               # Скрипт pg_dump для docker-сервиса backup
│
├── data/                       # Создаётся автоматически при запуске
│   └── jobs.sqlite3            # Хранилище задач APScheduler (напоминания)
│
├── .env.example                # Шаблон переменных окружения
├── ADMIN_GUIDE.md              # Инструкция для администратора салона
├── alembic.ini
├── docker-compose.yml          # bot + postgres + backup
├── Dockerfile
├── docker-entrypoint.sh
├── pytest.ini
└── requirements.txt
```

---

## Схема базы данных

```
┌─────────────────────────────────────────────────────────────────┐
│  salons                                                         │
│  id · name · address · timezone                                 │
└──────────┬──────────────────────────┬──────────────────────────┘
           │ 1:N                      │ 1:N
           ▼                          ▼
┌──────────────────────┐   ┌──────────────────────────────────────┐
│  masters             │   │  services                            │
│  id · salon_id       │   │  id · salon_id · name                │
│  name · description  │   │  description · duration_minutes      │
│  is_active           │   │  base_price_kopecks · is_active      │
└──────┬───────────────┘   └───────────────────┬──────────────────┘
       │                                        │
       │         N:M (через master_services)    │
       └──────────────────┬─────────────────────┘
                          ▼
              ┌────────────────────────────────┐
              │  master_services               │
              │  id · master_id · service_id   │
              │  price_override_kopecks        │
              │  duration_override_minutes     │
              └────────────────────────────────┘

┌──────────────────────────────────┐
│  working_hours                   │  ← шаблон рабочих часов по дням
│  id · master_id · weekday        │    (mon/tue/.../sun)
│  start_time · end_time           │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  time_off                        │  ← исключения: отпуск, обед,
│  id · master_id                  │    выходной. Перекрывают working_hours
│  start_at · end_at (UTC)         │
│  reason                          │
└──────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  clients                                             │
│  id · telegram_id (BigInt, unique) · username        │
│  first_name · phone                                  │
└──────────────────────┬───────────────────────────────┘
                       │ 1:N
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  bookings                                                        │
│  id · client_id (FK) · master_id (FK) · service_id (FK)         │
│  start_at · end_at (UTC)                                         │
│  price_kopecks  ← фиксируется на момент брони                   │
│  status: active / completed / cancelled_client /                 │
│          cancelled_salon / no_show                               │
│  reminder_job_id  ← ID задачи APScheduler                       │
│                                                                  │
│  UNIQUE INDEX (master_id, start_at) WHERE status = 'active'      │
└──────────────────────────────────────────────────────────────────┘
```

> Цены хранятся в **копейках** (Integer), отображаются делением на 100.  
> Все временны́е метки — в **UTC**, конвертация в часовой пояс происходит при отображении.

---

## Сценарии использования

### Пользовательский путь

```
/start
  └── Главное меню (Reply-кнопки)
        ├── ✂️ Записаться
        │     ├── Выбор услуги (inline-кнопки)
        │     ├── Выбор мастера
        │     ├── Выбор даты (ближайшие 7 дней)
        │     ├── Выбор свободного слота (сетка 15 минут, запись минимум за 1 ч)
        │     ├── Подтверждение (детали + цена)
        │     └── ✅ Запись создана → напоминание за 1 ч запланировано
        │
        ├── 📋 Мои записи  (та же логика у кнопки «❌ Отменить запись»)
        │     └── Список активных броней
        │           └── ❌ Отменить: <дата> → отмена в один клик + отмена напоминания
        │
        └── ℹ️ О салоне
              └── Адрес, часы работы, мастера
```

### Административный путь (/admin)

```
/admin  (только для ADMIN_IDS)
  └── Админ-меню (inline-кнопки)
        ├── 🗓 Записи на сегодня
        │     └── Список: время · услуга · мастер · клиент
        │
        ├── 👤 Мастера
        │     └── Список мастеров, клик по имени = вкл/выкл (is_active toggle)
        │
        ├── ✂️ Услуги
        │     └── Список услуг, клик по названию = вкл/выкл
        │
        ├── 🚫 Заблокировать время  [FSM]
        │     ├── Выбор мастера
        │     └── Ввод периода текстом («2026-07-01 14:00 16:00 Обед»)
        │           └── при неверном формате бот попросит прислать заново
        │
        └── 📋 Список блокировок
              └── Будущие блокировки, клик по строке = удаление
```

---

## Настройка контента

### Через /admin (пошагово)

1. Напишите боту `/admin` — откроется панель управления.
2. **Мастера:** кнопка «Мастера» — включайте/отключайте нужных. Отключённый мастер не показывается при записи, но его история броней сохраняется.
3. **Услуги:** кнопка «Услуги» — аналогично.
4. **Блокировка времени:** кнопка «Заблокировать время» → выберите мастера → введите период в формате `ГГГГ-ММ-ДД ЧЧ:ММ ЧЧ:ММ Причина`, например:
   - `2026-07-01 13:00 14:00 Обед`
   - `2026-12-31 00:00 23:59 Новогодний выходной`
5. Для удаления блокировки: кнопка «Список блокировок» → нажмите на строку нужной блокировки — она удалится.

### Изменение текстов и данных о салоне

Все тексты и статичная информация (название, адрес, часы работы) находятся в файле `bot/texts.py`. Отредактируйте его и перезапустите бота.

### Сброс и повторное наполнение БД

Если нужно добавить или изменить мастеров и услуги:

```bash
# Редактируйте db/seed.py, затем:
python -m db.seed

# Или при использовании Docker:
docker compose run --rm bot python -m db.seed
```

> Скрипт seed безопасен для повторного запуска — существующие записи не дублируются.

---

## Обновление и обслуживание

### Обновление кода

```bash
# Остановить сервис
sudo systemctl stop barber-bot   # или: docker compose down

# Получить новую версию
git pull origin main

# Применить новые миграции (если есть)
venv/bin/python -m alembic upgrade head
# или для Docker:
docker compose run --rm bot python -m alembic upgrade head

# Запустить
sudo systemctl start barber-bot   # или: docker compose up -d
```

### Бэкап базы данных

**Вручную:**
```bash
# SQLite (dev)
cp bot.db bot.db.backup_$(date +%Y%m%d)

# PostgreSQL
pg_dump -U barber barber_bot > backup_$(date +%Y%m%d_%H%M).sql
```

**Автоматически через cron** (добавить в `crontab -e`):
```cron
0 3 * * * pg_dump -U barber barber_bot > /backups/barber_$(date +\%Y\%m\%d).sql
0 4 * * * find /backups -name "barber_*.sql" -mtime +7 -delete
```

**Через Docker:** сервис `backup` в `docker-compose.yml` делает это автоматически. Настройте интервал через `BACKUP_INTERVAL_SECONDS` и срок хранения через `BACKUP_RETENTION_DAYS` в `.env`.

### Быстрые команды systemd

| Команда | Действие |
|---------|----------|
| `sudo systemctl start barber-bot` | Запустить |
| `sudo systemctl stop barber-bot` | Остановить |
| `sudo systemctl restart barber-bot` | Перезапустить |
| `sudo systemctl status barber-bot` | Статус процесса |
| `sudo journalctl -u barber-bot -f` | Логи в реальном времени |
| `sudo journalctl -u barber-bot --since "1 hour ago"` | Логи за последний час |

---

## Частые проблемы

| Симптом | Причина | Решение |
|---------|---------|---------|
| Бот не отвечает на команды | Неверный `BOT_TOKEN` | Проверьте токен: `/mybots` у @BotFather |
| `/admin` отвечает «Команда доступна только администраторам» | Ваш Telegram ID не в `ADMIN_IDS` | Добавьте свой ID в `.env` и перезапустите бота |
| «Свободных слотов нет» на все дни | Не заполнены рабочие часы мастеров | Проверьте таблицу `working_hours`, запустите `python -m db.seed` |
| Напоминание не пришло | Задача APScheduler потерялась | Перезапустите бота — при старте напоминания восстанавливаются |
| `alembic: Can't locate revision` | Конфликт миграций | Удалите `bot.db` (dev) или выполните `alembic stamp head` |
| Бот падает сразу после запуска | `DATABASE_URL` не задан или БД недоступна | Проверьте `.env` и доступность PostgreSQL |
| `TelegramForbiddenError` в логах | Пользователь заблокировал бота | Это нормально — напоминание не отправляется, запись остаётся |

---

## Лицензия

Проект передаётся клиенту без ограничений на использование. Исходный код является коммерческой разработкой.

---

<details>
<summary>Чеклист перед сдачей клиенту</summary>

- [ ] **Токен** — `BOT_TOKEN` установлен и бот отвечает на `/start`
- [ ] **Администратор** — `ADMIN_IDS` заполнен, `/admin` открывается без ошибок
- [ ] **Контент** — мастера и услуги добавлены в БД, рабочие часы настроены
- [ ] **Тест записи** — пройден полный сценарий: услуга → мастер → дата → слот → подтверждение → запись видна в «Мои записи»
- [ ] **Напоминание** — создана тестовая запись на +1ч, убедиться что напоминание пришло
- [ ] **systemd / Docker** — сервис стартует после перезагрузки (`systemctl is-enabled barber-bot` → `enabled`)
- [ ] **Бэкап** — выполнен и проверен хотя бы один ручной бэкап БД
- [ ] **Инструкция** — клиент получил этот README и знает как перезапустить бота

</details>
