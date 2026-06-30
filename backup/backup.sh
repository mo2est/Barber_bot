#!/bin/sh
# Периодический pg_dump с ретеншеном. Запускается отдельным сервисом в
# docker-compose (образ postgres:16-alpine — pg_dump там уже есть).
set -eu

mkdir -p /backups

while true; do
    ts="$(date +%Y%m%d_%H%M%S)"
    out="/backups/barber_bot_${ts}.sql.gz"

    echo "[$(date -Iseconds)] Бэкап -> ${out}"
    if pg_dump -h "${PGHOST}" -U "${PGUSER}" "${PGDATABASE}" | gzip > "${out}"; then
        echo "[$(date -Iseconds)] OK: $(du -h "${out}" | cut -f1)"
    else
        echo "[$(date -Iseconds)] ОШИБКА бэкапа" >&2
        rm -f "${out}"
    fi

    find /backups -name "*.sql.gz" -mtime "+${BACKUP_RETENTION_DAYS:-7}" -delete

    sleep "${BACKUP_INTERVAL_SECONDS:-86400}"
done
