# Sprint 57: Real-time Threat Dashboard with WebSocket Streaming

> **Goal**: Live event streaming and real-time threat visualization with WebSocket support and instant threat updates

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Sprint Duration | 1 session |
| Test Target | 14 tests (reaching ~926 cumulative) |
| Phases | 1 (Real-time Dashboard with WebSocket) |
| Priority | Live event streaming, real-time updates, instant threat visibility |

---

## Context

**Completed (Sprints 49-55)**:
- Sprint 49: RemediationOrchestrator (15 tests) ✅
- Sprint 50: SmartRemediationEngine (15 tests) ✅
- Sprint 51: Real-time Response System (19 tests) ✅
- Sprint 52: Dashboard Integration (14 tests) ✅
- Sprint 53: Multi-Account Orchestration (15 tests) ✅
- Sprint 54: Advanced Threat Correlation (15 tests) ✅
- Sprint 55: Compliance & Audit Features (16 tests) ✅ (Planned)
- **Cumulative**: 897 tests PASS (projected)

**Current Sprint (Next)**:
- Sprint 56: Custom Response Playbooks (15 tests planned)
  - Target: 912 tests cumulative

**Future Sprint (This)**:
- Sprint 57 Phase 1: Real-time Threat Dashboard (14 tests)
  - Build WebSocket event streaming
  - Implement real-time threat updates
  - Create live remediation progress tracking
  - Enable instant dashboard synchronization

---

## Sprint 57 Phase 1: Real-time Threat Dashboard (14 tests)

### Objective
Upgrade threat dashboard from polling-based updates to WebSocket-driven real-time streaming, enabling instant threat visibility, live remediation progress tracking, and collaborative security team operations with synchronized dashboards.

### Implementation Files

#### 1. WebSocketEventBroadcaster Class
**File**: `lambda/guardian/websocket/event_broadcaster.py`

```python
class WebSocketEventBroadcaster:
    def __init__(self, connection_manager=None):
        """Initialize WebSocket broadcaster."""
        self.connections = {}
        self.manager = connection_manager
    
    def broadcast_threat_detected(self, threat):
        """
        Broadcast new threat detection to all connected clients.
        
        Message format:
        {
            'event_type': 'threat_detected',
            'timestamp': ISO-8601,
            'threat_id': str,
            'threat_type': str,
            'severity': int,
            'account_id': str,
            'affected_resources': [...]
        }
        """
    
    def broadcast_remediation_started(self, execution_id, threat_id):
        """Broadcast remediation execution start."""
    
    def broadcast_remediation_progress(self, execution_id, progress_percent, resources_status):
        """Broadcast real-time remediation progress (every resource update)."""
    
    def broadcast_remediation_completed(self, execution_id, status, summary):
        """Broadcast remediation completion."""
    
    def broadcast_compliance_status_change(self, framework, new_status):
        """Broadcast compliance metric update."""
    
    def broadcast_playbook_execution(self, execution_id, playbook_name, status):
        """Broadcast playbook execution events."""
    
    def register_client_connection(self, connection_id, filters=None):
        """Register WebSocket client with optional event filters."""
    
    def unregister_client_connection(self, connection_id):
        """Unregister WebSocket client."""
    
    def send_to_client(self, connection_id, message):
        """Send message to specific client."""
    
    def broadcast_to_all(self, message, filter_fn=None):
        """Broadcast to all connected clients with optional filtering."""
    
    def broadcast_to_account(self, account_id, message):
        """Broadcast to clients filtered by account."""
```

#### 2. RealtimeDashboardService Class
**File**: `lambda/guardian/services/realtime_dashboard_service.py`

