"""Multi-account AWS support for Guardian.

Consolidated from the former ``guardian.multiaccount`` package so that all
multi-account functionality lives under a single package name.
"""

from .account_manager import (
    AccountAggregator,
    AccountManager,
    AccountRegistry,
    RoleAssumer,
)
from .consolidated_reporter import ConsolidatedReporter
from .role_assumptioner import RoleAssumptioner

__all__ = [
    "AccountAggregator",
    "AccountManager",
    "AccountRegistry",
    "RoleAssumer",
    "ConsolidatedReporter",
    "RoleAssumptioner",
]
