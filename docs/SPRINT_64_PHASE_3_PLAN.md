# Sprint 64 Phase 3: WebSocket Real-Time Dashboard - Implementation Plan

**Status:** 📋 PENDING  
**Target Date:** Current Development Session  
**Planned Tests:** 15 (bringing total to 363/367)

---

## Overview

Phase 3 builds a real-time dashboard that streams live cost updates via WebSocket, displays live recommendations as costs change, and provides interactive visualizations using Recharts. The system integrates Phase 1 (ARIMA forecasting) and Phase 2 (recommendations) into a unified real-time monitoring interface.

---

## Core Components (To Implement)

### 1. WebSocket Server Handler

**File:** `lambda/guardian/handlers/websocket_handler.py`

**Purpose:** Manage WebSocket connections and broadcast real-time cost updates

**Methods:**

- `handle_connect(connection_id)` - Register new WebSocket connection
  - Store connection ID in DynamoDB
  - Initialize connection metadata (user, account)
  
- `handle_disconnect(connection_id)` - Clean up closed connections
  - Remove connection ID from DynamoDB
  - Clean up session state
  
- `broadcast_cost_update(account_id, cost_data)` - Send live cost to all connected clients
  - Cost: {timestamp, current_cost, forecast, trend, volatility}
  - Send to all connections for account_id
  
- `broadcast_recommendation_update(account_id, recommendations)` - Live recommendations
  - Triggered when new recommendations are generated
  - Sends prioritized recommendations list
  
- `send_alert(connection_id, alert)` - Send cost alert to specific client
  - Alert types: threshold_exceeded, anomaly_detected, recommendation_ready

### 2. Real-Time Cost Streamer

**File:** `lambda/guardian/analytics/cost_streamer.py`

**Purpose:** Generate real-time cost updates with trend analysis

**Methods:**

- `get_current_cost(account_id)` - Get latest cost snapshot
  - Queries Cost Explorer API for most recent hour
  - Calculates trend (↑↓→)
  - Returns: {timestamp, cost, trend, volatility_index}
  
- `stream_cost_updates(account_id, interval_seconds)` - Generate cost stream
  - Polls at regular intervals (default 60s)
  - Compares with forecast from Phase 1
  - Detects anomalies
  - Returns stream of {cost, forecast, variance, alert}
  
- `calculate_cost_variance(actual, forecast)` - Compare to ARIMA forecast
  - Variance = (actual - forecast) / forecast
  - Returns: {variance_percent, is_anomaly, severity}

### 3. Dashboard React Components

**File:** `apps/web/src/components/Dashboard/RealtimeDashboard.tsx`

**Purpose:** Main real-time monitoring interface

**Sub-components:**

- `CostChart.tsx` - Live updating cost chart (Recharts)
  - Line chart: actual vs forecasted cost
  - Real-time updates every 60 seconds
  - Shows trend (↑↓→) and variance bars
  
- `RecommendationPanel.tsx` - Live recommendations list
  - Updates as costs change
  - Shows top 5 prioritized recommendations
  - Action buttons: "Approve", "Snooze", "Dismiss"
  
- `CostMetrics.tsx` - Key metrics card
  - Current cost, daily trend, forecast accuracy
  - Volatility index, anomaly count
  
- `AlertBanner.tsx` - Real-time alerts
  - Cost threshold alerts
  - Anomaly notifications
  - Recommendation ready alerts

### 4. WebSocket Connection Manager

**File:** `apps/web/src/lib/hooks/useWebSocket.ts`

**Purpose:** React hook for WebSocket connection management

**Methods:**

- `useWebSocket(url, account_id)` - Connect and manage WebSocket
  - Auto-reconnect on disconnect
  - Message queue for offline fallback
  - Returns: {isConnected, costData, recommendations, alerts}
  
- `useRealtimeCost(account_id)` - Subscribe to cost updates
  - Returns: {current_cost, forecast, trend, variance}
  
- `useRecommendations(account_id)` - Subscribe to live recommendations
  - Returns: {recommendations, lastUpdate, confidence}

### 5. Cost Alert System

