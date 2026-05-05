# AWS Guardian API Reference

All endpoints require NextAuth session authentication via `Authorization: Bearer` header or session cookie.

---

## Status & Health

### GET /api/status
**Multi-region health check with DynamoDB fallback**

**Auth**: Required  
**Query Parameters**:
- `regions` (optional): Comma-separated region list (e.g., `ap-northeast-1,us-east-1`)

**Response**:
```json
{
  "cost": { "today_cost": 150, "monthly_cost": 3500, ... },
  "ec2": { "total_instances": 5, "running_instances": 4, "anomalies": [...] },
  "s3": { "total_buckets": 10, "public_buckets": 1, "anomalies": [...] },
  "recent_events": [...],
  "last_check": "2026-05-05T10:30:00Z",
  "next_check": "2026-05-05T11:30:00Z",
  "system_health": "healthy",
  "is_stale": false
}
```

---

## Events

### GET /api/events
**Retrieve recent security events with optional filtering**

**Auth**: Required  
**Query Parameters**:
- `type` (optional): Filter by event type (ec2, s3, cost, etc.)
- `severity` (optional): Filter by severity (info, warning, critical)
- `hours` (optional, default: 24): Hours to look back

**Response**:
```json
{
  "events": [
    {
      "event_id": "evt-xxx",
      "event_type": "ec2",
      "severity": "critical",
      "timestamp": "2026-05-05T10:15:00Z",
      "details": { "instance_id": "i-123", "region": "ap-northeast-1" }
    }
  ],
  "total": 5
}
```

### GET /api/events/stream
**Real-time event stream (SSE)**

**Auth**: Required  
**Response**: Server-Sent Events stream with new events every 2 seconds (mock mode)

---

## Actions & Remediation

### GET /api/actions
**List auto-response actions with optional filtering**

**Auth**: Required  
**Query Parameters**:
- `type` (optional): Filter by action type (stop_instance, block_bucket, etc.)
- `status` (optional): Filter by status (pending, success, failed)

**Response**:
```json
{
  "actions": [
    {
      "action_id": "act-001",
      "type": "stop_instance",
      "resource_id": "i-123",
      "status": "success",
      "timestamp": "2026-05-05T10:00:00Z",
      "region": "ap-northeast-1"
    }
  ],
  "total": 3
}
```

### GET /api/actions/stream
**Real-time action stream (SSE)**

**Auth**: Required  
**Response**: Server-Sent Events stream with new actions every 5 seconds (mock mode)

### POST /api/remediate
**Execute immediate remediation action**

**Auth**: Required (admin role)  
**Request Body**:
```json
{
  "resource_id": "i-123",
  "action_type": "stop_instance",
  "region": "ap-northeast-1",
  "dry_run": false
}
```

**Response**: 200 OK with action result

### POST /api/rollback
**Reverse a previous auto-response action**

**Auth**: Required (admin role)  
**Request Body**:
```json
{
  "action_id": "act-001",
  "region": "ap-northeast-1"
}
```

**Response**: 200 OK with rollback result

---

## Accounts

### GET /api/accounts
**List connected AWS accounts (multi-account support)**

**Auth**: Required  
**Response**:
```json
{
  "accounts": [
    {
      "account_id": "123456789012",
      "account_name": "Production",
      "region": "ap-northeast-1",
      "role_arn": "arn:aws:iam::123456789012:role/guardian"
    }
  ]
}
```

---

## AI Analysis

### POST /api/analyze-threat
**Get AI-powered threat analysis using Gemini API**

**Auth**: Required  
**Request Body**:
```json
{
  "events": [
    {
      "event_type": "ec2",
      "severity": "critical",
      "resource_id": "i-123",
      "details": { "exposed_ports": [22, 3389] }
    }
  ]
}
```

**Response**:
```json
{
  "severity": "critical",
  "rootCause": "Exposed security group allows public SSH access",
  "remediationSteps": ["Restrict SG to known IPs", "Review access logs"],
  "preventionTips": ["Use VPC endpoints", "Enable GuardDuty"]
}
```

### POST /api/analyze-insights
**Cross-region threat correlation and pattern detection**

**Auth**: Required  
**Request Body**:
```json
{
  "regions": ["ap-northeast-1", "us-east-1"],
  "anomalies": [
    { "region": "ap-northeast-1", "type": "ec2_exposed", "count": 2 },
    { "region": "us-east-1", "type": "s3_public", "count": 1 }
  ]
}
```

**Response**:
```json
{
  "correlation_score": 85,
  "threat_type": "Multi-Region Exposure Pattern",
  "confidence": 0.92,
  "urgency": 9,
  "recommendation": "Implement global SCP to enforce security group policies",
  "cost_impact": 120,
  "remediation_rate": 0.75
}
```

