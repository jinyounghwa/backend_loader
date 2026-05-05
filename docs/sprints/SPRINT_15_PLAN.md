# Sprint 15: Multi-Region Deployment + Advanced Analysis

**Status**: 📋 Ready for Gemini Review  
**Duration**: ~3 hours (Phase 1: 90min, Phase 2: 60min, Phase 3: 30min)  
**Gemini Collaboration**: Plan → Review → Implement → Document

---

## Executive Summary

Extend AWS Guardian from single-region (ap-northeast-1) to **multi-region deployment** with cross-region threat analysis and advanced AI-powered insights. Enable organizations to monitor AWS resources across all regions from a unified dashboard while maintaining independent response rules per region.

---

## Context

**Current State (Post-Sprint 14)**:
- ✅ Single-region dashboard (ap-northeast-1)
- ✅ Gemini AI threat analysis (Phase 1)
- ✅ Performance optimization (Phase 2)
- ⚠️ Region data exists (instances_by_region, anomalies) but **not visualized**
- ⚠️ API calls only to primary region
- ⚠️ No cross-region CloudTrail correlation

**Sprint 15 Goal**: Enable dashboard to display multi-region metrics and auto-response rules

---

## Phase 1: Multi-Region Dashboard UI (90 min)

### A. Backend Changes (API Enhancement)

**File**: `apps/web/src/app/api/status/route.ts`

```typescript
// BEFORE: Single region hardcoded
const summary = getStatus('ap-northeast-1')

// AFTER: Support region parameter + cross-region aggregation
const regions = req.nextUrl.searchParams.get('regions')?.split(',') || ['ap-northeast-1']
const summaries = await Promise.all(
  regions.map(r => getStatus(r))
)
```

**Endpoints Modified**:
1. `/api/status` → add `?regions=ap-northeast-1,us-east-1,eu-west-1`
2. `/api/events` → filter by region (optional)
3. `/api/actions` → track region per action

**Database Impact**: No schema change (region already in data)

### B. Frontend Components

**New Components**:

1. **RegionSelector** (45 LOC)
   - Multi-select dropdown (React Select or native <select multiple>)
   - Default: all regions
   - Persist to localStorage (user preference)
   - Styled: Tailwind, consistent with Header

2. **RegionMetrics** (80 LOC)
   - 4-column grid: EC2 (running/stopped), S3 (secure/public), Cost (30-day), Anomalies
   - Per-region breakdown
   - Color-coded severity badges
   - Click-to-drill-down (show instances in that region)

3. **RegionComparisonChart** (90 LOC)
   - Bar chart: Region vs Cost (30-day total)
   - Recharts BarChart component (reuse from ChartSection)
   - Tooltip: hover to see breakdown

4. **RegionInstanceMap** (70 LOC) — *Optional*
   - Table: Region | EC2 Running | EC2 Stopped | S3 Buckets | Cost
   - Sortable columns
   - Export to CSV button

**Modified Components**:

1. **page.tsx** (Dashboard)
   - Add RegionSelector above current dashboard
   - If single region selected: show current layout
   - If multi-region: show RegionMetrics + RegionComparisonChart
   - Add region context to all API calls

2. **AccountSelector.tsx** (Optional)
   - Add "All Regions" option
   - OR separate region selector

### C. Data Flow

```
User selects regions in RegionSelector
    ↓
localStorage.setItem('selectedRegions', JSON.stringify(regions))
    ↓
useEffect hooks re-fetch /api/status?regions=...
    ↓
RegionMetrics + RegionComparisonChart update
    ↓
Child components (EventFeed, ActionHistory, etc.) re-filter
```

### D. Styling Notes

- RegionSelector: Similar to AccountSelector (mini pill layout optional)
- RegionMetrics: 4-column grid, responsive (2col on md, 1col on sm)
- RegionComparisonChart: Full width, h-64

---

## Phase 2: Multi-Region Auto-Response (60 min)

### A. Backend Enhancement

**File**: `lambda/guardian/storage/response_rules.py` (NEW)

```python
class ResponseRule:
    rule_id: str
    region: str  # "ap-northeast-1" or "*" for all
    event_type: str  # "unauthorized_region", "open_port", etc.
    action: str  # "stop_instance", "block_bucket"
    enabled: bool
    
def save_rule(rule: ResponseRule) -> None:
    dynamodb.put_item(
        TableName='guardian-response-rules',
        Item=marshal_item(rule)
    )

def get_rules(region: str) -> List[ResponseRule]:
    # Returns rules for region + rules with region="*"
    return query_rules_by_region(region)
```

**Updated Files**:
1. `lambda/guardian/handler.py` → Call `get_rules(region)` before responding
2. `lambda/guardian/responders/telegram.py` → Include region in response context
3. DynamoDB table: `guardian-response-rules` (add GSI on region)

### B. Frontend Enhancement

**New Endpoint**: `/api/response-rules`

```typescript
// GET /api/response-rules?region=ap-northeast-1
export async function GET(req: Request) {
  const region = req.nextUrl.searchParams.get('region') || 'ap-northeast-1'
  const session = await auth()
  if (!session || !isAdmin(session)) return 401

  return NextResponse.json(await fetchRules(region))
}

// POST /api/response-rules (admin only)
export async function POST(req: Request) {
  const { rule } = await req.json()
  await saveRule(rule)
  return NextResponse.json({ success: true })
}
```

**New Component: ResponseRuleManager** (120 LOC) — *Optional*

- Table of rules per region
- Add/Edit/Delete buttons (admin only)
- Test rule button (dry-run)
- Audit trail (log of rule changes)

### C. Test Scenario

