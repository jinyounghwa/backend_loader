# Sprint 59 Phase 2: Auto-Trigger Engine

## Summary

Completed Phase 2 of Sprint 59: Auto-Trigger Engine. Implemented AutoTriggerEngine class for determining which playbooks should execute automatically vs require manual approval, with priority-based execution queue and 5-second throttling to prevent duplicate executions.

**Phase Status:**
- ✅ Phase 1: ML Prediction → Playbook Mapping (8 tests)
- ✅ Phase 2: Auto-Trigger Engine (9 tests)
- ⏳ Phase 3: Response Metrics & Dashboard (5 tests)
- ⏳ Phase 4: Response Feedback Engine (4 tests)

**Sprint 59 Phase 2 Tests: 9/9 PASS ✅**

---

## Implementation Details

### AutoTriggerEngine Class

**File:** `lambda/guardian/ml/auto_trigger_engine.py` (~210 lines)

**Purpose:** Determines execution eligibility and ordering for playbooks recommended by ResponseMapper.

**Core Methods:**

1. **`should_auto_execute(playbook: Dict) → bool`**
   - Input: Playbook dict
   - Output: True if `auto_execute=True`, False otherwise
   - Logic: Simple boolean flag check
   - Purpose: Filter playbooks by auto-execute capability

2. **`should_trigger_immediately(playbook: Dict, prediction: Dict) → bool`**
   - Input: Playbook dict (with confidence_threshold, severity_threshold), prediction dict (confidence, severity)
   - Output: True if all conditions met
   - Logic:
     - Check `auto_execute=True`
     - Verify `confidence >= confidence_threshold`
     - Verify `severity >= severity_threshold`
   - Purpose: Double-check thresholds before auto-execution

3. **`separate_playbooks(recommended_playbooks: List[Dict]) → Tuple[List[Dict], List[Dict]]`**
   - Input: List of recommended playbooks from ResponseMapper
   - Output: Tuple of (auto_execute_playbooks, manual_approval_playbooks)
   - Logic: Partition by `auto_execute` flag
   - Purpose: Separate workflows for auto vs manual execution

