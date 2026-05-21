"""JSON logging configuration for AWS Guardian"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "action"):
            log_data["action"] = record.action
        if hasattr(record, "resource"):
            log_data["resource"] = record.resource
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "detail"):
            log_data["detail"] = record.detail

        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Configure logger with both console and file handlers.

    Guard against duplicate handlers when called multiple times
    (e.g. in tests or Lambda re-initialization).
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # Console handler (INFO+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (DEBUG+) with JSON format
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning("Could not set up file logging: %s", e)

    return logger


def log_check_result(logger: logging.Logger, check_type: str, status: str, detail: Optional[str] = None) -> None:
    logger.info(
        "%s: %s",
        check_type,
        status,
        extra={
            "action": "check_result",
            "resource": check_type,
            "status": status,
            "detail": detail or "",
        },
    )


def log_remediation(
    logger: logging.Logger, action: str, resource: str, status: str, detail: Optional[str] = None
) -> None:
    logger.info(
        "%s: %s - %s",
        action,
        resource,
        status,
        extra={
            "action": "remediation",
            "resource": resource,
            "status": status,
            "detail": detail or "",
        },
    )