```python
class RealtimeDashboardService:
    def __init__(self, threat_service=None, dashboard_service=None, broadcaster=None):
        """Initialize real-time dashboard service."""
        self.threats = threat_service
        self.dashboard = dashboard_service
        self.broadcaster = broadcaster
    
    def get_initial_dashboard_state(self, account_id=None):
        """
        Get full dashboard state for new WebSocket connection.
        Includes all active threats, remediation progress, metrics.
        """
    
    def stream_threat_updates(self, threat_id):
        """Get threat detail stream for specific threat."""
    
    def stream_remediation_progress(self, execution_id):
        """Stream real-time remediation progress."""
    
    def stream_account_threats(self, account_id):
        """Stream all threats for account (filtered stream)."""
    
    def get_dashboard_diff(self, last_state, current_state):
        """
        Calculate incremental diff for efficient updates.
        Only sends changed fields (reduce bandwidth).
        """
    
    def apply_client_filters(self, event, client_filters):
        """Apply client-specified filters to events."""
    
    def get_playback_history(self, threat_id, duration_minutes=60):
        """Get historical events for playback (replay last N minutes)."""
```

#### 3. DashboardConnectionManager Class
**File**: `lambda/guardian/websocket/connection_manager.py`

```python
class DashboardConnectionManager:
    def __init__(self):
        """Initialize connection manager."""
        self.connections = {}
        self.subscriptions = {}
    
    def register_connection(self, connection_id, user_id, account_id=None):
        """Register new WebSocket connection."""
    
    def unregister_connection(self, connection_id):
        """Unregister closed WebSocket connection."""
    
    def subscribe_to_threat(self, connection_id, threat_id):
        """Subscribe client to specific threat updates."""
    
    def subscribe_to_account(self, connection_id, account_id):
        """Subscribe client to account-wide threat updates."""
    
    def unsubscribe_from_threat(self, connection_id, threat_id):
        """Unsubscribe from threat."""
    
    def get_subscriptions(self, connection_id):
        """Get all subscriptions for connection."""
    
    def get_subscribers(self, threat_id):
        """Get all clients subscribed to threat."""
    
    def update_connection_activity(self, connection_id):
        """Update last activity timestamp for connection."""
    
    def get_stale_connections(self, timeout_minutes=30):
        """Get connections with no activity (for cleanup)."""
    
    def cleanup_stale_connections(self, timeout_minutes=30):
        """Remove idle connections."""
```

#### 4. DashboardStreamManager Class
**File**: `lambda/guardian/websocket/stream_manager.py`

```python
class DashboardStreamManager:
    def __init__(self, broadcaster=None, dashboard_service=None):
        """Initialize stream manager."""
        self.broadcaster = broadcaster
        self.dashboard = dashboard_service
    
    def handle_threat_detection(self, threat):
        """Handle threat detection event and broadcast."""
    
    def handle_remediation_update(self, execution_id, update):
        """Handle remediation progress update and broadcast."""
    
    def handle_resource_update(self, resource_id, status, action):
        """Handle individual resource update and broadcast."""
    
    def handle_playbook_event(self, event):
        """Handle playbook execution event and broadcast."""
    
    def handle_compliance_update(self, framework, metrics):
        """Handle compliance metric update and broadcast."""
    
    def handle_audit_event(self, event):
        """Handle audit trail event and broadcast."""
    
    def batch_updates(self, events, batch_size=10, batch_timeout_ms=100):
        """
        Batch multiple events into single message.
        Reduces number of messages while maintaining responsiveness.
        """
```

#### 5. WebSocket API Handler
**File**: `lambda/guardian/handlers/websocket_handler.py`

```python
def connect_handler(event, context):
    """
    WebSocket $connect endpoint.
    Initialize connection, send initial state, register subscriptions.
    """

def disconnect_handler(event, context):
    """
    WebSocket $disconnect endpoint.
    Cleanup connection, unsubscribe from all streams.
    """

def default_handler(event, context):
    """
    WebSocket $default route for client messages.
    
    Client message format:
    {
        'action': 'subscribe_threat' | 'subscribe_account' | 'unsubscribe' | 'apply_filter',
        'threat_id': str (optional),
        'account_id': str (optional),
        'filters': {...} (optional)
    }
    """

def message_handler(connection_id, action, payload):
    """Route client messages to appropriate handlers."""
```

