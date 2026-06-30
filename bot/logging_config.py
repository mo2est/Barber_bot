"""JSON-форматтер логов — для прода, где логи парсит ELK/Loki/CloudWatch и т.п."""

from __future__ import annotations

import json
import logging
import traceback


class JsonFormatter(logging.Formatter):
    """Каждая запись лога — одна строка JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(payload, ensure_ascii=False)
