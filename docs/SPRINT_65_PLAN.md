# Sprint 65: Real AWS Integration & Advanced Features

**Status:** Planning (next sprint after Sprint 64)

**Goal:** Production-ready AWS integration with real API calls, multi-account support, and advanced automation

---

## Overview

Sprint 65 replaces simulated implementations with real AWS APIs and adds enterprise features for multi-account environments. The system transitions from proof-of-concept to production-grade cost optimization platform.

---

## Phases & Test Plan

| Phase | Component | Tests | Focus |
|-------|-----------|-------|-------|
| 1 | Real AWS API Integration | 12 | Cost Explorer, EC2, S3, RDS, Lambda, DynamoDB actual calls |
| 2 | CloudTrail Anomaly Detection | 11 | Real-time event streaming, pattern recognition, threat scoring |
| 3 | Multi-Account Management | 10 | Cross-account role assumption, consolidated reporting |
| 4 | Advanced Dashboard & Automation | 12 | Real-time WebSocket updates, smart remediation, cost predictions |
| **Total** | **Sprint 65** | **45** | **Production-ready system** |

**Cumulative:** 70 (Sprint 64) + 45 (Sprint 65) = **115 tests**

---

## Phase 1: Real AWS API Integration (12 tests)

### Implementation Files
- `lambda/guardian/integrations/cost_explorer_client.py` — Real Cost Explorer API calls
- `lambda/guardian/integrations/ec2_manager.py` — EC2 actions via boto3
- `lambda/guardian/integrations/s3_manager.py` — S3 operations via boto3
- `lambda/guardian/integrations/rds_manager.py` — RDS modifications via boto3
- `lambda/guardian/integrations/lambda_manager.py` — Lambda optimization via boto3
- `lambda/guardian/integrations/dynamodb_manager.py` — DynamoDB tuning via boto3
- `tests/backend/test_aws_integration.py` — 12 integration tests

### Test Cases
1. `test_cost_explorer_daily_cost` — Fetch actual daily costs
2. `test_cost_explorer_monthly_trend` — Get monthly cost trends
3. `test_ec2_list_instances` — List instances with real filters
4. `test_ec2_stop_instance` — Actually stop EC2 instance
5. `test_s3_list_buckets` — List S3 buckets with policies
6. `test_s3_block_public_access` — Apply block public settings
7. `test_rds_modify_instance` — Modify RDS instance class
8. `test_lambda_get_metrics` — Fetch Lambda CloudWatch metrics
9. `test_lambda_update_memory` — Update function memory config
10. `test_dynamodb_get_table_metrics` — Get DynamoDB metrics
11. `test_dynamodb_update_ttl` — Enable/disable TTL
12. `test_batch_operations` — Execute multi-service batch operations

---

## Phase 2: CloudTrail Anomaly Detection (11 tests)

### Implementation Files
- `lambda/guardian/cloudtrail/event_processor.py` — Parse CloudTrail events
- `lambda/guardian/cloudtrail/pattern_matcher.py` — Detect suspicious patterns
- `lambda/guardian/cloudtrail/threat_scorer.py` — Calculate threat scores
- `lambda/guardian/storage/cloudtrail_events.py` — Store events for analysis
- `tests/backend/test_cloudtrail_detection.py` — 11 detection tests

### Detectable Patterns
- Unauthorized region access (EC2 in unexpected regions)
- Mass deletion attempts (multiple resource deletions)
- Permission escalation (IAM policy changes)
- Unusual authentication patterns (failed logins, MFA bypass attempts)
- Cost spike triggers (resource provisioning spikes)
- Suspicious API patterns (high volume in short window)

### Test Cases
1. `test_parse_cloudtrail_event` — Parse raw CloudTrail JSON
2. `test_detect_unauthorized_region` — Identify EC2 in new regions
3. `test_detect_mass_deletion` — Catch bulk resource deletions
4. `test_detect_permission_escalation` — Identify IAM policy changes
5. `test_detect_auth_anomaly` — Flag unusual authentication
6. `test_calculate_threat_score` — Score threat severity
7. `test_pattern_correlation` — Connect related events
8. `test_temporal_analysis` — Detect time-based patterns
9. `test_false_positive_filtering` — Reduce alert fatigue
10. `test_event_enrichment` — Add context to alerts
11. `test_batch_event_processing` — Process event stream efficiently

---

## Phase 3: Multi-Account Management (10 tests)

### Implementation Files
- `lambda/guardian/multiaccount/role_assumptioner.py` — Cross-account role assumption
- `lambda/guardian/multiaccount/account_manager.py` — Multi-account orchestration
- `lambda/guardian/multiAccount/consolidated_reporter.py` — Aggregate costs across accounts
- `lambda/guardian/storage/account_registry.py` — Store account configurations
- `tests/backend/test_multiaccountmanagement.py` — 10 multi-account tests

