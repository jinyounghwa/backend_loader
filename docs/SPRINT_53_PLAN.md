# Sprint 53: Multi-Account Orchestration

> **Goal**: Cross-account threat detection and coordinated remediation across multiple AWS accounts

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Sprint Duration | 1 session |
| Test Target | 15 tests (reaching ~866 cumulative) |
| Phases | 1 (Multi-Account Orchestration) |
| Priority | Cross-account threat coordination and unified monitoring |

---

## Context

**Completed (Sprint 52)**:
- Phase 1: Dashboard Integration (14 tests) ✅
- Real-time threat monitoring and visualization
- Executive metrics and aggregation
- **Cumulative**: 851 tests PASS

**Current Sprint**:
- Sprint 53 Phase 1: Multi-Account Orchestration (15 tests)
- Build cross-account threat detection
- Implement multi-account remediation coordination
- Create account-level policies and controls

---

## Sprint 53 Phase 1: Multi-Account Orchestration (15 tests)

### Objective
Build multi-account threat orchestration system that detects threats across multiple AWS accounts, applies account-specific policies, and coordinates remediation actions across organizational accounts.

### Implementation Files

#### 1. MultiAccountThreatAggregator Class
**File**: `lambda/guardian/services/multi_account_threat_aggregator.py`

```python
class MultiAccountThreatAggregator:
    def __init__(self, threat_detection_services=None, audit_logger=None):
        """Initialize with threat services for multiple accounts."""
        self.threat_services = threat_detection_services or {}
        self.audit = audit_logger
        self.aggregated_threats = []
    
    def register_account(self, account_id: str, threat_service) -> None:
        """Register a threat detection service for an account."""
    
    def detect_threats_all_accounts(self, lookback_minutes=60) -> List[Dict]:
        """
        Detect threats across all registered accounts.
        Returns aggregated threat list with account context.
        """
    
    def get_threats_by_account(self, account_id: str) -> List[Dict]:
        """Get threats specific to an account."""
    
    def identify_cross_account_threats(self) -> List[Dict]:
        """
        Identify threats that span multiple accounts.
        Examples: credential compromise, lateral movement, data exfiltration.
        """
    
    def correlate_threats_across_accounts(self) -> List[Dict]:
        """
        Find correlated threats across accounts.
        Group by threat type, timeframe, attacker patterns.
        """
    
    def get_threat_distribution(self) -> Dict:
        """Get threat distribution across all accounts."""
```

#### 2. MultiAccountRemediationOrchestrator Class
**File**: `lambda/guardian/orchestrators/multi_account_orchestrator.py`

```python
class MultiAccountRemediationOrchestrator:
    def __init__(self, remediation_executors=None, policy_manager=None, audit_logger=None):
        """Initialize with executors for multiple accounts."""
        self.executors = remediation_executors or {}
        self.policy_manager = policy_manager
        self.audit = audit_logger
        self.cross_account_executions = []
    
    def register_account_executor(self, account_id: str, executor) -> None:
        """Register a remediation executor for an account."""
    
    def remediate_threat_across_accounts(self, threat: Dict, resource_map: Dict) -> Dict:
        """
        Execute remediation across multiple accounts.
        
        resource_map: {
            'account-123': [resources],
            'account-456': [resources],
        }
        """
    
    def apply_account_policy(self, threat: Dict, account_id: str, policy: Dict) -> Dict:
        """Apply account-specific policy to threat remediation."""
    
    def coordinate_remediation_sequence(self, threats: List[Dict], dependency_map: Dict) -> Dict:
        """
        Coordinate remediation sequence when threats are interdependent.
        Respects account-level dependencies and ordering constraints.
        """
    
    def get_cross_account_execution_status(self, execution_id: str) -> Dict:
        """Get status of cross-account remediation execution."""
    
    def get_multi_account_summary(self) -> Dict:
        """Get summary of multi-account remediation activity."""
```

#### 3. AccountPolicyManager Class
**File**: `lambda/guardian/policies/account_policy_manager.py`

