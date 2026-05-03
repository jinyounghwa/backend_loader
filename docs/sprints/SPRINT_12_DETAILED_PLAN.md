# Sprint 12: Frontend Advanced Features & Real-Time Updates

**Status:** PLANNED (Ready for implementation)
**Target Components:** Dashboard enhancements, WebSocket integration, Toast notifications
**Estimated Duration:** 2-3 sessions
**Dependencies:** Sprint 11 Phase 1 + Phase 2 complete, Socket.io setup

---

## Overview

Sprint 12 builds on Sprint 11's foundation by adding:
1. **Real-time updates** via WebSocket (replace 30-second polling)
2. **Toast notifications** for action success/failure
3. **Advanced filtering** (by action type, status, date range)
4. **Audit log integration** with DynamoDB
5. **Performance optimizations** (debouncing, memo optimization)

---

## Phase 1: Real-Time Updates with WebSocket

### Why WebSocket?
- Current polling: 30s intervals = 2,880 API calls/day per user
- WebSocket: Instant updates, 1 persistent connection
- Better UX: Actions complete in real-time instead of 30s delay
- Cost: Fewer Lambda invocations for dashboard queries

### Implementation Plan

#### 1.1 Socket.IO Server Setup
**File:** `apps/web/src/lib/socket.ts`

```typescript
import { Server as SocketServer } from 'socket.io';
import { NextApiRequest, NextApiResponse } from 'next';

export const socketHandler = (req: NextApiRequest, res: NextApiResponse) => {
  if (res.socket.server.io) {
    console.log('Socket.IO already running');
    res.end();
    return;
  }

  const io = new SocketServer(res.socket.server, {
    cors: { origin: process.env.NEXT_PUBLIC_APP_URL },
  });

  io.on('connection', (socket) => {
    console.log(`Client connected: ${socket.id}`);
    
    socket.on('subscribe-account', (accountId: string) => {
      socket.join(`account:${accountId}`);
    });

    socket.on('disconnect', () => {
      console.log(`Client disconnected: ${socket.id}`);
    });
  });

  res.socket.server.io = io;
  res.end();
};
```

**File:** `apps/web/src/app/api/socket/route.ts`
- Exports socketHandler as GET/POST
- Initializes Socket.IO on first request

#### 1.2 Socket.IO Client Hook
**File:** `apps/web/src/lib/hooks/useSocket.ts`

```typescript
import { useEffect, useRef, useCallback } from 'react';
import io, { Socket } from 'socket.io-client';

export const useSocket = () => {
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    socketRef.current = io(process.env.NEXT_PUBLIC_APP_URL, {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5,
    });

    return () => {
      socketRef.current?.disconnect();
    };
  }, []);

  const subscribe = useCallback((event: string, handler: (...args: any[]) => void) => {
    if (socketRef.current) {
      socketRef.current.on(event, handler);
    }
  }, []);

  const emit = useCallback((event: string, data: any) => {
    if (socketRef.current) {
      socketRef.current.emit(event, data);
    }
  }, []);

  return { subscribe, emit };
};
```

#### 1.3 Real-Time Event Updates
**File:** `apps/web/src/components/Dashboard/EventFeed.tsx` (Modified)

Replace polling with WebSocket subscription:

```typescript
useEffect(() => {
  const handleNewEvent = (event: GuardianEvent) => {
    setEvents(prev => [event, ...prev.slice(0, 4)]);
  };

  subscribe('event:new', handleNewEvent);
  emit('subscribe-account', selectedAccountId);

  return () => {
    // Unsubscribe handled by socket cleanup
  };
}, [selectedAccountId, subscribe, emit]);
```

**Changes:**
- Remove 30-second setInterval
- Subscribe to `event:new` socket event
- Auto-prepend new events to list
- Maintain 5-item limit

#### 1.4 Real-Time Action Updates
**File:** `apps/web/src/components/Dashboard/ActionHistory.tsx` (Modified)

Subscribe to action completion events:

```typescript
useEffect(() => {
  const handleActionComplete = (action: Action) => {
    setActions(prev => {
      const idx = prev.findIndex(a => a.action_id === action.action_id);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = action;
        return updated;
      }
      return [action, ...prev.slice(0, -1)];
    });
  };

  subscribe('action:complete', handleActionComplete);
  emit('subscribe-account', selectedAccountId);
}, [selectedAccountId, subscribe, emit]);
```