#### 6. Frontend Dashboard WebSocket Hook
**File**: `apps/web/src/lib/hooks/useRealtimeDashboard.ts`

```typescript
export function useRealtimeDashboard(accountId?: string) {
    // WebSocket connection management
    // Auto-reconnect on disconnect
    // Incremental state updates
    // Subscription management
    // Event stream filtering
    
    return {
        threats: Threat[],
        remediations: RemediationExecution[],
        metrics: DashboardMetrics,
        isConnected: boolean,
        subscribe: (threatId: string) => void,
        unsubscribe: (threatId: string) => void,
        applyFilter: (filter: DashboardFilter) => void,
    }
}
```

### Test Files

#### Backend Tests (8 tests)
**File**: `tests/backend/test_realtime_dashboard.py`

```python
class TestWebSocketEventBroadcaster:
    def test_broadcast_threat_detected(self):
        """✅ Broadcast new threat detection."""
    
    def test_broadcast_remediation_progress(self):
        """✅ Broadcast real-time remediation progress."""
    
    def test_register_client_connection(self):
        """✅ Register WebSocket client."""

class TestRealtimeDashboardService:
    def test_get_initial_dashboard_state(self):
        """✅ Get full state for new connection."""
    
    def test_stream_threat_updates(self):
        """✅ Stream specific threat updates."""
    
    def test_get_dashboard_diff(self):
        """✅ Calculate incremental diff for efficiency."""

class TestConnectionManager:
    def test_register_and_unregister_connection(self):
        """✅ Manage connection lifecycle."""
    
    def test_subscription_management(self):
        """✅ Subscribe/unsubscribe from threats."""
```

#### Integration Tests (6 tests)
**File**: `tests/integration/test_realtime_dashboard_integration.py`

```python
class TestRealtimeDashboardIntegration:
    def test_end_to_end_threat_broadcast(self):
        """✅ Threat detection → broadcast → client receives."""
    
    def test_remediation_progress_streaming(self):
        """✅ Real-time remediation progress updates."""
    
    def test_multi_client_same_threat_subscription(self):
        """✅ Multiple clients receive same threat updates."""
    
    def test_account_filtered_subscription(self):
        """✅ Clients only receive account-relevant threats."""
    
    def test_connection_recovery_and_replay(self):
        """✅ Reconnected client receives recent history."""
    
    def test_dashboard_performance_under_load(self):
        """✅ Broadcast 100 concurrent clients, <100ms latency."""
```

### Key Design Decisions

1. **WebSocket Event Broadcasting**
   - All dashboard updates sent via WebSocket
   - Message batching to reduce overhead
   - Incremental diffs for bandwidth efficiency
   - Fallback to polling if WebSocket unavailable

2. **Client-Side Filtering**
   - Clients subscribe to specific threats/accounts
   - Server only sends relevant events to subscribed clients
   - Reduces bandwidth and CPU overhead
   - Flexible filtering based on client preferences

3. **Connection Management**
   - Auto-cleanup of idle connections (30+ minutes)
   - Graceful disconnect/reconnect handling
   - Heartbeat mechanism to detect stale connections
   - Connection state persistence

4. **Incremental Updates**
   - Send only changed fields (diff calculation)
   - Reduce message size and bandwidth
   - Faster client-side rendering
   - Maintain full state for recovery

5. **Ordered Event Delivery**
   - Events delivered in chronological order
   - Threat → Remediation → Progress → Complete
   - Prevent state inconsistencies from out-of-order updates
   - Replay capability for recovery

---

## Testing Strategy

### Unit Tests (8)
- WebSocket broadcast functionality
- Connection registration/unregistration
- Subscription management
- Dashboard state calculation
- Diff generation for incremental updates

### Integration Tests (6)
- End-to-end threat broadcasting
- Remediation progress streaming
- Multi-client synchronization
- Account filtering
- Connection recovery and playback
- Performance under load (100 concurrent clients)

### Test Coverage

