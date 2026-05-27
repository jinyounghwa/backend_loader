# Sprint 64: ML Enhancement & Real-Time Updates

**Status:** 📋 PLANNING  
**Date:** May 27, 2026  
**Duration:** 4 phases  
**Cumulative Target:** 367+ tests (312 current + 55+ new)

---

## Context

**Previous Sprint (Sprint 63) Completion:**
- ✅ Phase 1: Persistence Layer (21 tests)
- ✅ Phase 2: Time-Series Analytics (18 tests)
- ✅ Phase 3: Cost Analytics Engine (8 tests)
- ✅ Phase 4: Dashboard React UI (7 tests)
- **Cumulative:** 312 tests PASS

**Next Milestone:**
Sprint 64 enhances the cost analytics system with machine learning capabilities and real-time dashboard updates. Building on Sprint 63's foundation, we'll add:
1. Seasonal ARIMA forecasting (replacing simple linear regression)
2. Automated optimization recommendations (ML-based)
3. Real-time WebSocket dashboard (replacing polling)
4. Multi-account cost aggregation (enterprise support)

---

## Phase Overview

### Phase 1: Seasonal ARIMA Forecasting (13 tests)
**Goal:** Replace linear regression with seasonal ARIMA for better accuracy on recurring patterns

| Component | Tests | Implementation |
|-----------|-------|-----------------|
| ARIMAForecaster | 8 | AutoARIMA with seasonal decomposition |
| SeasonalityDetector | 3 | Identify yearly/monthly/weekly patterns |
| ModelComparison | 2 | Compare ARIMA vs linear regression |

**Files:**
- `lambda/guardian/analytics/arima_forecaster.py` (new, ~300 lines)
- `lambda/guardian/analytics/seasonality_detector.py` (new, ~250 lines)
- `tests/backend/test_arima_forecasting.py` (new, 13 tests)
- `docs/SPRINT_64_PHASE_1_COMPLETION.md` (documentation)

**Algorithms:**
- ARIMA(p,d,q) with seasonal parameters
- STL (Seasonal and Trend decomposition using Loess)
- AIC/BIC model selection
- Confidence interval calculation

---

### Phase 2: ML-Based Recommendations (14 tests)
**Goal:** Generate intelligent optimization recommendations based on patterns and ML

| Component | Tests | Implementation |
|-----------|-------|-----------------|
| RecommendationEngine | 9 | Pattern-to-action mapping |
| PriorityScorer | 3 | Rank recommendations by impact |
| ROIPredictor | 2 | ML model for savings estimation |

**Files:**
- `lambda/guardian/analytics/recommendation_engine.py` (new, ~320 lines)
- `lambda/guardian/analytics/priority_scorer.py` (new, ~200 lines)
- `lambda/guardian/handlers/recommendations_handler.py` (new, ~180 lines)
- `tests/backend/test_recommendations.py` (new, 14 tests)
- `docs/SPRINT_64_PHASE_2_COMPLETION.md` (documentation)

**ML Features:**
- Detect cost patterns (sudden spikes, gradual trends)
- Match patterns to known optimization actions
- Score recommendations by: impact, feasibility, timeline
- Learn from historical outcomes

---

### Phase 3: WebSocket Real-Time Dashboard (15 tests)
**Goal:** Enable real-time cost updates via WebSocket (replace polling)

| Component | Tests | Implementation |
|-----------|-------|-----------------|
| WebSocketServer | 6 | AWS API Gateway WebSocket setup |
| DashboardConnector | 5 | Client-side connection management |
| RealtimeDataFeed | 4 | Stream cost updates, alerts, metrics |

**Files:**
- `lambda/guardian/handlers/websocket_handler.py` (new, ~250 lines)
- `apps/web/src/hooks/useRealTimeAnalytics.ts` (new, ~180 lines)
- `apps/web/src/components/Dashboard/RealTimeCostMonitor.tsx` (new, ~220 lines)
- `tests/backend/test_websocket.py` (new, 6 tests)
- `apps/web/__tests__/hooks/useRealTimeAnalytics.test.ts` (new, 5 tests)
- `apps/web/__tests__/components/RealTimeCostMonitor.test.tsx` (new, 4 tests)
- `docs/SPRINT_64_PHASE_3_COMPLETION.md` (documentation)

**Features:**
- WebSocket connections: /cost-analytics channel
- Real-time events: forecast updates, spike alerts, recommendations
- Automatic reconnect with exponential backoff
- Client-side state management with useRealTimeAnalytics hook

---

### Phase 4: Multi-Account Aggregation (13 tests)
**Goal:** Support cost analysis across multiple AWS accounts

