# Sprint 49: Remediation Orchestration

> **Goal**: Coordinate remediation across multiple AWS resources with intelligent ordering and impact assessment

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Sprint Duration | 1 session |
| Test Target | 15 tests (reaching ~803 cumulative) |
| Phases | 1 (Remediation Orchestration) |
| Priority | Multi-resource remediation coordination |

---

## Context

**Completed (Sprint 48):**
- Phase 1: Advanced Threat Correlation (15 tests) ✅
- Phase 2: ML-Based Remediation Prediction (15 tests) ✅
- Phase 3: Multi-Account Orchestration (15 tests) ✅
- **Cumulative**: 788 tests PASS

**Current Sprint**:
- Sprint 49 Phase 1: Remediation Orchestrator (15 tests)
- Implement multi-resource remediation with dependency ordering and impact assessment

---

## Sprint 49 Phase 1: Remediation Orchestration (15 tests)

### Objective
Coordinate remediation across multiple resources (EC2, S3, IAM, Network) with intelligent ordering, impact prediction, and cost estimation.

### Implementation Files

#### 1. RemediationOrchestrator Class
**File**: `lambda/guardian/orchestrators/remediation_orchestrator.py`

```python
class RemediationOrchestrator:
    def __init__(self, audit_logger=None, max_workers: int = 3):
        """Initialize orchestrator with execution tracking."""
        self.audit = audit_logger
        self.max_workers = max_workers
        self.execution_history = []
    
    def execute_multi_resource_remediation(self, threat: Dict, resources: List[Dict]) -> Dict:
        """
        Execute remediation across multiple resources in dependency order.
        
        Execution order: EC2 → Network → S3 → IAM
        
        Returns:
        {
            'threat_id': str,
            'total_resources': int,
            'successful_remediations': int,
            'failed_remediations': int,
            'execution_time_seconds': float,
            'remediation_chain': [
                {
                    'resource_id': str,
                    'resource_type': 'ec2|s3|iam|network',
                    'action': str,
                    'status': 'success|failed',
                    'timestamp': str
                }
            ]
        }
        """
    
    def execute_parallel_remediation(self, threat: Dict, resources: List[Dict]) -> Dict:
        """
        Execute remediation in parallel for independent resources (same type).
        Uses ThreadPoolExecutor with max_workers=3.
        
        Returns same structure as execute_multi_resource_remediation.
        """
    
    def correlate_resources_by_threat(self, threat: Dict, all_resources: List[Dict]) -> List[Dict]:
        """
        Find all resources affected by a specific threat.
        
        Args:
            threat: Threat object with threat_type and account_id
            all_resources: All available resources to search
        
        Returns:
            List of resources affected by this threat
        
        Threat-to-Resource Mapping:
        - 'Unauthorized EC2' → 'ec2'
        - 'Public Bucket' → 's3'
        - 'Unauthorized Access' → 'iam'
        - 'Network Breach' → 'network'
        """
    
    def assess_remediation_impact(self, threat: Dict, resources: List[Dict]) -> Dict:
        """
        Predict impact of remediation before execution.
        
        Returns:
        {
            'estimated_downtime_minutes': float,
            'affected_services': [str],
            'customer_impact': str,
            'recommendations': [str],
            'safe_to_proceed': bool
        }
        
        Service Impact:
        - EC2: 2.0 min downtime, affects 'Compute'
        - S3: No downtime, affects 'Storage'
        - Network: 1.5 min downtime, affects 'Connectivity'
        - IAM: No downtime, affects 'Authorization'
        
        Customer Impact:
        - Severity >= 8: 'Critical - immediate remediation required'
        - Severity >= 6: 'High - remediation recommended'
        - Severity < 6: 'Medium - consider impact before remediation'
        """
    
    def estimate_remediation_cost(self, threat: Dict, resources: List[Dict]) -> Dict:
        """
        Estimate cost of remediation actions.
        
        Returns:
        {
            'estimated_cost_usd': float,
            'cost_breakdown': {'action_name': cost, ...},
            'cost_vs_risk': str
        }
        
        Cost Rules:
        - EC2 stop: $0.00
        - EC2 terminate (severity >= 9): $0.05 per instance
        - S3 block public: $0.00
        - IAM revoke: $0.00
        - Network isolate: $0.00
        """
    
    def get_orchestration_summary(self) -> Dict:
        """
        Get summary of all orchestration executions.
        
        Returns:
        {
            'total_executions': int,
            'total_resources_remediated': int,
            'successful_remediations': int,
            'failed_remediations': int,
            'average_execution_time_seconds': float,
            'success_rate': float (0.0-1.0)
        }
        """
    
    def _remediate_resource(self, threat: Dict, resource: Dict) -> Dict:
        """Execute remediation for a single resource."""
        # Action selection based on resource type and threat severity
        # Status: 'success' unless resource.get('compromised') == True
    
    def _threat_affects_resource(self, threat: Dict, resource: Dict) -> bool:
        """Determine if threat affects a specific resource by type matching."""
```

