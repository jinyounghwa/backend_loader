# Sprint 52: Dashboard Integration

> **Goal**: Real-time threat monitoring and remediation progress visualization

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Sprint Duration | 1 session |
| Test Target | 15 tests (reaching ~852 cumulative) |
| Phases | 1 (Dashboard Integration) |
| Priority | Real-time threat visualization and monitoring |

---

## Context

**Completed (Sprint 51)**:
- Phase 1: Real-time Response System (19 tests) ✅
- Event-driven threat detection and auto-remediation
- Progress tracking and timeline generation
- **Cumulative**: 837 tests PASS

**Current Sprint**:
- Sprint 52 Phase 1: Dashboard Integration (15 tests)
- Build real-time threat dashboard
- Visualize remediation progress
- Track threat status and metrics

---

## Sprint 52 Phase 1: Dashboard Integration (15 tests)

### Objective
Build real-time monitoring dashboard that visualizes threat status, remediation progress, and executive metrics from the automated response system.

### Implementation Files

#### 1. DashboardDataService Class
**File**: `lambda/guardian/services/dashboard_data_service.py`

```python
class DashboardDataService:
    def __init__(self, threat_service, executor, tracker, audit_logger=None):
        """Initialize with dashboard data sources."""
        self.threat_service = threat_service
        self.executor = executor
        self.tracker = tracker
        self.audit = audit_logger
    
    def get_threat_dashboard(self, account_id=None) -> Dict:
        """
        Get current threat dashboard data.
        
        Returns:
        {
            'active_threats': [threat data],
            'threat_summary': {...},
            'severity_distribution': {...},
            'recent_remediations': [execution data],
            'metrics': {...}
        }
        """
    
    def get_remediation_progress(self, threat_id: str) -> Dict:
        """Get real-time remediation progress for specific threat."""
    
    def get_threat_timeline(self, threat_id: str, hours=24) -> List[Dict]:
        """Get threat events in timeline format."""
    
    def get_executive_metrics(self, days=30) -> Dict:
        """
        Get executive-level metrics.
        
        Returns:
        {
            'total_threats_detected': int,
            'threats_resolved': int,
            'auto_remediation_rate': float,
            'average_response_time': float,
            'critical_threats': int
        }
        """
    
    def get_threat_status_by_account(self) -> Dict:
        """Get threat status aggregated by account."""
    
    def get_remediation_status_summary() -> Dict:
        """Get summary of ongoing remediations."""
```

#### 2. DashboardAPI Handler
**File**: `lambda/guardian/handlers/dashboard_handler.py`

```python
def lambda_handler(event, context):
    """
    Dashboard API endpoints.
    
    Routes:
    - GET /dashboard/threats - Current threat status
    - GET /dashboard/threats/{threat_id} - Specific threat details
    - GET /dashboard/remediation/{execution_id} - Remediation progress
    - GET /dashboard/metrics - Executive metrics
    - GET /dashboard/timeline/{threat_id} - Threat timeline
    - GET /dashboard/accounts - Threat status by account
    """
```

#### 3. Web Dashboard Components
**File**: `apps/web/src/components/Dashboard/ThreatDashboard.tsx`

```typescript
// Main dashboard component
export function ThreatDashboard() {
  // Real-time threat status
  // Severity distribution chart
  // Active remediations list
  // Recent events timeline
}
```

**File**: `apps/web/src/components/Dashboard/ThreatCard.tsx`

```typescript
// Individual threat card
export function ThreatCard({ threat }) {
  // Threat ID, severity, type
  // Recommended strategy
  // Current status (detected, remediating, resolved)
}
```

**File**: `apps/web/src/components/Dashboard/RemediationProgress.tsx`

```typescript
// Real-time remediation progress
export function RemediationProgress({ execution_id }) {
  // Progress percentage
  // Resource status list
  // Timeline of events
}
```

**File**: `apps/web/src/components/Dashboard/ExecutiveMetrics.tsx`

```typescript
// High-level metrics
export function ExecutiveMetrics() {
  // Total threats detected
  // Threats resolved
  // Auto-remediation rate
  // Critical threats pending
}
```

#### 4. API Routes
**File**: `apps/web/src/app/api/guardian/dashboard/threats/route.ts`