```
1. Create rule: region="us-east-1", event_type="open_port", action="stop_instance"
2. CloudTrail event in us-east-1 → Trigger Lambda
3. Lambda queries rule → Found! Execute stop_instance
4. Telegram alert: "Stopped i-xxx in us-east-1 (us-east-1-rule-1)"
```

---

## Phase 3: Advanced AI-Powered Insights (30 min)

### A. Cross-Region Threat Correlation

**New Endpoint**: `/api/analyze-threat-cross-region`

```typescript
// Analyze pattern across regions
export async function POST(req: Request) {
  const { events_by_region } = await req.json()
  // events_by_region: { "ap-northeast-1": [...], "us-east-1": [...], ... }
  
  const prompt = `
    Analyze these security events from multiple AWS regions for correlation patterns:
    ${JSON.stringify(events_by_region)}
    
    Questions:
    1. Is this a coordinated attack (same pattern across regions)?
    2. What's the threat profile?
    3. Recommended response per region?
  `
  
  const analysis = await gemini.analyze(prompt)
  return NextResponse.json(analysis)
}
```

**Use Case**: If malicious traffic detected in ap-northeast-1 AND us-east-1 simultaneously → likely coordinated → escalate to critical

### B. Predictive Insights (Cost Anomaly Detection)

**New Hook**: `useCostAnomalies()`

```typescript
// Detect cost spikes per region using simple statistical model
// Calculate 7-day moving average per region
// Flag if today > moving_avg * 1.2 (20% spike)
// Gemini: "Cost in us-east-1 spiked 35% vs. weekly average. Likely causes: ..."
```

### C. Audit Trail Analytics

**New Endpoint**: `/api/analytics/remediation-effectiveness`

```typescript
// Analyze success rate of auto-response actions
// Query: Last 30 days of remediation actions
// Metrics: success_rate, avg_response_time, most_triggered_rules
// Gemini summary: "Your auto-response success rate is 94%. Most common: stop_instance (45%)"
```

---

## Gemini Collaboration Workflow

### Phase 2a: Architecture Review (Gemini)

**Prompt for Gemini**:
```
Review the multi-region architecture for Sprint 15:

BACKEND:
- DynamoDB response_rules table with region GSI
- Lambda: get_rules(region) filters by region + wildcard "*"
- Telegram responder includes region in context

FRONTEND:
- RegionSelector component (multi-select, localStorage)
- RegionMetrics grid (per-region breakdown)
- /api/status?regions=... aggregation

QUESTIONS:
1. Should response_rules be per region or global with region override?
2. What happens if region is added/removed during runtime?
3. Should UI support partial region failures (1 region down, others OK)?
4. Caching strategy for multi-region data (independent or global TTL)?

Any architectural concerns or improvements?
```

---

## Acceptance Criteria

### Phase 1 ✅
- [ ] RegionSelector renders (multi-select or pills)
- [ ] RegionMetrics displays data for 2+ regions
- [ ] RegionComparisonChart updates on region selection
- [ ] localStorage persists region selection
- [ ] API calls include region parameter
- [ ] Responsive design (works on mobile)
- [ ] Zero TypeScript errors
- [ ] Build time < 2.5s

### Phase 2 ✅
- [ ] POST /api/response-rules creates new rule (admin)
- [ ] Lambda queries rules by region
- [ ] Auto-response executes region-specific rule
- [ ] Telegram alert includes region context
- [ ] Test rule endpoint works (dry-run)

### Phase 3 ✅
- [ ] /api/analyze-threat-cross-region returns correlation analysis
- [ ] Cost anomaly detection flags spikes > 20%
- [ ] Remediation effectiveness metrics calculated
- [ ] Gemini insights generated (3+ insights per analysis)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| API timeout with 5+ regions | High | Parallelize calls with Promise.all(), add timeout |
| Region data inconsistency | Medium | Eventual consistency OK, document 5min lag |
| Rule conflict (global vs regional) | Medium | Clear precedence: regional > global |
| Gemini API cost scaling | Low | Cache results 1hr, batch analyses |

---

## Files to Create/Modify

**NEW**:
```
✨ apps/web/src/components/Dashboard/RegionSelector.tsx
✨ apps/web/src/components/Dashboard/RegionMetrics.tsx
✨ apps/web/src/components/Dashboard/RegionComparisonChart.tsx
✨ apps/web/src/app/api/response-rules/route.ts
✨ apps/web/src/app/api/analyze-threat-cross-region/route.ts
✨ lambda/guardian/storage/response_rules.py
```

**MODIFY**:
```
📝 apps/web/src/app/page.tsx (RegionSelector integration)
📝 apps/web/src/app/api/status/route.ts (region parameter)
📝 lambda/guardian/handler.py (get_rules by region)
📝 NEXT_STEPS.md (Sprint 15 completion)
```

---

## Success Metrics

- **Time**: 3 hours (Phase 1: 90min, Phase 2: 60min, Phase 3: 30min)
- **Build**: Zero TypeScript errors, build time < 2.5s
- **Coverage**: All 3 phases (100%)
- **Components**: +4 new (RegionSelector, RegionMetrics, RegionComparisonChart, ResponseRuleManager)
- **API Endpoints**: +2 new (/response-rules, /analyze-threat-cross-region)
- **Test Status**: Python 116/116 passing (no backend changes that break tests)
- **Documentation**: Sprint 15 completion summary

---

## Gemini Collaboration Status

- [ ] Phase 2a: Gemini Architecture Review
- [ ] Phase 3: Claude Code Implementation
- [ ] Phase 4: Gemini Code Review (optional)
- [ ] Phase 5: Documentation + Commit