4. **`create_execution_queue(auto_playbooks: List[Dict]) → ExecutionQueue`**
   - Input: Auto-execute playbooks
   - Output: ExecutionQueue ordered by priority
   - Logic: Wrap playbooks in ExecutionQueue (maintains ResponseMapper's priority sorting)
   - Purpose: Prepare playbooks for sequential execution

5. **`can_execute_now(playbook_id: str) → bool`**
   - Input: Playbook ID
   - Output: True if OK to execute, False if throttled
   - Logic:
     - Check if playbook executed in last 5 seconds
     - If yes, return False (throttled)
     - If no, record execution time and return True
   - State: Maintains `last_execution_time` dict
   - Purpose: Prevent spam execution (5-second cooldown per playbook)

6. **`reset_throttle(playbook_id: str) → None`**
   - Input: Playbook ID
   - Output: None
   - Logic: Remove playbook from throttle tracking
   - Purpose: Test helper for clearing throttle state

### ExecutionQueue Class

**File:** `lambda/guardian/ml/auto_trigger_engine.py` (same file, ~85 lines)

**Purpose:** FIFO queue with priority-based ordering for playbooks.

**Core Methods:**

1. **`__init__()`** - Initialize empty queue
2. **`enqueue(playbook: Dict)`** - Add playbook, auto-sort by priority
3. **`dequeue() → Dict | None`** - Remove and return next playbook
4. **`peek() → Dict | None`** - View next without removing
5. **`is_empty() → bool`** - Check if queue empty
6. **`size() → int`** - Get queue length

**Sorting Logic:**
- Primary: `priority` field (ascending: 1 < 2 < 3 = higher to lower priority)
- Secondary: `match_score` field (descending: 0.9 > 0.8 = better scores first within same priority)

---

## Design Decisions

### 1. Auto-Execute is Binary

**Decision:** `auto_execute` field is boolean filter, not a score.

**Why:** 
- Clean separation: auto-execute playbooks execute immediately, others go to approval queue
- No ambiguity: either auto or manual, no gray area
- Defense-in-depth: ResponseMapper filters by thresholds, AutoTriggerEngine validates again

### 2. Priority Ordering is Inherited

**Decision:** Don't re-sort; use priority from ResponseMapper.

**Why:**
- ResponseMapper already sorted by priority (1 = highest)
- ExecutionQueue preserves that ordering
- Avoids re-sorting logic duplication

### 3. Throttling is Playbook-Specific

**Decision:** Each playbook_id has independent 5-second cooldown.

**Why:**
- Prevents spam execution of same playbook
- Allows different playbooks to execute in parallel
- 5-second window is short enough for Lambda execution (15-minute max)
- In-memory storage acceptable (cleared between Lambda invocations)

### 4. Thresholds Double-Checked

**Decision:** AutoTriggerEngine validates confidence/severity even though ResponseMapper already filtered.

**Why:**
- Defense-in-depth pattern
- Adds safety check before auto-execution
- Prevents accidental execution due to data mutation

---

## Testing

### Test Coverage: 9 Tests, 100% Pass Rate

**File:** `tests/backend/test_ml_auto_trigger.py`

#### AutoTriggerEngine Tests (5):

| Test | Purpose | Assertion |
|------|---------|-----------|
| test_auto_execute_flag_filtering | Verify boolean flag check | Correct True/False for mixed playbooks |
| test_confidence_severity_threshold_trigger | Verify dual threshold validation | Both thresholds required for True result |
| test_manual_approval_separation | Verify partitioning by auto_execute | Correct split into auto/manual lists |
| test_priority_queue_ordering | Verify queue priority ordering | Dequeue returns priority 1, then 2, then 3 |
| test_throttle_duplicate_execution | Verify 5-second throttling window | Second execution blocked, third allowed after reset |

#### ExecutionQueue Tests (4):

| Test | Purpose | Assertion |
|------|---------|-----------|
| test_queue_enqueue_dequeue | Basic queue operations | Size tracking and FIFO removal |
| test_queue_peek | Non-destructive viewing | Peek doesn't remove, size unchanged |
| test_queue_is_empty | Queue status checking | Correct empty/non-empty state |
| test_queue_priority_sorting | Priority-based ordering | Correct dequeue order after sorting |

**Test Execution:**
```
============================= test session starts ==============================
platform darwin -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0

tests/backend/test_ml_auto_trigger.py::TestAutoTriggerEngine::test_auto_execute_flag_filtering PASSED [ 11%]
tests/backend/test_ml_auto_trigger.py::TestAutoTriggerEngine::test_confidence_severity_threshold_trigger PASSED [ 22%]
tests/backend/test_ml_auto_trigger.py::TestAutoTriggerEngine::test_manual_approval_separation PASSED [ 33%]
tests/backend/test_ml_auto_trigger.py::TestAutoTriggerEngine::test_priority_queue_ordering PASSED [ 44%]
tests/backend/test_ml_auto_trigger.py::TestAutoTriggerEngine::test_throttle_duplicate_execution PASSED [ 55%]
tests/backend/test_ml_auto_trigger.py::TestExecutionQueue::test_queue_enqueue_dequeue PASSED [ 66%]
tests/backend/test_ml_auto_trigger.py::TestExecutionQueue::test_queue_peek PASSED [ 77%]
tests/backend/test_ml_auto_trigger.py::TestExecutionQueue::test_queue_is_empty PASSED [ 88%]
tests/backend/test_ml_auto_trigger.py::TestExecutionQueue::test_queue_priority_sorting PASSED [100%]

============================== 9 passed ==============================
```

---

## Architecture

### Data Flow: ResponseMapper → AutoTriggerEngine → ExecutionQueue

```
ResponseMapper Output
    ├─ threat_type: 'Unknown Region'
    ├─ recommended_playbooks: [
    │  {
    │    playbook_id: 'pb-unknown-region-block',
    │    auto_execute: True,
    │    priority: 1,
    │    match_score: 0.87,
    │    confidence_threshold: 0.85,
    │    severity_threshold: 7
    │  },
    │  {
    │    playbook_id: 'pb-ssh-isolate',
    │    auto_execute: False,
    │    priority: 2,
    │    match_score: 0.92,
    │    confidence_threshold: 0.90,
    │    severity_threshold: 8
    │  }
    │ ]
    │
    └─ primary_playbook: 'pb-unknown-region-block'
            ↓
    AutoTriggerEngine.separate_playbooks()
            ↓
    Auto-Execute (auto_execute=True)        Manual Approval (auto_execute=False)
    ├─ pb-unknown-region-block              ├─ pb-ssh-isolate
    │  (1 playbook)                         │  (1 playbook)
    │       ↓                                │       ↓
    │  AutoTriggerEngine.create_             │  ApprovalService.request_
    │  execution_queue()                    │  approval()
    │       ↓                                │       ↓
    │  ExecutionQueue                      │  Approval Queue
    │  ├─ peek(): pb-unknown-region-block  │  └─ pending_approvals[]
    │  ├─ dequeue(): pb-unknown-region-    │
    │  │  block → execute immediately      │
    │  └─ is_empty(): True                 │
    │       ↓                                │
    │  can_execute_now('pb-unknown-        │
    │  region-block') → True               │
    │       ↓                                │
    │  Execute playbook                    │
    │  (after throttle check)              │
```

---

## Files Created/Modified

### Implementation
- `lambda/guardian/ml/auto_trigger_engine.py` (210L) - AutoTriggerEngine + ExecutionQueue classes

### Tests
- `tests/backend/test_ml_auto_trigger.py` (250L) - 9 test cases for auto-trigger logic

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.14 |
| Framework | No external dependencies (stdlib only) |
| Testing | pytest 9.0.3 |
| Data Structures | Dict (playbook mapping), List (queue) |
| Algorithms | Priority sorting (by priority field, then match_score) |

---

## Cumulative Test Count

- Sprint 59 Phase 1: 8 tests PASS ✅
- Sprint 59 Phase 2: 9 tests PASS ✅
- **Total so far: 17 tests PASS ✅**

---

## Integration Example

```python
from guardian.ml.response_mapper import ResponseMapper
from guardian.ml.auto_trigger_engine import AutoTriggerEngine

# Phase 1: Map prediction to playbooks
mapper = ResponseMapper()
prediction = {
    'threat_type': 'Unknown Region',
    'confidence': 0.95,
    'severity': 8,
    'account_id': 'test-account',
    'timestamp': '2026-05-26T10:00:00Z'
}
mapping_result = mapper.map_prediction_to_playbook(prediction)

# Phase 2: Determine auto-trigger vs manual approval
engine = AutoTriggerEngine()
auto_playbooks, manual_playbooks = engine.separate_playbooks(
    mapping_result['recommended_playbooks']
)

# Create execution queue for auto-playbooks
execution_queue = engine.create_execution_queue(auto_playbooks)

# Check if first playbook can execute now (respects throttling)
if not execution_queue.is_empty():
    next_pb = execution_queue.peek()
    if engine.can_execute_now(next_pb['playbook_id']):
        pb_to_execute = execution_queue.dequeue()
        # Execute pb_to_execute...
```

---

## Validation Checklist

- [x] AutoTriggerEngine class implemented with 6 methods
- [x] ExecutionQueue class implemented with 6 methods
- [x] Auto-execute flag filtering working
- [x] Confidence/severity threshold double-checking
- [x] Playbook separation into auto/manual groups
- [x] Priority-based queue ordering correct
- [x] 5-second throttling prevents duplicate execution
- [x] All 9 tests passing (5 engine + 4 queue)
- [x] No external dependencies (stdlib only)
- [x] Full integration with Phase 1 ResponseMapper

---

## Next Steps (Sprint 59 Phase 3+)

Phase 3: Response Metrics & Dashboard (5 tests)
- Track playbook execution metrics (success/failure, duration, impact)
- Dashboard panel for execution history and success rates

Phase 4: Response Feedback Engine (4 tests)
- Collect feedback on playbook effectiveness
- Adaptive learning for improving future recommendations

---

## Git Commit

```
feat: Sprint 59 Phase 2 - Auto-Trigger Engine (9 tests)

- Implemented AutoTriggerEngine for playbook auto-execution decision logic
- Added 5 core methods: should_auto_execute, should_trigger_immediately,
  separate_playbooks, create_execution_queue, can_execute_now
- Implemented ExecutionQueue with priority-based FIFO ordering
- Added 5-second throttling to prevent duplicate playbook execution
- Defense-in-depth: double-check confidence/severity thresholds
- Separated auto-execute and manual-approval workflows
- Created 9 comprehensive test cases (5 engine + 4 queue)
- All tests passing; ready for Phase 3 (Response Metrics)

Total Sprint 59 Phase 2: 9 tests PASS
Cumulative: 17 tests PASS (Phase 1 + Phase 2)
```

---

**Completed:** May 26, 2026
**Test Status:** 9/9 PASS ✅
**Ready for:** Phase 3 (Response Metrics & Dashboard) in next session
