"""Guardian models package.

Exposes both the ML models (anomaly detection / forecasting) and the
Pydantic schemas used for type-safe validation of Lambda events,
checker responses, responder inputs, and API payloads.

Note: the Pydantic schemas previously lived in a sibling ``models.py``
module, which was shadowed by this package on import. They now live in
``schemas.py`` and are re-exported here so ``from guardian.models import
CheckerResponse`` continues to work.
"""

from .isolation_forest_detector import IsolationForestDetector
from .schemas import (
    AuditLogRecord,
    CheckerResponse,
    EventBridgeDetail,
    EventBridgeScheduledEvent,
    EventsResponse,
    Finding,
    RemediationAction,
    RemediationMetricRecord,
    ResponderInput,
    ResponseRuleRecord,
    StatusResponse,
)
from .time_series_forecaster import TimeSeriesForecaster

__all__ = [
    # ML models
    "IsolationForestDetector",
    "TimeSeriesForecaster",
    # Pydantic schemas
    "AuditLogRecord",
    "CheckerResponse",
    "EventBridgeDetail",
    "EventBridgeScheduledEvent",
    "EventsResponse",
    "Finding",
    "RemediationAction",
    "RemediationMetricRecord",
    "ResponderInput",
    "ResponseRuleRecord",
    "StatusResponse",
]
