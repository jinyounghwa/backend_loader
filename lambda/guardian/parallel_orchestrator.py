"""
Parallel Guardian Orchestrator — async parallel check execution.

Delegates to the main GuardianOrchestrator for checker creation and
result processing. Runs checks in parallel using ``check_async()``
(which wraps sync ``check()`` via ``run_in_executor``).
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

from guardian.checkers.base import _run_sync
from guardian.config import Config
from guardian.orchestrator import GuardianOrchestrator


class ParallelOrchestrator:
    """Run all Guardian checks in parallel using asyncio."""

    def __init__(self, orchestrator: GuardianOrchestrator):
        self._orch = orchestrator

    async def run_all_checks_parallel(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Run all checks in parallel and aggregate results."""
        check_type = event.get("check_type", "all").lower()
        checks_to_run = self._orch._get_checks_for_type(check_type)

        async def _run_check(name: str):
            checker = self._orch.checkers.get(name)
            if not checker:
                return name, None
            try:
                result = await checker.check_async()
                return name, result
            except Exception as exc:
                self._orch.logger.error("Parallel check %s failed: %s", name, exc)
                return name, None

        tasks = [_run_check(name) for name in checks_to_run]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        aggregated: Dict[str, Any] = {
            "timestamp": event.get("time", datetime.now(timezone.utc).isoformat()),
            "check_type": check_type,
            "checks": {},
            "accounts": [],
        }

        for name, result in results:
            if result is not None:
                aggregated["checks"][name] = result.to_dict()

        return {"statusCode": 200, "body": aggregated}


def run_all_checks(orchestrator: GuardianOrchestrator, event: Dict[str, Any]) -> Dict[str, Any]:
    """Sync entry point — creates a ParallelOrchestrator and runs checks."""
    parallel = ParallelOrchestrator(orchestrator)
    return _run_sync(parallel.run_all_checks_parallel(event))
