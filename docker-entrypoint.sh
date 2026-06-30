#!/bin/sh
# Накатываем миграции перед каждым стартом контейнера — безопасно
# (alembic upgrade head идемпотентен), удобно для docker-compose up.
set -e

echo "-> Применяю миграции БД..."
python -m alembic upgrade head

exec "$@"
