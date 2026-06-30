# 💈 Бот онлайн-записи в барбершоп

> Telegram-бот для записи клиентов: услуга → мастер → дата → свободное время.
> Напоминания за час до визита, админ-панель прямо в боте, без накладок по времени.

**Стек:** Python 3.12 · aiogram 3 · SQLAlchemy 2 (async) · PostgreSQL / SQLite · Docker
**Версия:** 1.0 · Разработано под заказ (барбершоп, 1 точка, 1 администратор)

---

## 📑 Содержание

1. [Возможности](#-возможности)
2. [Запуск на Windows — пошагово с нуля](#-запуск-на-windows--пошагово-с-нуля)
3. [Быстрый старт (macOS / Linux)](#-быстрый-старт-macos--linux)
4. [Развёртывание на сервере (production)](#-развёртывание-на-сервере-production)
5. [Конфигурация (.env)](#-конфигурация-env)
6. [Структура проекта](#-структура-проекта)
7. [Схема базы данных](#-схема-базы-данных)
8. [Сценарии использования](#-сценарии-использования)
9. [Настройка контента](#-настройка-контента)
10. [Обновление, обслуживание и частые проблемы](#-обновление-и-обслуживание)

---

## ✨ Возможности

### Для клиентов
- [x] Запись на услугу в несколько нажатий: услуга → мастер → дата → свободный слот → подтверждение
- [x] Автоматический расчёт свободного времени (учитывает длительность услуги, график мастера, перерывы и занятые слоты)
- [x] Просмотр своих активных записей
- [x] Отмена записи
- [x] Напоминание за 1 час до визита
- [x] Защита от спама и от создания слишком большого числа записей

### Для администраторов (команда `/admin`)
- [x] Список записей на сегодня
- [x] Включение / выключение мастеров
- [x] Включение / выключение услуг
- [x] Блокировка рабочего времени (отпуск, обед, больничный)
- [x] Просмотр и удаление блокировок

---

## 🪟 Запуск на Windows — пошагово с нуля

> Этот раздел рассчитан на человека **без опыта программирования**. Делайте по
> порядку, ничего не пропуская. Команды копируются целиком.

### Шаг 1. Создать бота в @BotFather
1. Откройте Telegram, в поиске найдите **@BotFather** (с синей галочкой).
2. Напишите ему `/newbot`.
3. Придумайте имя бота (например `Барбершоп Запись`).
4. Придумайте username — он должен заканчиваться на `bot` (например `my_barber_booking_bot`).
5. BotFather пришлёт **токен** — длинную строку вида `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
   **Скопируйте и сохраните его** — он понадобится в Шаге 8.

> ⚠️ Никому не показывайте токен. Кто его знает — управляет вашим ботом.

### Шаг 2. Узнать свой Telegram ID
1. В поиске найдите бота **@userinfobot**.
2. Напишите ему `/start`.
3. Он пришлёт ваш `Id` — число вроде `453425437`. Сохраните его (это нужно,
   чтобы только вы имели доступ к команде `/admin`).

### Шаг 3. Установить Python
1. Зайдите на https://www.python.org/downloads/ и скачайте Python 3.12.
2. Запустите установщик.
3. **❗ ОБЯЗАТЕЛЬНО** поставьте галочку **«Add python.exe to PATH»** внизу
   первого окна установщика — иначе команды ниже работать не будут.
4. Нажмите «Install Now», дождитесь конца.
5. Проверка: нажмите `Win + R`, введите `cmd`, Enter. В чёрном окне напишите:
   ```
   python --version
   ```
   Должно появиться `Python 3.12.x`. Если «не является внутренней командой» —
   переустановите Python с галочкой PATH.

### Шаг 4. Скачать код
**Вариант А (проще):** скачать ZIP с GitHub → кнопка **Code → Download ZIP** →
распаковать, например, в `C:\barber_bot`.

**Вариант Б (если установлен git):**
```
git clone <адрес-репозитория> C:\barber_bot
```

### Шаг 5. Открыть папку в командной строке
1. Откройте папку с кодом в Проводнике (там, где лежит `requirements.txt`).
2. Кликните в **адресную строку** Проводника (вверху, где путь к папке).
3. Сотрите путь, напишите `cmd` и нажмите Enter.
4. Откроется чёрное окно, уже «стоящее» в нужной папке.

### Шаг 6. Создать виртуальное окружение
В этом же окне выполните по очереди:
```
python -m venv .venv
.venv\Scripts\activate.bat
```
После активации слева в строке появится `(.venv)`.

> 💡 Если используете **PowerShell** (синее окно) и команда `activate` выдаёт
> ошибку про «выполнение сценариев отключено» — проще открыть обычный `cmd`
> (Шаг 5) и использовать `activate.bat`. Либо один раз выполните в PowerShell:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` и подтвердите.

### Шаг 7. Установить зависимости
```
pip install -r requirements.txt
```
Подождите 1–2 минуты — скачаются нужные библиотеки.

### Шаг 8. Создать файл .env из шаблона
```
copy .env.example .env
notepad .env
```
В открывшемся блокноте впишите:
- `BOT_TOKEN=` — токен из Шага 1
- `ADMIN_IDS=` — ваш ID из Шага 2

Остальное можно не трогать (по умолчанию используется простая база SQLite).
Сохраните файл (`Ctrl + S`) и закройте блокнот.

### Шаг 9. Первый запуск
Перед самым первым запуском создайте таблицы в базе и (по желанию) тестовые данные:
```
python -m alembic upgrade head
python -m db.seed
```
Теперь запустите бота:
```
python -m bot.main
```
Если в окне появилось `Бот запущен: @ваш_бот` — всё работает. Откройте бота в
Telegram, напишите `/start`. Для остановки — `Ctrl + C` в чёрном окне.

### Шаг 10. Постоянная работа
Пока чёрное окно открыто — бот работает. Если закрыть окно или выключить
компьютер — бот выключится. Варианты «чтобы работал всегда»:

**Простой (на своём ПК):** создайте файл `start_bot.bat` в папке проекта:
```bat
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m bot.main
pause
```
Запускайте бота двойным кликом по нему. Чтобы стартовал при включении ПК —
положите ярлык этого файла в папку автозагрузки (`Win + R` → `shell:startup`).

**Надёжный (рекомендуется для реального салона):** арендовать недорогой
сервер (VPS) и поставить бота туда — тогда он работает 24/7 независимо от
вашего компьютера. См. раздел [Развёртывание на сервере](#-развёртывание-на-сервере-production).

### Таблица типичных ошибок Windows

| Симптом | Причина | Решение |
|---|---|---|
| `python не является внутренней командой` | Не стоит галочка Add to PATH | Переустановить Python с галочкой (Шаг 3) |
| `activate ... выполнение сценариев отключено` | Политика PowerShell | Использовать `cmd` + `activate.bat` (Шаг 6) |
| `No module named ...` | Не активирован `.venv` или не ставили зависимости | Повторить Шаги 6–7 |
| `TokenValidationError` / бот не стартует | Неверный или пустой `BOT_TOKEN` | Проверить `.env` (Шаг 8) |
| `/admin` пишет «только для администраторов» | Неверный `ADMIN_IDS` | Вписать свой ID из @userinfobot |

---

## 🚀 Быстрый старт (macOS / Linux)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # вписать BOT_TOKEN и ADMIN_IDS
python -m alembic upgrade head
python -m db.seed             # тестовые данные (опционально)
python -m bot.main
```

---

## 🖥 Развёртывание на сервере (production)

### Требования к серверу

| Параметр | Минимум | Комментарий |
|---|---|---|
| ОС | Ubuntu 22.04+ | подойдёт любой Linux |
| RAM | 512 МБ | боту хватает с запасом |
| CPU | 1 vCPU | — |
| Диск | 5 ГБ | под систему, код и БД |
| Сеть | исходящий HTTPS | для режима polling домен НЕ нужен |

### Вариант А — напрямую (systemd)

```bash
# 1. Зависимости системы
sudo apt update && sudo apt install -y python3-venv python3-pip git

# 2. Отдельный пользователь под бота
sudo useradd -m -s /bin/bash barber && sudo su - barber

# 3. Код и окружение
git clone <адрес-репозитория> ~/barber_bot && cd ~/barber_bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4. Конфиг
cp .env.example .env && nano .env     # BOT_TOKEN, ADMIN_IDS (+ DATABASE_URL для Postgres)
python -m alembic upgrade head
python -m db.seed

# 5. systemd-сервис (выйти из пользователя barber: exit)
sudo nano /etc/systemd/system/barber-bot.service
```
Содержимое сервиса:
```ini
[Unit]
Description=Barber booking bot
After=network.target

[Service]
User=barber
WorkingDirectory=/home/barber/barber_bot
ExecStart=/home/barber/barber_bot/.venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
# 6. Запуск и логи
sudo systemctl daemon-reload
sudo systemctl enable --now barber-bot
journalctl -u barber-bot -f          # смотреть логи в реальном времени
```

### Вариант Б — Docker (рекомендуется)

В проекте уже есть `Dockerfile` и `docker-compose.yml` (бот + PostgreSQL +
автоматические бэкапы). Развёртывание одной командой:

```bash
cp .env.example .env && nano .env     # BOT_TOKEN, ADMIN_IDS
docker compose up -d --build
```
Миграции применяются автоматически при старте. Тестовые данные (по желанию):
```bash
docker compose exec bot python -m db.seed
```

---

## ⚙️ Конфигурация (.env)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — (обязательно) | Токен от @BotFather |
| `ADMIN_IDS` | — | ID администраторов через запятую: `123,456` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./bot.db` | SQLite (дев) или `postgresql+asyncpg://...` (прод) |
| `TIMEZONE` | `Europe/Moscow` | Часовой пояс салона |
| `USE_WEBHOOK` | `false` | `false` = polling (просто), `true` = webhook (нужен https-домен) |
| `WEBHOOK_URL` | — | Публичный адрес, напр. `https://example.com` (только при webhook) |
| `WEBHOOK_PATH` | `/webhook` | Путь вебхука |
| `WEBHOOK_SECRET` | — | Секрет проверки запросов Telegram |
| `WEB_SERVER_HOST` | `0.0.0.0` | Хост веб-сервера (health/metrics/webhook) |
| `WEB_SERVER_PORT` | `8080` | Порт веб-сервера |
| `LOG_FILE` | — | Путь к файлу лога (пусто = только консоль) |
| `LOG_JSON` | `false` | `true` = структурированные JSON-логи |
| `SENTRY_DSN` | — | DSN Sentry для трекинга ошибок (опционально) |
| `POSTGRES_PASSWORD` | `barber` | Пароль БД для docker-compose |
| `BACKUP_INTERVAL_SECONDS` | `86400` | Как часто делать бэкап (docker) |
| `BACKUP_RETENTION_DAYS` | `7` | Сколько дней хранить бэкапы |

---

## 📂 Структура проекта

```
barber_bot/
├── bot/
│   ├── main.py            # точка входа (запуск polling/webhook)
│   ├── config.py          # чтение настроек из .env
│   ├── texts.py           # все тексты сообщений (легко менять)
│   ├── states.py          # шаги диалогов (FSM)
│   ├── callbacks.py       # данные инлайн-кнопок
│   ├── health.py          # /health для мониторинга
│   ├── metrics.py         # /metrics (Prometheus)
│   ├── logging_config.py  # JSON-логи
│   ├── handlers/          # обработчики команд и кнопок
│   │   ├── start.py        #   /start и главное меню
│   │   ├── booking.py      #   сценарий записи
│   │   ├── my_bookings.py  #   мои записи / отмена
│   │   └── admin.py        #   админ-панель
│   ├── keyboards/         # клавиатуры (кнопки)
│   ├── middlewares/       # rate-limiting (антиспам)
│   └── services/          # бизнес-логика (слоты, брони, напоминания)
├── db/
│   ├── models.py          # таблицы базы данных
│   ├── session.py         # подключение к БД
│   └── seed.py            # тестовые данные
├── alembic/               # миграции схемы БД
├── tests/                 # автотесты (pytest)
├── backup/backup.sh       # скрипт бэкапов
├── Dockerfile             # сборка контейнера
├── docker-compose.yml     # бот + PostgreSQL + бэкапы
├── requirements.txt       # зависимости Python
├── .env.example           # шаблон настроек
├── README.md              # документация разработчика
└── ADMIN_GUIDE.md         # инструкция для администратора салона
```

---

## 🗄 Схема базы данных

```
salons (салоны)
├── id (PK)
├── name, address, timezone
│
├──< masters (мастера)
│   ├── id (PK), salon_id (FK → salons)
│   ├── name, description, is_active
│   │
│   ├──< working_hours (график)        ┐ unique(master_id, weekday)
│   │   └── weekday, start_time, end_time
│   ├──< time_off (блокировки времени)
│   │   └── start_at, end_at, reason
│   └──< master_services (услуги мастера)  ┐ unique(master_id, service_id)
│       ├── master_id (FK), service_id (FK)
│       └── price_override, duration_override
│
└──< services (услуги)
    ├── id (PK), salon_id (FK → salons)
    └── name, duration_minutes, base_price_kopecks, is_active

clients (клиенты)
├── id (PK), telegram_id (unique)
└── username, first_name, phone

bookings (записи)
├── id (PK)
├── client_id (FK → clients)
├── master_id (FK → masters)
├── service_id (FK → services)
├── start_at, end_at, price_kopecks
├── status (active / cancelled / completed / no_show)
└── reminder_job_id
    ⓘ Частичный уникальный индекс (master_id, start_at) WHERE status='active'
      — защита от двойного бронирования одного слота.
```
> 💰 Цены хранятся в копейках (целое число) — чтобы не было ошибок округления.

---

## 🧭 Сценарии использования

### Путь клиента
```
/start
└── Главное меню
    ├── 📅 Записаться
    │   └── выбор услуги → выбор мастера → выбор даты → выбор времени
    │       └── подтверждение → ✅ запись создана (+ напоминание за час)
    ├── 📋 Мои записи
    │   └── список активных → [Отменить]
    └── ℹ️ О нас / контакты
```

### Путь администратора (FSM)
```
/admin  (доступ только для ADMIN_IDS)
└── Админ-меню
    ├── 🗓 Записи на сегодня
    ├── 👤 Мастера        → нажатие переключает ✅/⛔
    ├── ✂️ Услуги         → нажатие переключает ✅/⛔
    ├── 🚫 Заблокировать время
    │   └── выбрать мастера → [FSM] прислать «ГГГГ-ММ-ДД ЧЧ:ММ ЧЧ:ММ причина»
    │       └── ✅ блокировка создана
    └── 📋 Список блокировок → нажатие удаляет блокировку
```

---

## 🎨 Настройка контента

### Через бота (`/admin`)
Мастера, услуги и блокировки времени управляются прямо из админ-панели —
подробно см. **[ADMIN_GUIDE.md](ADMIN_GUIDE.md)** (инструкция простым языком).

### Изменить названия/тексты/цены стартового набора
Тексты сообщений — в `bot/texts.py`. Стартовый набор мастеров и услуг —
в `db/seed.py`.

### Сброс и повторное наполнение базы (SQLite)
```bash
del bot.db                      # Windows  (rm bot.db на macOS/Linux)
python -m alembic upgrade head
python -m db.seed
```

---

## 🔧 Обновление и обслуживание

### Обновить код
```bash
git pull
pip install -r requirements.txt      # если менялись зависимости
python -m alembic upgrade head       # если менялась схема БД
sudo systemctl restart barber-bot    # или: docker compose up -d --build
```

### Бэкап базы данных
**SQLite:** просто скопируйте файл `bot.db` в надёжное место.

**PostgreSQL вручную:**
```bash
pg_dump -U barber barber_bot | gzip > backup_$(date +%F).sql.gz
```
**PostgreSQL по расписанию (cron, ежедневно в 3:00):**
```
0 3 * * * pg_dump -U barber barber_bot | gzip > /backups/barber_$(date +\%F).sql.gz
```
> В Docker-варианте бэкапы делаются автоматически (сервис `backup`).

### Быстрые команды systemd

| Действие | Команда |
|---|---|
| Статус | `sudo systemctl status barber-bot` |
| Перезапуск | `sudo systemctl restart barber-bot` |
| Остановить | `sudo systemctl stop barber-bot` |
| Логи (хвост) | `journalctl -u barber-bot -f` |
| Автозапуск вкл | `sudo systemctl enable barber-bot` |

### Частые проблемы

| Симптом | Причина | Решение |
|---|---|---|
| Бот не отвечает | Процесс не запущен | Проверить `systemctl status` / окно cmd |
| `TokenValidationError` | Неверный токен | Проверить `BOT_TOKEN` в `.env` |
| Нет свободных слотов | Нет графика мастера / всё занято / блокировка | Проверить через `/admin` |
| `/admin` недоступен | Неверный `ADMIN_IDS` | Вписать свой Telegram ID |
| Не приходят напоминания | Часовой пояс / бот падал | Проверить `TIMEZONE` и логи |
| Ошибка подключения к БД | Неверный `DATABASE_URL` | Проверить строку подключения |
| Двойная запись на слот | (защищено индексом БД) | Не должно происходить; если да — прислать логи |

---

## 📄 Лицензия

MIT. Свободно использовать и изменять.

---

<details>
<summary>✅ Чеклист перед сдачей клиенту (нажмите, чтобы раскрыть)</summary>

- [ ] **Токен** вписан в `.env`, рабочий, проверен (бот отвечает на `/start`)
- [ ] **ADMIN_IDS** заданы, `/admin` открывается у нужных людей
- [ ] **Контент** наполнен: мастера, услуги, графики работы (через `/admin` или `seed.py`)
- [ ] **Тестовая запись** проведена end-to-end (запись → напоминание → отмена)
- [ ] **systemd / Docker** настроен, бот переживает перезапуск сервера
- [ ] **Бэкап** настроен и проверено восстановление
- [ ] **ADMIN_GUIDE.md** передан администратору салона
- [ ] **Уведомления о падениях** настроены (Sentry / мониторинг health-check)

</details>