**File:** `lambda/guardian/handlers/alert_handler.py`

**Purpose:** Generate and broadcast cost alerts

**Methods:**

- `check_cost_threshold(account_id, current_cost)` - Alert on threshold exceeded
  - Compare against user-defined threshold
  - Send alert to WebSocket if exceeded
  
- `detect_cost_anomaly(actual, forecast, threshold)` - Detect unusual costs
  - Use Phase 1 forecast confidence intervals
  - Alert if actual outside 95% CI
  
- `generate_recommendation_alert(account_id, recommendations)` - New recommendations ready
  - Alert when high-confidence recommendations found
  - Include summary in alert

---

## Test Plan (15 tests)

### WebSocket Handler Tests (4 tests)
1. `test_websocket_connect` - Connection registration
2. `test_websocket_disconnect` - Connection cleanup
3. `test_broadcast_cost_update` - Cost update broadcasting
4. `test_broadcast_recommendation_update` - Recommendation broadcasting

### Cost Streamer Tests (4 tests)
5. `test_get_current_cost` - Current cost retrieval
6. `test_stream_cost_updates` - Cost update streaming
7. `test_calculate_cost_variance` - Forecast variance calculation
8. `test_anomaly_detection` - Anomaly detection logic

### Dashboard Component Tests (4 tests)
9. `test_cost_chart_rendering` - CostChart component rendering
10. `test_recommendation_panel_updates` - Recommendation updates
11. `test_cost_metrics_display` - Metrics display
12. `test_alert_banner_visibility` - Alert notifications

### WebSocket Hook Tests (3 tests)
13. `test_use_websocket_connection` - Hook connection management
14. `test_use_realtime_cost` - Cost updates subscription
15. `test_use_recommendations_updates` - Recommendation updates subscription

---

## Data Integration Points

**From Phase 1 (ARIMA Forecasting):**
- `ARIMAForecaster.forecast()` → 12-month forecast
- `ARIMAForecaster.get_forecast_summary()` → Forecast confidence intervals
- `SeasonalityDetector.detect_seasonality()` → Seasonal patterns

**From Phase 2 (Recommendations):**
- `RecommendationEngine.prioritize_recommendations()` → Ranked recommendations
- `ImpactCalculator.calculate_breakeven()` → Financial metrics
- `ServiceOptimizer.combined_optimization()` → Service-specific strategies

**Real-Time Data Sources:**
- AWS Cost Explorer API → Current costs
- CloudWatch Metrics → Resource utilization
- DynamoDB Connections → WebSocket clients

---

## WebSocket Message Format

**Client → Server:**
```json
{
  "action": "subscribe",
  "account_id": "123456789",
  "subscriptions": ["costs", "recommendations", "alerts"],
  "filters": {
    "cost_threshold": 100,
    "alert_level": "all"
  }
}
```

**Server → Client (Cost Update):**
```json
{
  "type": "cost_update",
  "timestamp": "2026-05-27T12:00:00Z",
  "account_id": "123456789",
  "data": {
    "current_cost": 1234.56,
    "forecast_cost": 1200.00,
    "trend": "↑",
    "variance_percent": 2.88,
    "is_anomaly": false,
    "volatility_index": 0.15
  }
}
```

**Server → Client (Recommendation Update):**
```json
{
  "type": "recommendation_update",
  "timestamp": "2026-05-27T12:15:00Z",
  "account_id": "123456789",
  "data": {
    "recommendations": [
      {
        "id": "rec-001",
        "service": "ec2",
        "action": "convert_to_reserved_instances",
        "monthly_savings": 300,
        "confidence": 0.95,
        "priority_score": 0.92
      }
    ]
  }
}
```

**Server → Client (Alert):**
```json
{
  "type": "alert",
  "timestamp": "2026-05-27T12:20:00Z",
  "account_id": "123456789",
  "data": {
    "alert_type": "threshold_exceeded",
    "message": "Daily cost exceeded $100 threshold",
    "current_cost": 105.50,
    "threshold": 100,
    "severity": "warning"
  }
}
```

---

## Implementation Strategy

