# Sprint 64 Phase 2: ML-Based Recommendations - Implementation Plan

**Status:** 📋 PENDING  
**Target Date:** Next Development Session  
**Planned Tests:** 14 (bringing total to 325/367)

---

## Overview

Phase 2 builds a machine learning-based recommendations engine on top of Phase 1's seasonality detection and ARIMA forecasting. The system analyzes cost patterns and service usage to recommend specific optimization actions.

---

## Core Components (To Implement)

### 1. RecommendationEngine Class

**File:** `lambda/guardian/analytics/recommendation_engine.py`

**Purpose:** Analyze costs and generate optimization recommendations

**Methods:**

- `analyze_cost_patterns(values, period)` - Identify high-cost periods and patterns
  - Returns: {peak_periods, off_peak_periods, volatility_score}
  
- `identify_opportunities(services_costs, seasonality)` - Find savings opportunities
  - Input: Dict of service → cost history, seasonality detection results
  - Returns: List of {service, opportunity_type, savings_estimate, confidence}
  
- `generate_recommendations(analysis_result)` - Create actionable recommendations
  - Input: Cost analysis, identified opportunities
  - Returns: List of {action, service, savings_monthly, implementation_effort}
  
- `calculate_roi(recommendation, upfront_cost)` - ROI for each recommendation
  - Returns: {payback_months, annual_savings, roi_percent}
  
- `prioritize_recommendations(recommendations)` - Rank by impact and feasibility
  - Returns: Sorted list by priority score

### 2. ServiceOptimizer Class

**File:** `lambda/guardian/analytics/service_optimizer.py`

**Purpose:** Service-specific optimization strategies

**Methods:**

- `optimize_ec2(instance_data, cost_history)` - EC2 optimization strategies
  - Returns: Recommendations for instance type, reserved instances, spot usage
  
- `optimize_rds(database_data, cost_history)` - RDS optimization strategies
  - Returns: Recommendations for instance class, reserved instances, auto-scaling
  
- `optimize_s3(bucket_data, cost_history)` - S3 optimization strategies
  - Returns: Recommendations for storage class, lifecycle policies, compression
  
- `optimize_lambda(invocation_data, cost_history)` - Lambda optimization strategies
  - Returns: Recommendations for memory allocation, compute optimization
  
- `optimize_dynamodb(table_data, cost_history)` - DynamoDB optimization strategies
  - Returns: Recommendations for on-demand vs provisioned, TTL settings

### 3. ImpactCalculator Class

**File:** `lambda/guardian/analytics/impact_calculator.py`

**Purpose:** Calculate real savings impact for recommendations

**Methods:**

- `estimate_savings(baseline_cost, optimization_type)` - Savings projection
  - Example: Reserved instance 40% savings, Spot instance 70% savings
  
- `validate_feasibility(recommendation, constraints)` - Check if recommendation is feasible
  - Constraints: SLA requirements, application compatibility, migration effort
  
- `calculate_breakeven(upfront_cost, monthly_savings, discount_rate)` - Financial analysis
  - Returns: Payback period, NPV, IRR

---

## Test Plan (14 tests)

### RecommendationEngine Tests (5 tests)
1. `test_analyze_cost_patterns` - Pattern identification
2. `test_identify_opportunities` - Opportunity detection
3. `test_generate_recommendations` - Recommendation generation
4. `test_calculate_roi` - ROI calculation
5. `test_prioritize_recommendations` - Priority ranking

### ServiceOptimizer Tests (7 tests)
6. `test_optimize_ec2` - EC2 strategies
7. `test_optimize_rds` - RDS strategies
8. `test_optimize_s3` - S3 strategies
9. `test_optimize_lambda` - Lambda strategies
10. `test_optimize_dynamodb` - DynamoDB strategies
11. `test_combined_optimization` - Multi-service optimization
12. `test_optimization_validation` - Feasibility checking

### ImpactCalculator Tests (2 tests)
13. `test_estimate_savings` - Savings estimation
14. `test_calculate_breakeven` - Financial analysis

---

## Data Integration Points

**From Phase 1:**
- `SeasonalityDetector.detect_seasonality()` → Seasonal pattern data
- `ARIMAForecaster.forecast()` → Cost forecasts
- `ARIMAForecaster.get_forecast_summary()` → 12-month projections

**From Existing Analytics (Phase 3 - Sprint 63):**
- `CostForecaster.estimate_savings_potential()` → Baseline savings estimates
- Service-level cost breakdown by account/region