```python
class AccountPolicyManager:
    def __init__(self, policy_storage=None, audit_logger=None):
        """Initialize account policy management."""
        self.policies = policy_storage or {}
        self.audit = audit_logger
        self.account_policies = {}
    
    def register_account_policy(self, account_id: str, policy: Dict) -> None:
        """Register policy for specific account."""
    
    def get_account_policy(self, account_id: str) -> Dict:
        """Get policy for account."""
    
    def evaluate_threat_against_policy(self, threat: Dict, account_id: str) -> Dict:
        """
        Evaluate threat against account policy.
        Returns: {
            'allowed_strategies': [...],
            'restricted_strategies': [...],
            'approval_required': bool,
            'escalation_required': bool,
        }
        """
    
    def apply_policy_constraints(self, strategy: str, account_id: str) -> Dict:
        """Apply account-level constraints to remediation strategy."""
    
    def get_policy_violations(self, threat: Dict, account_id: str) -> List[Dict]:
        """Identify any policy violations in proposed remediation."""
```

#### 4. Multi-Account API Handler
**File**: `lambda/guardian/handlers/multi_account_handler.py`

```python
def lambda_handler(event, context):
    """
    Multi-account orchestration API endpoints.
    
    Routes:
    - GET /multi-account/threats - Threats across all accounts
    - GET /multi-account/threats/{account_id} - Account-specific threats
    - GET /multi-account/cross-account - Cross-account threats
    - POST /multi-account/remediate - Cross-account remediation
    - GET /multi-account/executions/{execution_id} - Execution status
    - GET /multi-account/summary - Multi-account summary
    """
```

### Test Files

#### Backend Tests (8 tests)
**File**: `tests/backend/test_multi_account_orchestration.py`

```python
class TestMultiAccountThreatAggregator:
    def test_register_account(self):
        """✅ Register threat service for account."""
        # Register services for multiple accounts
        # Assert registration successful

    def test_detect_threats_all_accounts(self):
        """✅ Detect threats across all accounts."""
        # Detect threats in acc-123, acc-456, acc-789
        # Assert all threats returned with account context

    def test_get_threats_by_account(self):
        """✅ Get account-specific threats."""
        # Threats in multiple accounts
        # Filter by account_id
        # Assert correct filtering

    def test_identify_cross_account_threats(self):
        """✅ Identify threats spanning multiple accounts."""
        # Lateral movement threat across accounts
        # Assert detection and correlation

class TestMultiAccountRemediationOrchestrator:
    def test_remediate_threat_across_accounts(self):
        """✅ Execute remediation across multiple accounts."""
        # Threat affecting resources in 3 accounts
        # Execute coordinated remediation
        # Assert success across all accounts

    def test_apply_account_policy(self):
        """✅ Apply account-specific policy to remediation."""
        # Different policies in different accounts
        # Assert policies enforced

    def test_coordinate_remediation_sequence(self):
        """✅ Coordinate remediation with dependencies."""
        # Threats with ordering constraints
        # Assert correct sequence
```

#### Integration Tests (7 tests)
**File**: `tests/integration/test_multi_account_integration.py`

```python
class TestMultiAccountIntegration:
    def test_end_to_end_multi_account_threat_remediation(self):
        """✅ Complete multi-account threat → remediation flow."""
        # Threat in multiple accounts
        # Detect → Strategy → Execute
        # Assert success across all accounts

    def test_cross_account_lateral_movement_detection(self):
        """✅ Detect lateral movement across accounts."""
        # Credential compromised in acc-123
        # Lateral movement attempts to acc-456, acc-789
        # Assert detection and correlation

    def test_multi_account_dashboard_aggregation(self):
        """✅ Aggregate dashboard data across accounts."""
        # Threats in 3 accounts
        # Dashboard shows unified view
        # Assert correct aggregation

    def test_account_policy_enforcement(self):
        """✅ Enforce account-specific policies."""
        # Different remediation policies per account
        # Assert policies applied correctly

    def test_multi_account_remediation_coordination(self):
        """✅ Coordinate remediation across accounts."""
        # Parallel remediation in multiple accounts
        # Assert coordination and success

    def test_cross_account_remediation_failure_handling(self):
        """✅ Handle remediation failure in one account."""
        # Remediation succeeds in acc-123, fails in acc-456
        # Assert partial success and rollback handling

    def test_multi_account_audit_trail(self):
        """✅ Generate unified audit trail across accounts."""
        # Multi-account execution
        # Assert complete audit trail with account context
```