```typescript
// GET /api/guardian/dashboard/threats
export async function GET(request: Request) {
  // Return current threat dashboard data
}
```

**File**: `apps/web/src/app/api/guardian/dashboard/metrics/route.ts`

```typescript
// GET /api/guardian/dashboard/metrics
export async function GET(request: Request) {
  // Return executive metrics
}
```

### Test Files

#### Backend Tests (8 tests)
**File**: `tests/backend/test_dashboard_service.py`

```python
class TestDashboardDataService:
    def test_get_threat_dashboard(self):
        """✅ Return current threat dashboard data."""
        # Get dashboard with active threats
        # Assert all required fields present

    def test_get_remediation_progress(self):
        """✅ Return real-time remediation progress."""
        # Get progress for specific threat
        # Assert progress percentage and resource status

    def test_get_threat_timeline(self):
        """✅ Return threat events in timeline format."""
        # Get timeline for threat
        # Assert events sorted chronologically

    def test_get_executive_metrics(self):
        """✅ Return executive-level summary metrics."""
        # Get metrics
        # Assert all metrics calculated correctly

    def test_get_threat_status_by_account(self):
        """✅ Return threat status aggregated by account."""
        # Get accounts summary
        # Assert correct grouping and counts

    def test_threat_summary_statistics(self):
        """✅ Calculate threat summary statistics."""
        # Get summary with multiple threats
        # Assert counts and aggregations accurate

    def test_remediation_status_summary(self):
        """✅ Summarize all ongoing remediations."""
        # Get remediation summary
        # Assert correct totals and rates

    def test_dashboard_data_caching(self):
        """✅ Cache dashboard data for performance."""
        # Get dashboard data twice
        # Assert second call uses cache
```

#### Integration Tests (7 tests)
**File**: `tests/integration/test_dashboard_integration.py`

```python
class TestDashboardIntegration:
    def test_end_to_end_threat_to_dashboard(self):
        """✅ Threat detection → dashboard display."""
        # Detect threat
        # Assert visible in dashboard immediately

    def test_remediation_progress_updates(self):
        """✅ Real-time remediation progress updates."""
        # Start remediation
        # Track progress
        # Assert dashboard shows updates

    def test_threat_timeline_generation(self):
        """✅ Generate accurate threat timeline."""
        # Multiple threat events
        # Assert timeline chronologically correct

    def test_executive_metrics_calculation(self):
        """✅ Calculate accurate executive metrics."""
        # Multiple threats and remediations
        # Assert metrics calculation correct

    def test_multi_account_threat_aggregation(self):
        """✅ Aggregate threats across multiple accounts."""
        # Threats in different accounts
        # Assert correct grouping

    def test_dashboard_response_performance(self):
        """✅ Dashboard responds within SLA."""
        # Get dashboard data
        # Assert response time < 500ms

    def test_dashboard_data_freshness(self):
        """✅ Dashboard shows near-real-time data."""
        # Threat event → Dashboard update
        # Assert latency < 5 seconds
```

### Key Design Decisions

1. **Real-time Data Pipeline**
   - Dashboard pulls from ThreatDetectionService and RemediationProgressTracker
   - No database intermediate (direct in-memory state)
   - Cache layer for performance

2. **Severity-Based Visualization**
   - Color coding: Green (low) → Yellow (medium) → Orange (high) → Red (critical)
   - Severity distribution chart for executive summary
   - Filter by severity threshold

3. **Progress Tracking Display**
   - Progress bars for ongoing remediations
   - Resource status list (success/failed/pending)
   - Real-time updates via WebSocket (future enhancement)

4. **Metrics Calculation**
   - Auto-remediation success rate (successful / total)
   - Average response time (detection to remediation)
   - Critical threats pending (severity >= 9)
   - Trends over configurable period (7/30 days)

5. **Account Aggregation**
   - Threat count by account
   - Severity distribution by account
   - Remediation rate by account
   - Cross-account threat correlation

---

## Testing Strategy

### Unit Tests (8)
- Dashboard data service functionality
- Metric calculations
- Timeline generation
- Caching performance