**Input Data Structure:**
```python
{
    "account_id": "123456789",
    "service_costs": {
        "ec2": [monthly_costs_24_months],
        "rds": [monthly_costs_24_months],
        "s3": [monthly_costs_24_months],
        ...
    },
    "instance_details": {
        "ec2": [{"instance_id": "i-xxx", "type": "t3.medium", "region": "us-east-1", ...}],
        "rds": [{"db_instance": "prod-db", "class": "db.m5.large", ...}],
    },
    "constraints": {
        "sla_availability": 0.999,
        "max_downtime_hours": 1,
        "budget_constraints": {...}
    }
}
```

---

## Output Format

**Single Recommendation:**
```json
{
    "recommendation_id": "uuid",
    "service": "ec2",
    "action": "convert_to_reserved_instances",
    "description": "Convert 10 t3.medium instances to 1-year reserved instances",
    "current_monthly_cost": 1500,
    "projected_monthly_cost": 900,
    "monthly_savings": 600,
    "annual_savings": 7200,
    "implementation_effort": "low",
    "implementation_steps": ["Step 1", "Step 2"],
    "payback_period_months": 0,
    "confidence": 0.95,
    "priority_score": 0.89,
    "status": "ready_for_implementation"
}
```

---

## Implementation Strategy

### Step 1: RecommendationEngine (Days 1-2)
- Cost pattern analysis (peaks, troughs, volatility)
- Opportunity identification from patterns
- Recommendation generation and ranking
- ROI calculation

### Step 2: ServiceOptimizer (Days 2-3)
- Service-specific strategies (EC2, RDS, S3, Lambda, DynamoDB)
- Feasibility validation
- Cost impact modeling

### Step 3: ImpactCalculator (Day 3)
- Savings estimation with confidence intervals
- Breakeven analysis
- Financial projections (payback, NPV, IRR)

### Step 4: Integration & Testing (Day 4)
- Test all components together
- Integration with Phase 1 outputs
- Performance optimization
- Documentation

---

## Success Criteria

✅ 14 tests passing (100%)
✅ Recommendations with >80% confidence
✅ ROI calculations accurate within 5%
✅ Processing time <1s for typical account
✅ Memory usage <100MB per account
✅ Complete documentation with examples

---

## Key Design Decisions to Make

1. **Recommendation Confidence Scoring**
   - How to weigh pattern reliability vs. historical accuracy?
   - What's the minimum confidence threshold?

2. **Service-Specific Strategies**
   - Which optimization actions to recommend?
   - How to handle service-specific constraints (SLA, compatibility)?

3. **Financial Projections**
   - Use simple payback or NPV/IRR?
   - How to handle discount rates and inflation?

4. **Feasibility Assessment**
   - What constraints are hard blocks vs. warnings?
   - How to assess implementation complexity?

---

## Files to Create/Modify

**New Files:**
- `lambda/guardian/analytics/recommendation_engine.py` (~300 lines)
- `lambda/guardian/analytics/service_optimizer.py` (~400 lines)
- `lambda/guardian/analytics/impact_calculator.py` (~200 lines)
- `tests/backend/test_recommendations.py` (~500 lines)

**Modified Files:**
- `docs/SPRINT_64_PHASE_2_COMPLETION.md` (to be created after implementation)

---

## Commit Pattern

One commit per component:
1. `feat: Add RecommendationEngine for cost pattern analysis`
2. `feat: Add ServiceOptimizer for service-specific strategies`
3. `feat: Add ImpactCalculator for financial analysis`
4. `test: Add 14 tests for recommendations system`
5. `docs: Sprint 64 Phase 2 completion`

---

## Next Phase (Phase 3)

**WebSocket Real-Time Dashboard (15 tests)**
- Real-time cost updates via WebSocket
- Live recommendation updates
- Interactive dashboard with Recharts visualizations
- Server-sent events for cost alerts

---

## Session Continuity Notes

- All Phase 1 tests passing: 11/11 ✅
- pmdarima and statsmodels installed in environment
- Random seeds used in tests for reproducibility
- Test data uses synthetic 36-month time-series with trend + seasonality + noise

**To Resume Phase 2:**
1. Start with RecommendationEngine
2. Use SeasonalityDetector/ARIMAForecaster outputs as inputs
3. Follow test-driven development approach
4. Create comprehensive documentation