### Test Files

#### Backend Tests (8 tests)
**File**: `tests/backend/test_remediation_orchestration.py`

```python
class TestRemediationOrchestration:
    def test_execute_multi_resource_remediation(self):
        """✅ Execute remediation across multiple resource types in order."""
        # Threat with EC2, Network, S3 resources
        # Verify execution order: EC2 → Network → S3
        # Assert all remediations succeeded

    def test_execute_parallel_remediation(self):
        """✅ Execute remediation in parallel for independent resources."""
        # Multiple EC2 instances (same type)
        # Verify parallel execution via ThreadPoolExecutor
        # Assert completion time < sequential time

    def test_correlate_resources_by_threat(self):
        """✅ Find all resources affected by a threat."""
        # Threat type: 'Unauthorized EC2'
        # All resources: mix of EC2, S3, IAM, Network
        # Assert only EC2 resources returned

    def test_assess_remediation_impact(self):
        """✅ Predict impact before execution."""
        # 3 resource types (EC2, S3, Network)
        # Assert downtime = 2.0 + 1.5 = 3.5 minutes
        # Assert affected_services = ['Compute', 'Storage', 'Connectivity']

    def test_remediation_impact_customer_impact_levels(self):
        """✅ Customer impact levels by severity."""
        # Test severity 2 → 'Medium'
        # Test severity 6 → 'High'
        # Test severity 9 → 'Critical'

    def test_estimate_remediation_cost(self):
        """✅ Cost estimation by action type."""
        # 3 EC2 instances, 1 terminated (severity 10)
        # Assert cost = $0.05 (1 terminate)
        # Assert cost_vs_risk reflects threat severity

    def test_remediation_orchestration_summary(self):
        """✅ Generate orchestration execution summary."""
        # Execute 2 remediations with 4 and 3 resources
        # Assert success_rate calculated correctly

    def test_remediation_resource_correlation_by_threat_type(self):
        """✅ Resource correlation respects threat-type mapping."""
        # 'Public Bucket' threat + mix of S3/EC2/IAM resources
        # Assert only S3 resources selected
```

#### Integration Tests (7 tests)
**File**: `tests/integration/test_remediation_orchestration_integration.py`

```python
class TestRemediationOrchestrationIntegration:
    def test_end_to_end_multi_resource_threat_remediation(self):
        """✅ Complete flow: threat → correlate resources → execute remediation."""
        # Threat with 5 resources of mixed types
        # Assert all remediated in correct order
        # Assert chain reflects full execution sequence

    def test_remediation_execution_order_dependency(self):
        """✅ Verify execution respects dependency order."""
        # Resources: S3, EC2, Network, IAM (random order)
        # Assert executed as: EC2 → Network → S3 → IAM

    def test_parallel_remediation_independent_resources(self):
        """✅ Parallel execution for same resource type."""
        # 5 EC2 instances
        # Assert parallel execution faster than sequential

    def test_multi_type_resource_remediation_mixed(self):
        """✅ Handle mixed resource types with proper ordering."""
        # 2 EC2 + 3 S3 + 2 IAM resources
        # Assert EC2 first, then S3, then IAM

    def test_impact_assessment_with_multiple_services(self):
        """✅ Impact assessment aggregates across services."""
        # 2 EC2 + 2 Network resources
        # Assert downtime = 2.0 + 1.5 = 3.5 min
        # Assert services = ['Compute', 'Connectivity']

    def test_cost_estimation_multi_resource_scenarios(self):
        """✅ Cost estimation for complex remediation scenarios."""
        # Low severity (cost minimal) vs High severity (terminate cost)
        # Assert high severity has higher cost

    def test_orchestration_summary_aggregation(self):
        """✅ Summary correctly aggregates multiple executions."""
        # Execute 3 times: 3, 4, 5 resources
        # Assert total_resources_remediated = 12
        # Assert average_execution_time = mean of 3 executions
```

### Key Design Decisions

