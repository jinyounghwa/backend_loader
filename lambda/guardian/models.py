"""Pydantic models for Lambda events and responses.

Provides type-safe validation for EventBridge events, checker responses,
and responder inputs.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# EventBridge Events
# ============================================================================


class EventBridgeDetail(BaseModel):
    """Base EventBridge event detail"""

    checker_type: Optional[str] = Field(None, description="Type of checker (cost, ec2, s3, etc)")
    regions: Optional[List[str]] = Field(
        default_factory=lambda: ["ap-northeast-1"],
        description="AWS regions to check",
    )

    class Config:
        extra = "allow"  # Allow additional fields


class EventBridgeScheduledEvent(BaseModel):
    """EventBridge scheduled event from EventBridge cron/rate rule"""

    version: str = Field(..., description="Event version")
    id: str = Field(..., description="Event ID")
    detail_type: str = Field(..., alias="detail-type", description="Event detail type")
    source: str = Field(..., description="Event source (aws.events)")
    account: str = Field(..., description="AWS account ID")
    time: datetime = Field(..., description="Event timestamp")
    region: str = Field(..., description="AWS region")
    resources: List[str] = Field(default_factory=list, description="Associated resources")
    detail: EventBridgeDetail = Field(..., description="Event detail")

    class Config:
        populate_by_name = True  # Allow both alias and field name


# ============================================================================
# Checker Responses
# ============================================================================


class Finding(BaseModel):
    """A security finding or anomaly"""

    severity: str = Field(
        ..., description="Finding severity (critical, high, medium, low, info)"
    )
    title: str = Field(..., description="Finding title")
    description: str = Field(..., description="Finding description")
    resource: str = Field(..., description="Affected resource ID/ARN")
    resource_type: str = Field(..., description="Resource type (ec2, s3, etc)")
    region: str = Field(..., description="AWS region")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CheckerResponse(BaseModel):
    """Response from a checker (cost, ec2, s3, etc)"""

    checker_name: str = Field(..., description="Checker name (cost, ec2, s3, cloudtrail, etc)")
    findings: List[Finding] = Field(default_factory=list, description="List of findings")
    summary: Dict[str, Any] = Field(
        default_factory=dict, description="Aggregated summary data"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    region: str = Field(..., description="Region checked")
    status: str = Field(default="success", description="Checker status (success, partial, error)")
    error_message: Optional[str] = Field(None, description="Error message if status is error")


# ============================================================================
# Responder Inputs
# ============================================================================


class RemediationAction(BaseModel):
    """Auto-remediation action to execute"""

    action_type: str = Field(
        ..., description="Action type (stop_ec2, block_s3, revoke_iam, isolate_vpc)"
    )
    resource: str = Field(..., description="Resource ARN/ID")
    region: str = Field(..., description="Resource region")
    reason: str = Field(..., description="Reason for action")
    auto_remediate: bool = Field(default=True, description="Whether to auto-execute")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResponderInput(BaseModel):
    """Input for responders (telegram, discord, auto-remediation)"""

    findings: List[Finding] = Field(..., description="Findings to respond to")
    actions: List[RemediationAction] = Field(
        default_factory=list, description="Remediation actions"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = Field(default_factory=dict, description="Custom tags")


# ============================================================================
# DynamoDB Records
# ============================================================================


class AuditLogRecord(BaseModel):
    """DynamoDB audit log record"""

    log_id: str = Field(..., description="Unique log ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Affected resource")
    severity: str = Field(default="info")
    details: Dict[str, Any] = Field(default_factory=dict)
    user: Optional[str] = Field(None, description="User who triggered action")


class RemediationMetricRecord(BaseModel):
    """DynamoDB remediation metric record"""

    metric_id: str = Field(..., description="Unique metric ID")
    rule_id: str = Field(..., description="Associated rule ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action_type: str = Field(..., description="Action type")
    success: bool = Field(default=False)
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    affected_resources: int = Field(default=0)
    error_message: Optional[str] = Field(None)


# ============================================================================
# API Response Models
# ============================================================================


class StatusResponse(BaseModel):
    """API /status response"""

    status: str = Field(..., description="Overall status (healthy, degraded, unhealthy)")
    last_check: datetime = Field(...)
    checks: Dict[str, Any] = Field(default_factory=dict, description="Per-checker status")
    regions: Optional[List[Dict[str, Any]]] = Field(
        None, description="Multi-region status if queried"
    )


class EventsResponse(BaseModel):
    """API /events response"""

    total: int = Field(...)
    events: List[Dict[str, Any]] = Field(...)
    filters_applied: Dict[str, str] = Field(default_factory=dict)


class ResponseRuleRecord(BaseModel):
    """Response rule for auto-remediation"""

    rule_id: str = Field(..., description="Unique rule ID")
    name: str = Field(..., description="Rule name")
    trigger: str = Field(..., description="Trigger condition")
    action: str = Field(..., description="Action to execute")
    enabled: bool = Field(default=True)
    regions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