### Integration Tests (7)
- End-to-end threat to dashboard flow
- Real-time progress updates
- Multi-account aggregation
- Performance/SLA validation
- Data freshness verification

### Test Coverage

| Component | Coverage |
|-----------|----------|
| Threat dashboard | ✅ |
| Remediation progress | ✅ |
| Executive metrics | ✅ |
| Timeline generation | ✅ |
| Multi-account support | ✅ |
| Performance/caching | ✅ |
| Data freshness | ✅ |

---

## Implementation Checklist

- [ ] Create `lambda/guardian/services/dashboard_data_service.py`
  - [ ] `get_threat_dashboard()`
  - [ ] `get_remediation_progress()`
  - [ ] `get_threat_timeline()`
  - [ ] `get_executive_metrics()`
  - [ ] `get_threat_status_by_account()`
  - [ ] `get_remediation_status_summary()`

- [ ] Create `lambda/guardian/handlers/dashboard_handler.py`
  - [ ] GET /dashboard/threats endpoint
  - [ ] GET /dashboard/threats/{threat_id} endpoint
  - [ ] GET /dashboard/remediation/{execution_id} endpoint
  - [ ] GET /dashboard/metrics endpoint
  - [ ] GET /dashboard/timeline/{threat_id} endpoint

- [ ] Create `apps/web/src/components/Dashboard/ThreatDashboard.tsx`
- [ ] Create `apps/web/src/components/Dashboard/ThreatCard.tsx`
- [ ] Create `apps/web/src/components/Dashboard/RemediationProgress.tsx`
- [ ] Create `apps/web/src/components/Dashboard/ExecutiveMetrics.tsx`

- [ ] Create API routes
  - [ ] `apps/web/src/app/api/guardian/dashboard/threats/route.ts`
  - [ ] `apps/web/src/app/api/guardian/dashboard/metrics/route.ts`

- [ ] Create `tests/backend/test_dashboard_service.py` (8 tests)
- [ ] Create `tests/integration/test_dashboard_integration.py` (7 tests)

- [ ] Run all 15 tests: `pytest tests/backend/test_dashboard_service.py tests/integration/test_dashboard_integration.py -v`

- [ ] Create git commit:
  ```
  feat: Sprint 52 Phase 1 - Dashboard Integration (15 tests)
  ```

- [ ] Create SPRINT_52_COMPLETION.md documentation

---

## Success Criteria

- ✅ All 15 tests passing
- ✅ Cumulative test count: 852 (837 + 15)
- ✅ Code coverage: >90% for dashboard components
- ✅ Dashboard displays real-time threat status
- ✅ Remediation progress visible in real-time
- ✅ Executive metrics calculated correctly
- ✅ Multi-account support functional
- ✅ Response time < 500ms
- ✅ Git commit with appropriate message
- ✅ SPRINT_52_COMPLETION.md documentation created

---

## Files to Create/Modify

| File | Type | Tests |
|------|------|-------|
| `lambda/guardian/services/dashboard_data_service.py` | NEW | Core service |
| `lambda/guardian/handlers/dashboard_handler.py` | NEW | API handler |
| `apps/web/src/components/Dashboard/ThreatDashboard.tsx` | NEW | Main dashboard |
| `apps/web/src/components/Dashboard/ThreatCard.tsx` | NEW | Threat card |
| `apps/web/src/components/Dashboard/RemediationProgress.tsx` | NEW | Progress display |
| `apps/web/src/components/Dashboard/ExecutiveMetrics.tsx` | NEW | Metrics display |
| `apps/web/src/app/api/guardian/dashboard/threats/route.ts` | NEW | Threats API |
| `apps/web/src/app/api/guardian/dashboard/metrics/route.ts` | NEW | Metrics API |
| `tests/backend/test_dashboard_service.py` | NEW | 8 tests |
| `tests/integration/test_dashboard_integration.py` | NEW | 7 tests |
| `docs/SPRINT_52_COMPLETION.md` | NEW | Documentation |

---

## Next Sprint (Sprint 53+)

After Sprint 52 completion:
- Multi-Account Orchestration (cross-account threat response)
- Advanced Threat Correlation (ML-based pattern detection)
- Compliance & Audit Features (detailed logging and reporting)