1. **Execution Order**: EC2 → Network → S3 → IAM
   - EC2 instances isolated first
   - Then network access restricted
   - Then storage secured
   - Finally IAM permissions revoked

2. **Resource Correlation**: Thread-safe mapping between threat types and resource types
   - Reduces false positive remediations
   - Each threat only affects matching resource type

3. **Impact Assessment**: Predicts downtime and service impact before execution
   - EC2: 2 min + compute impact
   - Network: 1.5 min + connectivity impact
   - S3: No downtime + storage impact
   - IAM: No downtime + authorization impact

4. **Cost Estimation**: Only EC2 terminate incurs cost ($0.05/instance) for high severity threats
   - Other actions are free or negligible
   - Helps prioritize remediation decisions

5. **Parallel Execution**: ThreadPoolExecutor for same-resource-type remediations
   - max_workers=3 for controlled concurrency
   - Better for fleet-wide operations

---

## Testing Strategy

### Unit Tests (8)
- Class instantiation and method signatures
- Individual method logic (correlation, assessment, cost estimation)
- Summary calculation and aggregation

### Integration Tests (7)
- End-to-end flows
- Execution ordering verification
- Multi-service scenario handling
- Real-world threat-to-remediation pipelines

### Test Coverage

| Component | Coverage |
|-----------|----------|
| Multi-resource execution | ✅ |
| Parallel execution | ✅ |
| Resource correlation | ✅ |
| Impact assessment | ✅ |
| Cost estimation | ✅ |
| Summary aggregation | ✅ |
| Execution ordering | ✅ |
| Mixed resource types | ✅ |

---

## Implementation Checklist

- [ ] Create `lambda/guardian/orchestrators/remediation_orchestrator.py`
  - [ ] `__init__()` with audit logger and max_workers
  - [ ] `execute_multi_resource_remediation()` with ordering
  - [ ] `execute_parallel_remediation()` with ThreadPoolExecutor
  - [ ] `correlate_resources_by_threat()` with type mapping
  - [ ] `assess_remediation_impact()` with service calculation
  - [ ] `estimate_remediation_cost()` with cost rules
  - [ ] `get_orchestration_summary()` with aggregation
  - [ ] `_remediate_resource()` and `_threat_affects_resource()` helpers

- [ ] Create `tests/backend/test_remediation_orchestration.py` (8 tests)
  - [ ] test_execute_multi_resource_remediation
  - [ ] test_execute_parallel_remediation
  - [ ] test_correlate_resources_by_threat
  - [ ] test_assess_remediation_impact
  - [ ] test_remediation_impact_customer_impact_levels
  - [ ] test_estimate_remediation_cost
  - [ ] test_remediation_orchestration_summary
  - [ ] test_remediation_resource_correlation_by_threat_type

- [ ] Create `tests/integration/test_remediation_orchestration_integration.py` (7 tests)
  - [ ] test_end_to_end_multi_resource_threat_remediation
  - [ ] test_remediation_execution_order_dependency
  - [ ] test_parallel_remediation_independent_resources
  - [ ] test_multi_type_resource_remediation_mixed
  - [ ] test_impact_assessment_with_multiple_services
  - [ ] test_cost_estimation_multi_resource_scenarios
  - [ ] test_orchestration_summary_aggregation

- [ ] Run all 15 tests: `pytest tests/backend/test_remediation_orchestration.py tests/integration/test_remediation_orchestration_integration.py -v`

- [ ] Create git commit:
  ```
  feat: Sprint 49 Phase 1 - Remediation Orchestration (15 tests)
  ```

---

## Success Criteria

- ✅ All 15 tests passing
- ✅ Cumulative test count: 803 (788 + 15)
- ✅ Code coverage: >90% for RemediationOrchestrator class
- ✅ Git commit with appropriate message
- ✅ SPRINT_49_COMPLETION.md documentation created

---

## Files to Create/Modify

| File | Type | Tests |
|------|------|-------|
| `lambda/guardian/orchestrators/remediation_orchestrator.py` | NEW | Core implementation |
| `tests/backend/test_remediation_orchestration.py` | NEW | 8 tests |
| `tests/integration/test_remediation_orchestration_integration.py` | NEW | 7 tests |
| `docs/SPRINT_49_COMPLETION.md` | NEW | Documentation |

---

## Next Sprint (Sprint 50+)

After Sprint 49 completion:
- Smart Remediation Engine (threat severity → strategy mapping)
- Real-time response system (event-driven remediation)
- Dashboard integration (orchestration progress tracking)