### Features
- STS AssumeRole for cross-account access
- Per-account cost limits and thresholds
- Consolidated cost dashboard (all accounts)
- Account-specific alert policies
- Cost allocation by business unit/team

### Test Cases
1. `test_assume_cross_account_role` — Assume role in member account
2. `test_list_accounts` — List registered accounts
3. `test_register_new_account` — Add new account to system
4. `test_per_account_cost_query` — Get costs per account
5. `test_consolidated_cost_view` — Aggregate all account costs
6. `test_account_specific_rules` — Apply rules per account
7. `test_cross_account_anomaly` — Detect anomalies across accounts
8. `test_cost_allocation_by_team` — Allocate costs to business units
9. `test_account_permission_validation` — Verify cross-account permissions
10. `test_account_cost_comparison` — Compare costs across accounts

---

## Phase 4: Advanced Dashboard & Automation (12 tests)

### Implementation Files
- `lambda/guardian/automation/smart_remediation.py` — Intelligent remediation decisions
- `lambda/guardian/automation/schedule_optimizer.py` — Schedule-based optimization
- `lambda/guardian/automation/predictive_scaling.py` — Forecast-driven scaling
- `apps/web/src/components/CostTrends.tsx` — Cost trend visualization
- `apps/web/src/components/AnomalyInsights.tsx` — Anomaly explanation
- `apps/web/src/components/RemediationHistory.tsx` — Actions audit trail
- `tests/backend/test_advanced_automation.py` — 12 advanced automation tests

### Features
- Smart remediation: Don't stop production EC2, suggest alternatives
- Schedule-based optimization: Stop instances during off-hours
- Predictive scaling: Scale based on forecasted demand
- Anomaly explanation: Why did costs spike?
- Remediation history: What actions were taken and results

### Test Cases
1. `test_smart_remediation_ec2` — Suggest alternatives to stopping
2. `test_schedule_based_optimization` — Off-hours automation
3. `test_predictive_scaling_lambda` — Scale based on forecast
4. `test_cost_spike_explanation` — Explain anomalies
5. `test_remediation_success_rate` — Track action effectiveness
6. `test_abort_remediation_on_risk` — Stop unsafe actions
7. `test_cascading_recommendations` — Multi-step optimization
8. `test_cost_trend_visualization` — Real-time cost charts
9. `test_anomaly_insights_generation` — Detailed anomaly reports
10. `test_action_impact_simulation` — Preview remediation effects
11. `test_cost_optimization_roadmap` — Plan future optimizations
12. `test_end_to_end_advanced_flow` — Complete intelligent workflow

---

## Implementation Strategy

### Week 1: Phase 1 (Real AWS APIs)
- Replace all simulated handlers with actual boto3 clients
- Add credential management (IAM roles, STS)
- Implement error handling and retries
- Test with real AWS resources

### Week 2: Phase 2 (CloudTrail Detection)
- Enable CloudTrail event streaming
- Build pattern matching engine
- Implement threat scoring
- Create alert rules

### Week 3: Phase 3 (Multi-Account)
- Implement STS AssumeRole flow
- Build account registry
- Create consolidated reporting
- Test cross-account access

### Week 4: Phase 4 (Advanced Features)
- Implement smart remediation logic
- Build schedule optimizer
- Create predictive scaling
- Deploy advanced dashboard components

---

## Architecture Changes

### Current (Sprint 64)
```
Simulated Handlers
    ↓
DynamoDB Storage
    ↓
Telegram/Discord Alerts
```

### Sprint 65
```
Real AWS APIs (boto3)
    ↓
CloudTrail Event Stream
    ↓
Pattern Matching Engine
    ↓
Cross-Account Orchestration
    ↓
Smart Remediation & Scaling
    ↓
Advanced Dashboard + Alerts
```

---

## Success Criteria

- [ ] All 45 tests PASS
- [ ] Real AWS API integration working
- [ ] CloudTrail event processing < 5 second latency
- [ ] Multi-account support tested
- [ ] Smart remediation prevents unsafe actions
- [ ] Production deployment ready

---

## Risk Mitigation

1. **AWS API Throttling:** Implement exponential backoff and caching
2. **Cross-Account Permissions:** Test role assumption in staging first
3. **Remediation Mistakes:** Add approval gates for risky actions
4. **Cost Accuracy:** Validate Cost Explorer data against actual bills

---

## Dependencies

- `boto3` — AWS SDK (already installed)
- `botocore` — AWS core library
- `python-dateutil` — For CloudTrail timestamp parsing
- Real AWS accounts with appropriate IAM permissions

---

## Next Steps (After Sprint 65)

**Sprint 66:** Advanced ML, real-time notifications, mobile app

---

## Notes for Next Session

- Start with Phase 1 (AWS API integration)
- Create test AWS resources in development account
- Implement proper credential handling before Phase 2
- Plan for staging environment CloudTrail stream