**Changes:**
- Remove manual `loadActions()` polling
- Update action status in real-time
- Show new actions immediately

### Verification Checklist - Phase 1

- [ ] Socket.IO server initializes on app startup
- [ ] Client connects and receives connection ID in console
- [ ] Subscribe-account event works without errors
- [ ] EventFeed updates without page refresh on new event
- [ ] ActionHistory updates when action completes
- [ ] Multiple accounts receive isolated updates (room-based)
- [ ] Reconnection works after network disconnect

---

## Phase 2: Toast Notifications

### 2.1 Toast Component
**File:** `apps/web/src/components/Toast/Toast.tsx`

```typescript
interface ToastProps {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
  duration?: number;
  onDismiss: (id: string) => void;
}

export default function Toast({ id, type, message, duration = 4000, onDismiss }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), duration);
    return () => clearTimeout(timer);
  }, [duration, id, onDismiss]);

  const bgColor = {
    success: 'bg-green-900/50 border-green-700 text-green-400',
    error: 'bg-red-900/50 border-red-700 text-red-400',
    info: 'bg-blue-900/50 border-blue-700 text-blue-400',
    warning: 'bg-amber-900/50 border-amber-700 text-amber-400',
  };

  return (
    <div className={`p-4 rounded border ${bgColor[type]} flex items-center justify-between`}>
      <span className="text-sm">{message}</span>
      <button onClick={() => onDismiss(id)} className="ml-2 text-lg">✕</button>
    </div>
  );
}
```

### 2.2 Toast Container & Context
**File:** `apps/web/src/lib/hooks/useToast.ts`

```typescript
import { useCallback, useContext } from 'react';
import { ToastContext } from '@/components/Providers'; // Add to Providers

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');

  return {
    success: (msg: string) => context.add('success', msg),
    error: (msg: string) => context.add('error', msg),
    info: (msg: string) => context.add('info', msg),
    warning: (msg: string) => context.add('warning', msg),
  };
};
```

### 2.3 Integration in ActionHistory
**File:** `apps/web/src/components/Dashboard/ActionHistory.tsx` (Modified)

```typescript
const toast = useToast();

const handleExecuteAction = async () => {
  // ... existing code ...
  try {
    const res = await fetch(endpoint, { /* ... */ });
    if (res.ok) {
      toast.success(`Action executed: ${dialogConfig.confirmText}`);
      await loadActions();
    }
  } catch (err) {
    toast.error('Failed to execute action');
  }
};
```

### Verification Checklist - Phase 2

- [ ] Toast component renders with correct styling
- [ ] Auto-dismiss after 4 seconds
- [ ] Manual dismiss button works
- [ ] Success toast shows on action completion
- [ ] Error toast shows on failure
- [ ] Multiple toasts stack vertically
- [ ] Toasts appear top-right of viewport

---

## Phase 3: Advanced Filtering

### 3.1 Filter Component
**File:** `apps/web/src/components/Dashboard/ActionHistoryFilter.tsx`

```typescript
interface FilterState {
  actionType: string | null;
  status: string | null;
  dateRange: { start: Date | null; end: Date | null };
}

export default function ActionHistoryFilter({ onFilter }: { onFilter: (filters: FilterState) => void }) {
  const [filters, setFilters] = useState<FilterState>({
    actionType: null,
    status: null,
    dateRange: { start: null, end: null },
  });

  const handleApply = () => onFilter(filters);

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 space-y-3">
      {/* Dropdown for action type */}
      {/* Dropdown for status */}
      {/* Date range picker */}
      <button onClick={handleApply}>Apply Filters</button>
    </div>
  );
}
```

### 3.2 Enhanced API with Filtering
**File:** `apps/web/src/app/api/actions/route.ts` (Modified)

```typescript
const actionType = searchParams.get('action_type');
const status = searchParams.get('status');
const startDate = searchParams.get('start_date');
const endDate = searchParams.get('end_date');

let filtered = actions;

if (actionType) filtered = filtered.filter(a => a.action_type === actionType);
if (status) filtered = filtered.filter(a => a.status === status);

// Date range filtering logic
```

