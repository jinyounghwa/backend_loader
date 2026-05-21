"""Base class for all AWS Guardian checkers.

Provides a unified sync/async execution model:
- Subclasses implement ``check()`` (sync) with boto3 calls.
- ``check_async()`` automatically wraps it via ``run_in_executor``.
- For native async, override ``check_async()`` and use ``_run_sync``
  for any sync helpers.
"""

import asyncio
import concurrent.futures
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

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

    def __repr__(self) -> str:
        return f"CheckResult(severity={self.severity!r}, title={self.title!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CheckResult):
            return NotImplemented
        return (
            self.severity == other.severity
            and self.title == other.title
            and self.message == other.message
        )


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine from sync context, handling the
    'already running loop' case (e.g. inside Lambda runtime).

    This replaces the identical boilerplate previously copy-pasted
    in every checker's ``check()`` method.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Already inside an async context – offload to a worker thread.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class BaseChecker(ABC):
    """Abstract base class for all checkers.

    Execution model
    ---------------
    1. Default: subclasses override ``check()`` (sync).
       ``check_async()`` wraps it via ``run_in_executor``.
    2. Native-async: subclasses override ``check_async()``.
       ``check()`` is auto-generated using ``_run_sync``.

    Subclasses should pick **one** of the two patterns and
    implement only that method.  The other direction is handled
    automatically by this base class.
    """

    def __init__(
        self,
        clients: Dict[str, Any],
        config: Dict[str, Any],
        account_id: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
    ):
        self.clients = clients
        self.config = config
        self.account_id = account_id
        self.credentials = credentials

    # ------------------------------------------------------------------
    # Execution contract: subclasses implement EITHER check() OR check_async()
    # ------------------------------------------------------------------

    @abstractmethod
    def check(self) -> CheckResult:
        """Run the check synchronously and return result.

        Subclasses that prefer async-first should NOT override this;
        they should override ``check_async()`` instead and this method
        will be auto-provided.
        """
        # Default: delegate to async implementation
        return _run_sync(self.check_async())

    async def check_async(self) -> CheckResult:
        """Run the check asynchronously.

        Default implementation wraps ``check()`` in a thread executor
        so callers get non-blocking I/O for free.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.check)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _log_check_start(self, check_name: str) -> None:
        logger.info("Starting %s check", check_name)

    def _log_check_end(self, check_name: str, severity: str) -> None:
        logger.info("Completed %s check: %s", check_name, severity)

    def _log_error(self, check_name: str, error: Exception) -> None:
        logger.error("Error in %s: %s", check_name, str(error))

    def _handle_client_error(self, check_name: str, error: ClientError) -> CheckResult:
        error_code = error.response.get("Error", {}).get("Code", "Unknown")
        error_message = error.response.get("Error", {}).get("Message", str(error))
        self._log_error(check_name, error)
        return CheckResult.error(
            f"{check_name} Check Failed",
            f"AWS error ({error_code}): {error_message}",
        )

    def _handle_generic_error(self, check_name: str, error: Exception) -> CheckResult:
        self._log_error(check_name, error)
        return CheckResult.error(
            f"{check_name} Check Failed",
            f"Failed to check {check_name}: {str(error)}",
        )
