"""Base class for all AWS Guardian checkers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CheckResult:
    """Standard result format for all checkers."""

    SEVERITY_LEVELS = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def __init__(
        self,
        severity: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggested_action: Optional[str] = None,
    ):
        if severity not in self.SEVERITY_LEVELS:
            raise ValueError(f"Invalid severity: {severity}. Must be one of {self.SEVERITY_LEVELS}")

        self.severity = severity
        self.title = title
        self.message = message
        self.details = details or {}
        self.suggested_action = suggested_action

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "suggested_action": self.suggested_action,
        }

    @classmethod
    def info(cls, title: str, message: str) -> "CheckResult":
        """Create INFO result."""
        return cls("INFO", title, message)

    @classmethod
    def error(cls, title: str, message: str) -> "CheckResult":
        """Create ERROR result."""
        return cls("HIGH", title, message, suggested_action="Manual investigation required")


class BaseChecker(ABC):
    """Abstract base class for all checkers."""

    def __init__(
        self,
        clients: Dict[str, Any],
        config: Dict[str, Any],
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize checker with AWS clients and configuration.

        Args:
            clients: Dict of boto3 clients (ec2, s3, cloudtrail, etc.)
            config: Configuration dict with settings like regions, thresholds
            account_id: Optional account ID for cross-account checks
            credentials: Optional temporary credentials for cross-account access
        """
        self.clients = clients
        self.config = config
        self.account_id = account_id
        self.credentials = credentials

    @abstractmethod
    def check(self) -> CheckResult:
        """
        Run the check and return result.

        Must be implemented by subclasses.

        Returns:
            CheckResult with severity, title, message, details, suggested_action
        """
        pass

    async def check_async(self) -> CheckResult:
        """Async version of check() - can be overridden for parallel execution.

        Default implementation runs check() in thread pool for non-blocking I/O.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.check)

    def _log_check_start(self, check_name: str):
        logger.info("Starting %s check", check_name)

    def _log_check_end(self, check_name: str, severity: str):
        logger.info("Completed %s check: %s", check_name, severity)

    def _log_error(self, check_name: str, error: Exception):
        logger.error("Error in %s: %s", check_name, str(error))