### 3.3 Filter State in ActionHistory
**File:** `apps/web/src/components/Dashboard/ActionHistory.tsx` (Modified)

```typescript
const [filters, setFilters] = useState<FilterState>({ /* ... */ });

const loadActions = async () => {
  const params = new URLSearchParams({
    account_id: selectedAccountId,
    limit: '10',
    ...(filters.actionType && { action_type: filters.actionType }),
    ...(filters.status && { status: filters.status }),
  });
  
  const res = await fetch(`/api/actions?${params}`);
  // ...
};
```

### Verification Checklist - Phase 3

- [ ] Filter component renders all filter options
- [ ] Selecting action_type filters results
- [ ] Selecting status filters results
- [ ] Date range picker works (start/end)
- [ ] Combined filters work correctly
- [ ] Clear filters button resets all
- [ ] Filter state persists during navigation

---

## Phase 4: Audit Log Integration

### 4.1 DynamoDB Schema Enhancement
**File:** `lambda/guardian/storage/audit_logs.py` (Existing - enhance)

```python
async def save_audit_log(
  user: str,
  action: str,
  resource_id: str,
  account_id: str,
  status: str = 'success',
  details: dict = None
):
  """Save action to DynamoDB audit logs table"""
  table = dynamodb.Table('guardian-audit-logs')
  
  item = {
    'action_id': f"act-{uuid.uuid4()}",
    'timestamp': datetime.utcnow().isoformat(),
    'user': user,
    'action': action,
    'resource_id': resource_id,
    'account_id': account_id,
    'status': status,
    'details': details or {},
    'ttl': int(time.time()) + (90 * 86400),  # 90-day retention
  }
  
  table.put_item(Item=item)
  return item['action_id']
```

### 4.2 API Endpoint for Audit Logs
**File:** `apps/web/src/app/api/audit-logs/route.ts`

```typescript
export async function GET(request: NextRequest) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const searchParams = request.nextUrl.searchParams;
  const accountId = searchParams.get('account_id');
  const limit = Math.min(parseInt(searchParams.get('limit') || '50'), 100);

  try {
    // Query DynamoDB for audit logs
    const logs = await queryAuditLogs(accountId, limit);
    return NextResponse.json({ logs });
  } catch (error) {
    console.error('Failed to fetch audit logs:', error);
    return NextResponse.json({ error: 'Failed to fetch audit logs' }, { status: 500 });
  }
}
```

### 4.3 Audit Log Viewer Component
**File:** `apps/web/src/components/Dashboard/AuditLogViewer.tsx`

```typescript
export default function AuditLogViewer() {
  const { selectedAccountId } = useAccounts();
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const fetchLogs = async () => {
      const res = await fetch(`/api/audit-logs?account_id=${selectedAccountId}&limit=20`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs);
      }
    };

    fetchLogs();
  }, [selectedAccountId]);

  return (
    <div className="bg-[#1a1d27] border border-slate-800 rounded-lg p-5">
      <h2 className="text-lg font-semibold text-slate-100 mb-4">Audit Logs</h2>
      {/* Render audit logs in table format */}
    </div>
  );
}
```

### 4.4 Lambda Integration
**File:** `lambda/guardian/handler.py` (Existing - enhance)

When executing actions, save to audit log:

```python
from guardian.storage.audit_logs import save_audit_log

async def handle_remediate_action(account_id, action_type, resource_id, user):
  # Execute action...
  action_id = await save_audit_log(
    user=user,
    action=action_type,
    resource_id=resource_id,
    account_id=account_id,
    status='success'
  )
  return action_id
```

### Verification Checklist - Phase 4

- [ ] DynamoDB audit_logs table has TTL enabled
- [ ] Lambda writes to audit logs on every action
- [ ] API endpoint returns audit logs by account
- [ ] Audit logs include user, timestamp, action type
- [ ] Can filter audit logs by date range
- [ ] Export audit logs to CSV functionality

---

## Phase 5: Performance Optimizations

### 5.1 Debouncing for Filter Changes
**File:** `apps/web/src/lib/hooks/useDebounce.ts`

```typescript
export const useDebounce = (value: any, delay: number = 500) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
};
```

### 5.2 Memoization of Components
**File:** `apps/web/src/components/Dashboard/EventFeed.tsx` (Modified)

