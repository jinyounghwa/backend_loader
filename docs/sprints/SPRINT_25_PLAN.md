# Sprint 25: Advanced Checkers & Feature Expansion

**Target**: Add 2 new checkers (RDS, IAM Policy Analyzer), expand API coverage, improve error resilience

**Duration**: 3-4 days (estimated)

---

## Overview

Sprint 25 expands AWS Guardian with two sophisticated new checkers that analyze database security and IAM policy configurations. This sprint adds **35+ new tests**, **200+ lines of type-safe checker code**, and **2 new API endpoints**.

### New Deliverables

| Item | Scope | Status |
|------|-------|--------|
| **RDSChecker** | Check RDS instances for public accessibility, backup, encryption | NEW |
| **IAMPolicyAnalyzer** | Analyze IAM policies for overly-permissive actions | NEW |
| **/api/rds-status** | RDS health/security endpoint | NEW |
| **/api/iam-policies** | IAM policy analysis endpoint | NEW |
| Expanded test suite | 35+ new tests | NEW |

---

## Phase 1: RDS Checker Implementation

### Files to Create/Modify

```
lambda/guardian/checkers/rds.py (NEW - 150 lines)
tests/lambda/test_rds_checker_harness.py (NEW - 80 lines)
lambda/guardian/checkers/__init__.py (UPDATE - register RDSChecker)
lambda/guardian/orchestrator.py (UPDATE - add RDS to checkers list)
lambda/guardian/parallel_orchestrator.py (UPDATE - add RDS async task)
```

### RDSChecker Security Checks

Detect security issues in RDS instances:
1. **PubliclyAccessible = true** (HIGH severity)
2. **StorageEncrypted = false** (MEDIUM severity)
3. **BackupRetentionPeriod < 7 days** (LOW severity)
4. **EnableIAMDatabaseAuthentication = false** (MEDIUM severity)
5. **EnableCloudwatchLogsExports = []** (LOW severity)

---

## Phase 2: IAM Policy Analyzer Implementation

### Files to Create/Modify

```
lambda/guardian/checkers/iam_policy_analyzer.py (NEW - 200 lines)
tests/lambda/test_iam_policy_checker_harness.py (NEW - 100 lines)
lambda/guardian/orchestrator.py (UPDATE - add IAMPolicyAnalyzer)
lambda/guardian/parallel_orchestrator.py (UPDATE - add async task)
```

### IAMPolicyAnalyzer Security Checks

Detect overly-permissive IAM policies:
1. **Action: "*" with Resource: "*"** (CRITICAL severity)
2. **Action: "iam:*" or "ec2:*"** (HIGH severity)
3. **Action: "s3:GetObject" with Resource: "*"** (HIGH severity)
4. **NotAction with Deny Effect** (MEDIUM severity)

---

## Phase 3: New API Endpoints

### `/api/rds-status` - RDS Security Status

Returns RDS instance security analysis by region.

### `/api/iam-policies` - IAM Policy Analysis

Returns policy analysis with risk levels and remediation guidance.

---

## Phase 4: Integration & Testing

### Test Coverage

- `tests/lambda/test_rds_checker_harness.py` - 8 tests
- `tests/lambda/test_iam_policy_checker_harness.py` - 10 tests
- Update `tests/lambda/test_performance_baseline.py` - 2 new performance tests

### Documentation Updates

- Update `ARCHITECTURE.md` - Add RDS and IAM Policy Analyzer
- Update `CONTRIBUTING.md` - Checker implementation patterns
- Create `docs/CHECKER_CATALOG.md` - All 8 checkers documented

---

## Success Criteria

- [ ] RDSChecker: 8/8 tests passing, < 500ms performance
- [ ] IAMPolicyAnalyzer: 10/10 tests passing, < 500ms performance
- [ ] Combined: All 8 checkers < 3 seconds
- [ ] API endpoints: 2 new endpoints functional
- [ ] Documentation: CHECKER_CATALOG.md complete
- [ ] Type safety: mypy clean

---

## Implementation Order

1. Day 1: RDSChecker (code + tests + integration)
2. Day 2: IAMPolicyAnalyzer (code + tests + integration)
3. Day 3: API endpoints + documentation
4. Day 4: Final testing and cleanup

---

**Next Sprint**: Sprint 26 - Integration Testing & Edge Cases