### Key Design Decisions

1. **Account Registration Pattern**
   - Dynamic account registration
   - Support for add/remove accounts at runtime
   - No hard-coded account lists

2. **Policy Enforcement**
   - Per-account remediation policies
   - Approval workflows by account
   - Constraint-based strategy selection

3. **Cross-Account Coordination**
   - Parallel execution where independent
   - Sequential execution for dependent threats
   - Rollback support for failed accounts

4. **Threat Correlation**
   - Account-aware threat correlation
   - Lateral movement detection
   - Credential compromise tracking

5. **Unified Monitoring**
   - Single dashboard for all accounts
   - Account-level drill-down
   - Cross-account threat identification

---

## Testing Strategy

### Unit Tests (8)
- Multi-account threat detection
- Account policy application
- Remediation coordination
- Cross-account correlation

### Integration Tests (7)
- End-to-end multi-account flows
- Lateral movement detection
- Policy enforcement verification
- Failure handling and rollback
- Audit trail generation

### Test Coverage

| Component | Coverage |
|-----------|----------|
| Account registration | ✅ |
| Multi-account detection | ✅ |
| Cross-account threats | ✅ |
| Policy enforcement | ✅ |
| Remediation coordination | ✅ |
| Failure handling | ✅ |
| Audit trail | ✅ |

---

## Implementation Checklist

- [ ] Create `lambda/guardian/services/multi_account_threat_aggregator.py`
- [ ] Create `lambda/guardian/orchestrators/multi_account_orchestrator.py`
- [ ] Create `lambda/guardian/policies/account_policy_manager.py`
- [ ] Create `lambda/guardian/handlers/multi_account_handler.py`

- [ ] Create `tests/backend/test_multi_account_orchestration.py` (8 tests)
- [ ] Create `tests/integration/test_multi_account_integration.py` (7 tests)

- [ ] Run all 15 tests: `pytest tests/backend/test_multi_account_orchestration.py tests/integration/test_multi_account_integration.py -v`

- [ ] Create git commit:
  ```
  feat: Sprint 53 Phase 1 - Multi-Account Orchestration (15 tests)
  ```

- [ ] Create SPRINT_53_COMPLETION.md documentation

---

## Success Criteria

- ✅ All 15 tests passing
- ✅ Cumulative test count: 866 (851 + 15)
- ✅ Code coverage: >90% for multi-account components
- ✅ Cross-account threat detection working
- ✅ Multi-account remediation coordinated
- ✅ Account policies enforced
- ✅ Unified dashboard functional
- ✅ Git commit with appropriate message
- ✅ SPRINT_53_COMPLETION.md documentation created

---

## Files to Create

| File | Type | Tests |
|------|------|-------|
| `lambda/guardian/services/multi_account_threat_aggregator.py` | NEW | Core service |
| `lambda/guardian/orchestrators/multi_account_orchestrator.py` | NEW | Orchestration |
| `lambda/guardian/policies/account_policy_manager.py` | NEW | Policy management |
| `lambda/guardian/handlers/multi_account_handler.py` | NEW | API handler |
| `tests/backend/test_multi_account_orchestration.py` | NEW | 8 tests |
| `tests/integration/test_multi_account_integration.py` | NEW | 7 tests |
| `docs/SPRINT_53_COMPLETION.md` | NEW | Documentation |

---

## Next Sprint (Sprint 54+)

After Sprint 53 completion:
- Advanced Threat Correlation (ML-based pattern detection)
- Compliance & Audit Features (detailed reporting)
- Custom Response Playbooks (user-defined remediation actions)