| Component | Tests | Implementation |
|-----------|-------|-----------------|
| MultiAccountAggregator | 7 | Combine costs from N accounts |
| AccountManager | 4 | Account registration, permissions |
| AggregatedDashboard | 2 | UI for multi-account views |

**Files:**
- `lambda/guardian/storage/account_config.py` (new, ~220 lines)
- `lambda/guardian/analytics/multi_account_aggregator.py` (new, ~280 lines)
- `lambda/guardian/handlers/accounts_handler.py` (new, ~150 lines)
- `apps/web/src/components/Dashboard/AggregatedCostDashboard.tsx` (new, ~240 lines)
- `tests/backend/test_multi_account.py` (new, 7 tests)
- `apps/web/__tests__/components/AggregatedCostDashboard.test.tsx` (new, 4 tests)
- `docs/SPRINT_64_PHASE_4_COMPLETION.md` (documentation)

**Features:**
- Cross-account cost aggregation (SUM, AVG, MAX)
- Cost breakdown by account, service, region
- Consolidated forecasts across accounts
- Account-level recommendations

---

## Test Target Breakdown

| Phase | Unit | Integration | Total | Cumulative |
|-------|------|-------------|-------|------------|
| Phase 1 | 10 | 3 | 13 | 325 |
| Phase 2 | 11 | 3 | 14 | 339 |
| Phase 3 | 13 | 2 | 15 | 354 |
| Phase 4 | 10 | 3 | 13 | 367 |
| **TOTAL** | **44** | **11** | **55** | **367** |

---

## Technical Approach

### Phase 1: ARIMA Implementation
```python
# AutoARIMA with seasonal parameters
from statsmodels.tsa.arima.auto_arima import auto_arima

model = auto_arima(
    data,
    seasonal=True,
    m=12,  # 12-month seasonality
    trace=False,
    error_action='ignore'
)
forecast, conf_int = model.get_forecast(steps=30).conf_int(alpha=0.05)
```

**Advantages over linear regression:**
- Captures seasonal patterns (yearly billing cycles)
- Handles trend changes automatically
- Confidence intervals based on residual variance
- RMSE typically 30-50% lower than linear trend

---

### Phase 2: Recommendation Rules
```python
# Pattern-based recommendations
patterns = {
    "constant_high": "Consider reserved instances or commitment discounts",
    "sudden_spike": "Investigate cost spike - check CloudTrail for changes",
    "gradual_increase": "Monitor trend - implement cost optimization soon",
    "cyclical": "Use seasonal forecast to plan capacity",
}

# ML scoring: (impact × feasibility) / (time_to_implement)
score = (monthly_savings × success_rate) / implementation_days
```

---

### Phase 3: WebSocket Architecture
```
Client (Browser)
    ↓ (WebSocket.onopen)
    ↓ (Subscribe: /cost-analytics)
Lambda WSConnect
    ├─ Store connection ID
    ├─ Add to subscription list
    └─ Send initial state

Real-Time Loop (Lambda triggered by events)
    ├─ New forecast available → broadcast to all clients
    ├─ Spike detected → urgent alert to subscribed clients
    ├─ Recommendation generated → notify relevant accounts
    └─ Metrics updated → push latest numbers

Client (Browser)
    ↓ (Receive message)
    ↓ (Update state via hook)
    ↓ (Re-render components)
```

---

### Phase 4: Multi-Account Model
```
Master Account (Central)
    ├─ Member Account A (role: read-only)
    ├─ Member Account B (role: read-only)
    └─ Member Account C (role: read-only)

Aggregation Query:
    SELECT
        account_id,
        service,
        SUM(cost) as total_cost,
        AVG(cost) as avg_cost,
        MAX(cost) as peak_cost
    FROM cost_events
    GROUP BY account_id, service
```

---

## Implementation Order

**Recommended Sequence:**

1. **Week 1:** Phase 1 (ARIMA) - Backend only, no frontend dependency
2. **Week 2:** Phase 2 (Recommendations) - Builds on Phase 1 output
3. **Week 3:** Phase 3 (WebSocket) - Frontend + backend coordination
4. **Week 4:** Phase 4 (Multi-Account) - Integrates all previous phases

**Rationale:**
- Early phases unblock later phases
- Phase 1 completes before Phase 2 needs its output
- WebSocket (Phase 3) independent until Phase 4
- Multi-account aggregation (Phase 4) requires all components

---

## Deliverables Checklist

### Phase 1
- [ ] ARIMAForecaster class (auto_arima wrapper)
- [ ] SeasonalityDetector (STL decomposition)
- [ ] Model comparison tests
- [ ] Phase 1 completion doc
- [ ] Git commit: "feat: Sprint 64 Phase 1 - Seasonal ARIMA Forecasting (13 tests)"