### Step 1: WebSocket Handler (Day 1)
- WebSocket API Gateway setup
- Connection management (connect/disconnect)
- Broadcast mechanism
- Message routing

### Step 2: Cost Streamer (Day 1-2)
- Current cost retrieval from Cost Explorer
- Variance calculation with Phase 1 forecasts
- Anomaly detection
- Streaming logic

### Step 3: React Dashboard (Day 2)
- CostChart component with Recharts
- RecommendationPanel updates
- MetricsCard display
- AlertBanner notifications
- Responsive layout

### Step 4: WebSocket Hooks (Day 2-3)
- useWebSocket hook (connection management)
- useRealtimeCost hook (cost subscription)
- useRecommendations hook (recommendation subscription)
- Message handling and state management

### Step 5: Alert System (Day 3)
- Threshold checking
- Anomaly detection integration
- Alert broadcasting
- User notification preferences

### Step 6: Testing (Day 3-4)
- All 15 tests (100% coverage)
- End-to-end WebSocket flow
- Real-time update verification
- Performance testing (low latency)

---

## Success Criteria

✅ 15 tests passing (100%)  
✅ Real-time cost updates (latency <2 seconds)  
✅ Accurate forecast comparison (variance calculation)  
✅ Live recommendations (update within 30 seconds)  
✅ Cost alerts working (threshold and anomaly)  
✅ Dashboard responsive (works on mobile)  
✅ WebSocket stability (auto-reconnect working)  
✅ Complete documentation  

---

## Architecture Diagram

```
AWS Cost Explorer API
        ↓
CostStreamer (Real-time cost polling)
        ↓
WebSocket Handler (Broadcasting to clients)
        ↓
Connected Clients (Web Dashboard)
        ├─ CostChart (Recharts visualization)
        ├─ RecommendationPanel (Live updates)
        ├─ CostMetrics (KPI display)
        └─ AlertBanner (Notifications)

Integration with Phase 1 & 2:
ARIMAForecaster → CostStreamer (Forecast comparison)
RecommendationEngine → WebSocket (Live recommendations)
ImpactCalculator → Metrics (Financial projections)
```

---

## Files to Create/Modify

**New Files:**
- `lambda/guardian/handlers/websocket_handler.py` (~300 lines)
- `lambda/guardian/analytics/cost_streamer.py` (~250 lines)
- `apps/web/src/components/Dashboard/RealtimeDashboard.tsx` (~200 lines)
- `apps/web/src/components/Dashboard/CostChart.tsx` (~150 lines)
- `apps/web/src/components/Dashboard/RecommendationPanel.tsx` (~150 lines)
- `apps/web/src/lib/hooks/useWebSocket.ts` (~200 lines)
- `tests/backend/test_websocket.py` (~400 lines)
- `tests/frontend/test_realtime_dashboard.tsx` (~300 lines)

**Modified Files:**
- `sam/template.yaml` - Add WebSocket API Gateway
- `apps/web/src/app/page.tsx` - Integrate RealtimeDashboard

---

## Commit Pattern

1. `feat: Add WebSocket handler for real-time streaming`
2. `feat: Add CostStreamer with forecast integration`
3. `feat: Add RealtimeDashboard React components`
4. `feat: Add WebSocket connection hooks`
5. `feat: Add cost alert system`
6. `test: Add 15 tests for real-time dashboard`
7. `docs: Sprint 64 Phase 3 completion`

---

## Next Phase (Phase 4)

**Advanced Analytics & Automation (30 tests)**
- Automated cost optimization actions
- Machine learning model training
- Predictive alerting
- Custom threshold configuration
- Integration with existing Guardian system

---

## Session Continuity Notes

- Phase 1 tests passing: 11/11 ✅
- Phase 2 tests passing: 14/14 ✅
- pmdarima, statsmodels installed
- Phase 1 components available for integration
- Phase 2 analytics components ready
- Cost Explorer API credentials configured

**To Resume Phase 3:**
1. Start with WebSocket handler
2. Integrate Phase 1 ARIMA forecasts
3. Use Phase 2 recommendations
4. Build React components with Recharts
5. Create 15 comprehensive tests
