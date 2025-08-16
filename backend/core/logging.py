

from __future__ import annotations
import logging
import os
import sys
from loguru import logger

# --- stdlib → loguru bridge -------------------------------------------------
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except Exception:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        # Walk the stack to find the caller outside logging module
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[attr-defined]
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def init_logging():
    """Initialize Loguru with sane defaults, JSON/console switch, file rotation, and
    intercept stdlib/uvicorn logs. Safe to call multiple times (idempotent)."""
    # Remove all previous handlers
    logger.remove()

    # Read environment without importing settings to avoid circular deps
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    json_logs = _env_bool("JSON_LOGS", False)
    log_file = os.getenv("LOG_FILE_PATH")

    # Console sink
    console_fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
        "<level>{level: <8}</level> "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stdout,
        level=level,
        colorize=not json_logs,
        serialize=json_logs,
        backtrace=False,  # set True during deep debugging
        diagnose=False,
        format=console_fmt,
        enqueue=True,
    )

    # Optional file sink with rotation/retention
    if log_file:
        logger.add(
            log_file,
            level=level,
            rotation="10 MB",
            retention="14 days",
            compression="zip",
            enqueue=True,
            serialize=json_logs,
            colorize=False,
            backtrace=False,
            diagnose=False,
            format=console_fmt,
        )

    # Intercept stdlib logging (incl. FastAPI/Uvicorn)
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.setLevel(level)
        logging_logger.propagate = False

    # Convenience alias
    return logger