```typescript
const EventFeed = memo(function EventFeed() {
  // ... component code ...
}, (prevProps, nextProps) => {
  return prevProps.selectedAccountId === nextProps.selectedAccountId;
});

export default EventFeed;
```

### 5.3 Image & Asset Optimization
- Lazy load components using dynamic import
- Optimize SVG icons
- Enable image optimization in Next.js config

### Verification Checklist - Phase 5

- [ ] Lighthouse performance score > 80
- [ ] Filter changes debounced (500ms)
- [ ] Components memoized to prevent re-renders
- [ ] No console warnings or errors
- [ ] Network waterfall shows parallel requests
- [ ] Bundle size < 500KB (gzipped)

---

## Testing Strategy

### Unit Tests
```bash
npm test -- ActionHistory.test.tsx
npm test -- EventFeed.test.tsx
npm test -- ConfirmationDialog.test.tsx
```

### Integration Tests
1. WebSocket connection and message flow
2. Filter → API call → UI update
3. Audit log creation and retrieval

### E2E Tests
1. User logs in → Sees accounts
2. Selects account → Loads actions
3. Clicks execute → Confirmation → Action completes → Toast shows
4. Filters actions → Results update
5. Navigates to audit logs → Sees action history

---

## Rollout Plan

### Week 1: Phase 1-2
- WebSocket setup
- Toast notifications
- User testing with toggle feature flag

### Week 2: Phase 3-4
- Advanced filtering
- Audit log integration
- Performance testing

### Week 3: Phase 5
- Performance tuning
- Final testing
- Production deployment

---

## Success Criteria

| Criterion | Target |
|-----------|--------|
| WebSocket uptime | >99.5% |
| Toast display time | <100ms |
| Filter response time | <500ms |
| API request reduction | 80% decrease in polling calls |
| User satisfaction | 4.5+ / 5 stars |
| Bug rate | <1 per 100 user sessions |

---

## Known Risks & Mitigation

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| WebSocket scaling issues | Medium | Use Socket.IO adapter for horizontal scaling |
| Toast performance on slow networks | Low | Implement native OS notifications fallback |
| Audit log DynamoDB costs | Low | Implement TTL, archive to S3 after 90 days |
| Type mismatch between frontend/backend | Medium | Generate types from OpenAPI schema |

---

## Dependencies & Prerequisites

- [x] Sprint 11 Phase 1 + Phase 2 complete
- [ ] Socket.IO library installation
- [ ] DynamoDB audit_logs table schema
- [ ] TypeScript types for socket events
- [ ] React hook for toast management
- [ ] Date picker library (react-datepicker)

---

## Files to Create/Modify in Sprint 12

### New Files (12)
```
apps/web/src/lib/socket.ts
apps/web/src/app/api/socket/route.ts
apps/web/src/lib/hooks/useSocket.ts
apps/web/src/lib/hooks/useToast.ts
apps/web/src/lib/hooks/useDebounce.ts
apps/web/src/components/Toast/Toast.tsx
apps/web/src/components/Toast/ToastContainer.tsx
apps/web/src/components/Dashboard/ActionHistoryFilter.tsx
apps/web/src/components/Dashboard/AuditLogViewer.tsx
apps/web/src/app/api/audit-logs/route.ts
tests/integration/websocket.test.ts
tests/e2e/dashboard-flow.test.ts
```

### Modified Files (6)
```
apps/web/src/components/Dashboard/EventFeed.tsx
apps/web/src/components/Dashboard/ActionHistory.tsx
apps/web/src/components/Providers.tsx (add ToastProvider)
apps/web/src/app/api/actions/route.ts (add filtering)
lambda/guardian/storage/audit_logs.py
lambda/guardian/handler.py
```

---

## Appendix: Socket Event Reference

### Events Emitted by Server
```
event:new - New security event detected
action:complete - Action execution finished
action:failed - Action execution failed
account:status - Account status changed
metrics:update - Cost/metrics update
```

### Events Emitted by Client
```
subscribe-account - Subscribe to account updates
unsubscribe-account - Unsubscribe from account
filter:change - Filter criteria changed
```

---

## Questions & Discussion

- Should we implement Redux for more complex state?
- Should audit logs be queryable by user (RBAC)?
- Should we add real-time notifications/alerts widget?
- Should filtering be saved in URL params or localStorage?