### Phase 2
- [ ] RecommendationEngine (pattern matching + scoring)
- [ ] PriorityScorer (impact × feasibility)
- [ ] Recommendations Lambda handler
- [ ] Phase 2 completion doc
- [ ] Git commit: "feat: Sprint 64 Phase 2 - ML-Based Recommendations (14 tests)"

### Phase 3
- [ ] WebSocket handler (connect/disconnect/send)
- [ ] useRealTimeAnalytics hook
- [ ] RealTimeCostMonitor component
- [ ] Connection management with retry logic
- [ ] Phase 3 completion doc
- [ ] Git commit: "feat: Sprint 64 Phase 3 - WebSocket Real-Time Updates (15 tests)"

### Phase 4
- [ ] MultiAccountAggregator (cross-account SUM/AVG/MAX)
- [ ] AccountManager (registration, permissions)
- [ ] AggregatedCostDashboard component
- [ ] Cross-account forecasting
- [ ] Phase 4 completion doc
- [ ] Git commit: "feat: Sprint 64 Phase 4 - Multi-Account Aggregation (13 tests)"

### Final
- [ ] Sprint 64 completion report
- [ ] Final commit: "docs: Sprint 64 Final Report - ML & Real-Time Updates (55 tests, 367 cumulative)"

---

## Success Criteria

| Criterion | Target | Baseline |
|-----------|--------|----------|
| Phase 1 tests | 13 PASS | — |
| Phase 2 tests | 14 PASS | — |
| Phase 3 tests | 15 PASS | — |
| Phase 4 tests | 13 PASS | — |
| Total tests | 55 PASS | — |
| Cumulative | 367 PASS | 312 |
| ARIMA RMSE | <Linear RMSE × 0.7 | — |
| WebSocket latency | <200ms | — |
| Multi-account support | ≥3 accounts | — |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| ARIMA complexity | Use statsmodels library (well-tested) |
| WebSocket scaling | Use API Gateway's managed WebSocket (handles 2K+ concurrent) |
| Multi-account permissions | Implement least-privilege cross-account roles |
| ML model overfitting | Use time-series cross-validation (walk-forward) |

---

## Future Extensions (Sprint 65+)

- **Anomaly Detection ML:** Isolate Forest / One-Class SVM for cost outliers
- **Predictive Cost Alerts:** ML model to predict spikes 7 days in advance
- **Cost Attribution:** Tag-based cost allocation to teams/projects
- **RI Optimization:** ML-based reserved instance recommendations
- **Chargeback System:** Automated billing allocation across cost centers

---

## Notes for Implementation

1. **ARIMA Library:** Use `statsmodels.tsa.arima.auto_arima`
   - Handles seasonal components automatically
   - Returns confidence intervals
   - Install: `pip install statsmodels scikit-learn`

2. **WebSocket Testing:** Use `pytest-asyncio` for async Lambda tests
   - Mock API Gateway context
   - Test connection lifecycle (connect → subscribe → disconnect)

3. **Multi-Account Design:** Follow AWS security best practices
   - Cross-account IAM roles (assume role from master account)
   - Least-privilege policy (read-only for cost data)
   - Audit logging (CloudTrail for all API calls)

4. **Performance Considerations:**
   - Cache ARIMA models (reuse if data hasn't changed)
   - Batch WebSocket messages (aggregate updates every 5 seconds)
   - Lazy-load multi-account data (fetch on demand)

---

## Questions for Kickoff

1. Should ARIMA models be retrained daily, weekly, or on-demand?
2. What's the maximum number of accounts to support initially (3, 10, 100+)?
3. Should WebSocket updates be pushed continuously or only on significant changes?
4. Which recommendations should be auto-actionable vs. advisory-only?

**Recommended Answers:**
1. Daily retrain (captures new patterns, relatively cheap)
2. Start with 3-10 accounts (scales to 100+ with read replicas)
3. Significant changes only (spike >10%, new recommendation, metric changes >5%)
4. Advisory-only initially (avoid auto-stopping production workloads)

---

## Ready to Begin

Sprint 64 is ready for implementation. Phases should be executed in order (1 → 2 → 3 → 4) to maximize dependency flow.

**Next Steps:**
1. Confirm implementation approach
2. Start Phase 1: Seasonal ARIMA Forecasting
3. Create tests first (TDD approach)
4. Implement components
5. Document and commit

**Estimated Duration:** 4 weeks (1 week per phase)  
**Target Completion:** Mid-June 2026
