"""Structured application logging."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

LOG_FIELDS = (
    "session_id",
    "tool",
    "duration_ms",
    "order_id",
    "status_code",
    "method",
    "path",
    "engine",
    "error_type",
)

application_logger = logging.getLogger("cerebro_lu")
application_logger.addHandler(logging.NullHandler())


class JsonFormatter(logging.Formatter):
    """Format application records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for field_name in LOG_FIELDS:
            value = getattr(record, field_name, None)
            if value is not None:
                payload[field_name] = value
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    """Configure the project logger once."""

    logger = logging.getLogger("cerebro_lu")
    logger.setLevel(level.upper())
    logger.propagate = False
    logger.handlers = [
        handler
        for handler in logger.handlers
        if not isinstance(handler, logging.NullHandler)
    ]
    if logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the application namespace."""

    return logging.getLogger(f"cerebro_lu.{name}")
