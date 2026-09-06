"""
Structured JSON logging with job_id context.

Usage:
    from logging_config import get_logger, JobContext

    logger = get_logger(__name__)
    logger.info("server started", extra={"port": 8000})

    # Inside a job:
    with JobContext(job_id):
        logger.info("step completed", extra={"step": "download"})
"""

import logging
import json
import sys
import os
from contextvars import ContextVar
from datetime import datetime, timezone

# ContextVar so each async task / thread can carry its own job_id
_job_id: ContextVar[str | None] = ContextVar("job_id", default=None)


class JobContext:
    """Set job_id for all log lines inside this block."""
    def __init__(self, job_id: str):
        self._id = job_id
        self._token = None

    def __enter__(self):
        self._token = _job_id.set(self._id)
        return self

    def __exit__(self, *_):
        _job_id.reset(self._token)


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per line — Loki/Promtail parses these natively."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Attach job_id when set
        jid = _job_id.get()
        if jid:
            payload["job_id"] = jid

        # Merge any extra keys the caller passed
        for key in ("step", "movie", "image_url", "actor", "duration",
                     "count", "error", "request_id", "port", "detail"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val

        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes structured JSON to stdout."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
        logger.propagate = False
    return logger