| Component | Coverage |
|-----------|----------|
| WebSocket broadcasting | ✅ |
| Connection management | ✅ |
| Subscription system | ✅ |
| Real-time updates | ✅ |
| Client filtering | ✅ |
| Incremental diffs | ✅ |
| Performance | ✅ |

---

## Implementation Checklist

- [ ] Create `lambda/guardian/websocket/event_broadcaster.py`
- [ ] Create `lambda/guardian/services/realtime_dashboard_service.py`
- [ ] Create `lambda/guardian/websocket/connection_manager.py`
- [ ] Create `lambda/guardian/websocket/stream_manager.py`
- [ ] Create `lambda/guardian/handlers/websocket_handler.py`
- [ ] Create `apps/web/src/lib/hooks/useRealtimeDashboard.ts`

- [ ] Create `tests/backend/test_realtime_dashboard.py` (8 tests)
- [ ] Create `tests/integration/test_realtime_dashboard_integration.py` (6 tests)

- [ ] Run all 14 tests: `pytest tests/backend/test_realtime_dashboard.py tests/integration/test_realtime_dashboard_integration.py -v`

- [ ] Create git commit:
  ```
  feat: Sprint 57 Phase 1 - Real-time Threat Dashboard (14 tests)
  ```

- [ ] Create SPRINT_57_COMPLETION.md documentation

---

## Success Criteria

- ✅ All 14 tests passing
- ✅ Cumulative test count: 926 (912 + 14)
- ✅ Code coverage: >90% for WebSocket components
- ✅ WebSocket event broadcasting functional
- ✅ Connection management and lifecycle working
- ✅ Subscription filtering operational
- ✅ Real-time updates <100ms latency
- ✅ Connection recovery and playback
- ✅ Performance tested with 100 concurrent clients
- ✅ Git commit with appropriate message
- ✅ SPRINT_57_COMPLETION.md documentation created

---

## Files to Create

| File | Type | Tests |
|------|------|-------|
| `lambda/guardian/websocket/event_broadcaster.py` | NEW | Event broadcasting |
| `lambda/guardian/services/realtime_dashboard_service.py` | NEW | Real-time service |
| `lambda/guardian/websocket/connection_manager.py` | NEW | Connection mgmt |
| `lambda/guardian/websocket/stream_manager.py` | NEW | Stream management |
| `lambda/guardian/handlers/websocket_handler.py` | NEW | WebSocket handler |
| `apps/web/src/lib/hooks/useRealtimeDashboard.ts` | NEW | React hook |
| `tests/backend/test_realtime_dashboard.py` | NEW | 8 tests |
| `tests/integration/test_realtime_dashboard_integration.py` | NEW | 6 tests |
| `docs/SPRINT_57_COMPLETION.md` | NEW | Documentation |

---

## Next Sprint (Sprint 58+)

After Sprint 57 completion:
- Machine Learning threat correlation (predictive threat analysis, attack pattern learning)
- Advanced anomaly detection (statistical models, behavioral baselines)
- Threat intelligence integration (external feeds, enrichment)

---

## Architecture Flow

```
Threat Detection Event
    ↓
StreamManager.handle_threat_detection()
    ├─ Create threat event message
    ├─ Get all subscribed clients
    └─ EventBroadcaster.broadcast_threat_detected()
        ├─ Send to client 1 (WebSocket)
        ├─ Send to client 2 (WebSocket)
        └─ Send to client 3 (WebSocket)

RemediationOrchestrator Progress Update
    ↓
StreamManager.handle_remediation_update()
    ├─ Calculate diff from last state
    ├─ Format incremental update
    └─ EventBroadcaster.broadcast_remediation_progress()
        ├─ Send to clients subscribed to threat
        └─ Update progress % and resource status

Client WebSocket Connect
    ↓
websocket_handler.connect_handler()
    ├─ ConnectionManager.register_connection()
    ├─ RealtimeDashboardService.get_initial_dashboard_state()
    └─ Send full state to client

Client Subscribe to Threat
    ↓
websocket_handler.default_handler()
    ├─ ConnectionManager.subscribe_to_threat()
    └─ Send threat details and recent history

Real-time Dashboard (Frontend)
    ├─ useRealtimeDashboard() hook
    ├─ Connect to WebSocket
    ├─ Receive threat_detected events
    ├─ Update UI in real-time
    ├─ Subscribe to specific threats
    └─ Auto-reconnect on disconnect
```