---

## Cost

### POST /api/cost-anomalies
**Detect cost spikes using 7-day rolling average**

**Auth**: Required  
**Request Body**:
```json
{
  "regions": ["ap-northeast-1", "us-east-1"],
  "costData": {
    "ap-northeast-1": { "daily_costs": [...], "threshold": 10 },
    "us-east-1": { "daily_costs": [...], "threshold": 15 }
  }
}
```

**Response**:
```json
{
  "success": true,
  "anomalies": [
    {
      "region": "ap-northeast-1",
      "spike_percent": 25.5,
      "daily_impact": 120,
      "confidence": 0.95
    }
  ],
  "count": 1,
  "timestamp": "2026-05-05T10:30:00Z"
}
```

---

## Rules & Metrics

### GET /api/response-rules
**Fetch auto-response rules with optional filtering**

**Auth**: Required  
**Query Parameters**:
- `region` (optional): Filter by region (e.g., ap-northeast-1)

**Response**:
```json
{
  "rules": [
    {
      "rule_id": "rule-001",
      "region": "ap-northeast-1",
      "event_type": "unauthorized_exposure",
      "action": "stop_instance",
      "enabled": true,
      "priority": 10,
      "dry_run": false,
      "created_at": "2026-04-25T00:00:00Z",
      "created_by": "admin@example.com"
    }
  ],
  "total": 3,
  "timestamp": "2026-05-05T10:30:00Z"
}
```

### POST /api/response-rules
**Create a new auto-response rule**

**Auth**: Required (admin only)  
**Request Body**:
```json
{
  "rule_id": "rule-004",
  "region": "us-west-2",
  "event_type": "public_bucket",
  "action": "block_bucket",
  "priority": 20,
  "dry_run": true
}
```

**Response**: 201 Created with new rule

### DELETE /api/response-rules
**Delete an auto-response rule**

**Auth**: Required (admin only)  
**Query Parameters**:
- `rule_id` (required): ID of rule to delete

**Response**: 200 OK with deletion confirmation

### GET /api/remediation-metrics
**Get remediation effectiveness metrics**

**Auth**: Required  
**Query Parameters**:
- `rule_id` (optional): Filter by specific rule
- `days` (optional, default: 30): Days to analyze

**Response**:
```json
{
  "success": true,
  "metrics": [
    {
      "rule_id": "rule-001",
      "action_type": "stop_instance",
      "total_actions": 15,
      "successful_actions": 14,
      "success_rate": 0.93,
      "resolved_issues": 13,
      "resolution_rate": 0.87,
      "effectiveness_score": 0.90
    }
  ],
  "summary": {
    "total_rules": 3,
    "avg_effectiveness_score": 0.90,
    "avg_success_rate": 0.93,
    "avg_resolution_rate": 0.85
  },
  "timestamp": "2026-05-05T10:30:00Z"
}
```

---

## Audit & Notifications

### GET /api/audit-logs
**Retrieve audit trail of all actions**

**Auth**: Required  
**Query Parameters**:
- `user` (optional): Filter by user email
- `action` (optional): Filter by action type

**Response**:
```json
{
  "logs": [
    {
      "log_id": "log-001",
      "user": "admin@example.com",
      "action": "stop_instance",
      "resource_id": "i-123",
      "status": "success",
      "timestamp": "2026-05-05T10:00:00Z"
    }
  ],
  "total": 42
}
```

### POST /api/audit-logs
**Create audit log entry (internal use)**

**Auth**: Required  
**Request Body**:
```json
{
  "user": "admin@example.com",
  "action": "create_rule",
  "resource_id": "rule-004",
  "status": "success"
}
```

**Response**: 201 Created

### GET /api/notifications
**Real-time notification stream (SSE)**

**Auth**: Required  
**Response**: Server-Sent Events stream with notifications

---

## Authentication

All routes check authentication via `getAuthSession()`:
- **Local development**: Set `AWS_ENV=localstack` for hardcoded test session
- **Production**: Uses NextAuth v5 with GitHub OAuth
- **Session object**: `{ user: { email, name, role }, expires }`
- **Admin role**: Required for POST/DELETE on response-rules, remediate, rollback

---

## Error Responses

| Status | Error | Description |
|--------|-------|-------------|
| 400 | Bad Request | Missing required parameters |
| 401 | Unauthorized | No valid session |
| 403 | Forbidden | Session exists but insufficient permissions |
| 500 | Internal Server Error | Unexpected error |

All error responses follow format:
```json
{
  "error": "Error message",
  "status": 400
}
```

---

**Last Updated**: 2026-05-05  
**API Version**: v1.0  
**Total Endpoints**: 17 (35+ HTTP verb/path pairs)