---

## Message Flow Examples

### Threat Detection Message
```json
{
    "event_type": "threat_detected",
    "timestamp": "2026-05-26T14:30:00Z",
    "threat_id": "threat-xyz123",
    "threat_type": "Unauthorized EC2",
    "severity": 8,
    "account_id": "acc-123",
    "affected_resources": [
        {"resource_id": "i-001", "resource_type": "ec2"}
    ],
    "remediation_recommended": "REMEDIATE"
}
```

### Remediation Progress Message
```json
{
    "event_type": "remediation_progress",
    "timestamp": "2026-05-26T14:30:15Z",
    "execution_id": "exec-abc789",
    "threat_id": "threat-xyz123",
    "progress_percent": 45,
    "resources_status": {
        "total": 3,
        "completed": 2,
        "failed": 0,
        "pending": 1
    },
    "current_action": "Isolating network access"
}
```

### Playbook Execution Message
```json
{
    "event_type": "playbook_execution",
    "timestamp": "2026-05-26T14:30:30Z",
    "execution_id": "exec-abc789",
    "playbook_name": "EC2 Isolation Playbook",
    "status": "in_progress",
    "actions_completed": 2,
    "actions_total": 5,
    "current_action": "Revoking IAM roles"
}
```

---

## Performance Characteristics

- **Message Latency**: <100ms from event to client WebSocket
- **Connection Bandwidth**: ~5KB/min idle, ~50KB/min with threats
- **Connection Memory**: ~10KB per connection
- **Broadcast Throughput**: 100+ events/sec for 100 concurrent clients
- **Message Size**: 1-5KB per event (incremental diffs smaller)

---

## Compliance & Auditing

### Logged Information
- WebSocket connection/disconnection
- Subscription requests
- Unsubscription requests
- Filter changes
- Connection errors

### Audit Trail
All WebSocket events logged with:
- Client ID and user ID
- Connection timestamp
- Subscription details
- Message timestamps

---

## Context & Motivation

**Why Real-time WebSocket Dashboard?**

Current polling-based dashboard (Sprint 52):
- Updates every 5-30 seconds (configurable cache TTL)
- Latency: Users see threat 5-30 seconds after detection
- Bandwidth: Continuous polling even when idle
- Synchronization: Multiple users see different states

Real-time WebSocket provides:
- **Instant Visibility**: Users see threats immediately (<100ms)
- **Efficient Bandwidth**: Events only sent when something changes
- **Synchronized State**: All users see same state at same time
- **Live Collaboration**: Teams work with consistent view of threats

**Integration with Existing Systems:**
- ThreatDetectionService → StreamManager → EventBroadcaster
- RemediationOrchestrator → StreamManager → EventBroadcaster
- PlaybookExecutionEngine → StreamManager → EventBroadcaster
- DashboardDataService provides initial state and incremental updates

**Expected Benefits:**
- Reduce MTTR by instant threat awareness
- Improve team collaboration with synchronized views
- Reduce bandwidth with event-driven updates
- Better user experience with live dashboard
- Enable real-time threat correlation visualization

---

## Summary

Sprint 57 delivers real-time WebSocket-driven threat dashboard that enables:

- **Instant Threat Visibility**: See threats as they're detected (<100ms)
- **Live Remediation Tracking**: Watch remediation progress in real-time
- **Synchronized Teams**: All users see same state simultaneously
- **Efficient Updates**: Only send changed data (incremental diffs)
- **Flexible Subscriptions**: Subscribe to specific threats or accounts
- **Collaborative Security**: Enable team collaboration on live threats

This transforms AWS Guardian from a monitoring tool into a real-time collaborative security platform.

**Target**: 926 cumulative tests (912 + 14)
