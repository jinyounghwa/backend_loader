# Sprint 72: Real-Time Intelligence & Advanced Operations

**목표:** AWS Guardian v2.1 - 실시간 업데이트 + 고급 비용 최적화 + 규칙 빌더 + 통합  
**기간:** 2026-05-30 ~  
**누적 테스트 목표:** 442 + 60 = 502 (60 tests per 4 phases)

---

## 📋 Context

**현황:**
- Sprint 71 완료: 70 테스트 PASS (목표 68 초과)
- 누적 테스트: 442/362 (122%) - AWS Guardian v2.0 완성
- 모든 핵심 기능 구현됨
- 엔터프라이즈 멀티-계정 지원 완료

**Sprint 72 추가 목표:**
1. WebSocket 실시간 업데이트 (대시보드 라이브 스트림)
2. 고급 비용 최적화 (RI 권고, 스팟 인스턴스)
3. 커스텀 규칙 빌더 (UI 없는 API 기반)
4. 써드파티 통합 (Slack, PagerDuty, Teams)

---

## 📋 Phase 1: WebSocket Real-Time Updates (15 tests)

### 기능
- **WebSocketManager**: 클라이언트 연결 관리
- **EventBroadcaster**: 실시간 이벤트 브로드캐스트
- **SubscriptionManager**: 이벤트 구독 관리
- **MessageRouter**: 메시지 라우팅 및 필터링

### 구현 파일 (2개)

#### 신규 생성
- `lambda/guardian/realtime/websocket_manager.py` (300 lines)
  - `WebSocketManager`: 클라이언트 세션 관리
  - `EventBroadcaster`: 이벤트 실시간 전송
  - `SubscriptionManager`: 구독 필터링

- `tests/backend/test_realtime_updates.py` (15 tests)
  - `TestWebSocketManager` (3 tests): 연결 관리
  - `TestEventBroadcaster` (4 tests): 이벤트 브로드캐스트
  - `TestSubscriptionManager` (3 tests): 구독 필터
  - `TestRealtimeIntegration` (5 tests): 통합 테스트

### 기술 스택
- Python websockets (표준)
- DynamoDB 연결 저장소
- EventBridge → Lambda → WebSocket

### 테스트 예시
```python
def test_websocket_connect(self):
    """✅ Client connects to WebSocket."""
    manager = WebSocketManager()
    
    connection = manager.register_client({
        'client_id': 'client_1',
        'user_id': 'user_123'
    })
    
    assert connection['status'] == 'connected'
    assert connection['client_id'] == 'client_1'

def test_broadcast_threat_event(self):
    """✅ Broadcast threat event to subscribed clients."""
    broadcaster = EventBroadcaster()
    
    # Send event
    result = broadcaster.broadcast({
        'event_type': 'THREAT_DETECTED',
        'severity': 'CRITICAL',
        'instance_id': 'i-12345'
    })
    
    assert result['recipients'] > 0
    assert result['status'] == 'delivered'

def test_subscription_filtering(self):
    """✅ Filter events by subscription."""
    manager = SubscriptionManager()
    
    # Subscribe to CRITICAL threats only
    manager.subscribe('client_1', {
        'event_type': 'THREAT_DETECTED',
        'severity': 'CRITICAL'
    })
    
    # Low severity should be filtered
    result = manager.route_event({
        'event_type': 'THREAT_DETECTED',
        'severity': 'LOW'
    })
    
    assert 'client_1' not in result['recipients']
```

---

## 📋 Phase 2: Advanced Cost Optimization (15 tests)

### 기능
- **RIPurchaseAdvisor**: 예약 인스턴스 구매 권고
- **SpotInstanceOptimizer**: 스팟 인스턴스 활용 전략
- **CostForecastor**: 월별 비용 예측
- **OptimizationSimulator**: 변경 시나리오 시뮬레이션

### 구현 파일 (2개)

#### 신규 생성
- `lambda/guardian/optimizers/cost_advisor.py` (350 lines)
  - `RIPurchaseAdvisor`: RI 구매 ROI 계산
  - `SpotInstanceOptimizer`: Spot 가격 트래킹
  - `CostForecastor`: ML 기반 예측

- `tests/backend/test_cost_optimization.py` (15 tests)
  - `TestRIPurchase` (3 tests): RI 권고
  - `TestSpotStrategy` (3 tests): Spot 최적화
  - `TestCostForecasting` (3 tests): 비용 예측
  - `TestOptimizationSimulation` (3 tests): 시뮬레이션
  - `TestCostSavings` (3 tests): 절감액 계산

### 기술 스택
- 기존 cost_predictor 활용
- 간단한 RI/Spot 가격 로직
- 시나리오 계산

### 테스트 예시
```python
def test_ri_purchase_recommendation(self):
    """✅ Recommend RI purchase with ROI."""
    advisor = RIPurchaseAdvisor()
    
    recommendation = advisor.recommend({
        'instance_type': 't3.xlarge',
        'monthly_cost': 300,
        'usage_percentage': 95  # 95% utilized
    })
    
    assert recommendation['action'] == 'PURCHASE_RI_1YEAR'
    assert recommendation['roi'] > 0.25  # 25% savings

def test_spot_instance_strategy(self):
    """✅ Recommend Spot instances for flexible workloads."""
    optimizer = SpotInstanceOptimizer()
    
    strategy = optimizer.optimize({
        'instance_type': 't3.large',
        'monthly_cost': 150,
        'interruption_tolerance': 'HIGH'
    })
    
    assert strategy['recommendation'] == 'USE_SPOT'
    assert strategy['savings'] > 50  # 50%+ savings

def test_cost_forecast_accuracy(self):
    """✅ Forecast monthly costs with > 90% accuracy."""
    forecaster = CostForecastor()
    
    # Train on 90 days
    history = [100 + i*0.5 for i in range(90)]
    
    forecast = forecaster.forecast(history, days=30)
    
    assert len(forecast) == 30
    assert all(f > 0 for f in forecast)
```

---

## 📋 Phase 3: Custom Rule Builder (15 tests)

### 기능
- **RuleBuilder**: 규칙 생성/편집 API
- **RuleValidator**: 규칙 문법 검증
- **RuleExecutor**: 규칙 실행 엔진
- **RuleLibrary**: 규칙 템플릿 라이브러리

### 구현 파일 (2개)

#### 신규 생성
- `lambda/guardian/rules/rule_builder.py` (350 lines)
  - `RuleBuilder`: DSL 기반 규칙 생성
  - `RuleValidator`: 규칙 검증
  - `RuleExecutor`: 규칙 평가
  - `RuleLibrary`: 사전정의 템플릿

- `tests/backend/test_rule_builder.py` (15 tests)
  - `TestRuleBuilder` (3 tests): 규칙 생성
  - `TestRuleValidator` (3 tests): 검증
  - `TestRuleExecution` (3 tests): 실행
  - `TestRuleLibrary` (3 tests): 템플릿
  - `TestRuleIntegration` (3 tests): 통합

### 규칙 DSL 예시
```
IF threat.severity == 'CRITICAL' AND threat.type == 'MALWARE'
THEN action.response = 'ISOLATE' AND notify.channel = 'SLACK'

IF cost.daily > 100
THEN action.escalate = True AND action.approvers = ['ciso@example.com']

IF ec2.security_group.rules.allow_all == True
THEN action.fix = 'BLOCK_0_0_0_0' AND action.audit = True
```

### 테스트 예시
```python
def test_create_simple_rule(self):
    """✅ Create rule: IF threat.severity=CRITICAL THEN stop."""
    builder = RuleBuilder()
    
    rule = builder.create({
        'name': 'Stop Critical Threats',
        'condition': "threat.severity == 'CRITICAL'",
        'actions': ['STOP_INSTANCE', 'NOTIFY_SLACK']
    })
    
    assert rule['rule_id']
    assert rule['status'] == 'active'

def test_validate_rule_syntax(self):
    """✅ Validate rule DSL syntax."""
    validator = RuleValidator()
    
    result = validator.validate({
        'condition': "threat.severity == 'CRITICAL'",
        'actions': ['STOP_INSTANCE']
    })
    
    assert result['valid'] is True
    assert 'errors' not in result

def test_execute_rule_against_threat(self):
    """✅ Execute rule and determine actions."""
    executor = RuleExecutor()
    
    rule = {
        'condition': "threat.severity == 'CRITICAL'",
        'actions': ['ISOLATE']
    }
    
    threat = {'severity': 'CRITICAL', 'type': 'MALWARE'}
    
    actions = executor.execute(rule, threat)
    
    assert 'ISOLATE' in actions
```

---

## 📋 Phase 4: Third-Party Integrations (15 tests)

### 기능
- **SlackIntegration**: Slack 알림 및 상호작용
- **PagerDutyIntegration**: PagerDuty 인시던트 트리거
- **TeamsIntegration**: Microsoft Teams 통합
- **WebhookManager**: 일반 웹훅 지원

### 구현 파일 (2개)

#### 신규 생성
- `lambda/guardian/integrations/third_party_integrations.py` (400 lines)
  - `SlackIntegration`: Slack 메시지, 상호작용
  - `PagerDutyIntegration`: 인시던트 생성
  - `TeamsIntegration`: Teams 카드
  - `WebhookManager`: 커스텀 웹훅

- `tests/backend/test_third_party_integrations.py` (15 tests)
  - `TestSlackIntegration` (3 tests): Slack 메시지
  - `TestPagerDutyIntegration` (3 tests): PagerDuty
  - `TestTeamsIntegration` (3 tests): Teams
  - `TestWebhookManager` (3 tests): 웹훅
  - `TestIntegrationIntegration` (3 tests): 통합 흐름

### 기술 스택
- Slack API (webhook 기반)
- PagerDuty API
- Microsoft Teams webhook
- Custom webhook support

### 테스트 예시
```python
def test_send_slack_threat_notification(self):
    """✅ Send formatted threat alert to Slack."""
    slack = SlackIntegration(webhook_url='...')
    
    result = slack.send_threat({
        'threat_id': 'threat_123',
        'severity': 'CRITICAL',
        'message': 'Unauthorized EC2 in production'
    })
    
    assert result['status'] == 'delivered'
    assert result['message_ts']

def test_create_pagerduty_incident(self):
    """✅ Create PagerDuty incident for high severity."""
    pagerduty = PagerDutyIntegration(api_key='...')
    
    incident = pagerduty.create_incident({
        'title': 'CRITICAL: Malware detected',
        'severity': 'critical',
        'service_id': 'service_123'
    })
    
    assert incident['incident_id']
    assert incident['status'] == 'triggered'

def test_send_teams_alert(self):
    """✅ Send alert to Microsoft Teams."""
    teams = TeamsIntegration(webhook_url='...')
    
    result = teams.send_alert({
        'title': 'Security Alert',
        'description': 'Unauthorized access detected',
        'severity': 'HIGH'
    })
    
    assert result['status'] == 'delivered'

def test_register_custom_webhook(self):
    """✅ Register custom webhook endpoint."""
    manager = WebhookManager()
    
    webhook = manager.register({
        'name': 'custom-siem',
        'url': 'https://siem.example.com/api/events',
        'auth_token': 'secret_token'
    })
    
    assert webhook['webhook_id']
    assert webhook['status'] == 'active'
```

---

## 📊 Sprint 72 Test Summary

| Phase | 제목 | 테스트 |
|-------|------|--------|
| 1️⃣ | WebSocket Real-Time Updates | 15 |
| 2️⃣ | Advanced Cost Optimization | 15 |
| 3️⃣ | Custom Rule Builder | 15 |
| 4️⃣ | Third-Party Integrations | 15 |
| **합계** | **Sprint 72** | **60** |

**Cumulative:** 442 + 60 = **502 tests**

---

## 🛠️ Technical Approach

### Real-Time Updates
- WebSocket 저장소: DynamoDB (연결당 PK: client_id)
- 메시지 라우팅: EventBridge → Lambda → WebSocket 브로드캐스트
- 구독 필터: 메모리 기반 (재연결 시 재설정)

### 비용 최적화
- RI 권고: 과거 90일 사용량 기반 ROI 계산
- Spot 최적화: 인스턴스 타입별 과거 가격 추적
- 예측: 기존 ARIMA 모델 활용

### 규칙 빌더
- DSL: Python ast 기반 간단한 파싱
- 검증: 문법 + 의미 검증 (두 단계)
- 실행: JSON 규칙 → Python 평가

### 써드파티 통합
- 인증: API 키, 웹훅 (URL 저장소)
- 재시도: 지수 백오프 (최대 3회)
- 감시: CloudWatch 로그

---

## 📁 Files to Create (4 files)

### Phase 1
1. `lambda/guardian/realtime/websocket_manager.py`
2. `tests/backend/test_realtime_updates.py`

### Phase 2
1. `lambda/guardian/optimizers/cost_advisor.py`
2. `tests/backend/test_cost_optimization.py`

### Phase 3
1. `lambda/guardian/rules/rule_builder.py`
2. `tests/backend/test_rule_builder.py`

### Phase 4
1. `lambda/guardian/integrations/third_party_integrations.py`
2. `tests/backend/test_third_party_integrations.py`

---

## ✅ Success Criteria

- ✅ 60 tests PASS (15 per phase)
- ✅ WebSocket 메시지 지연 < 100ms
- ✅ 비용 최적화 ROI 계산 정확도 > 90%
- ✅ 규칙 평가 성능 < 50ms
- ✅ 통합 메시지 전달 성공률 > 99%
- ✅ Cumulative: 502/362 tests (139%)

---

## 📅 Estimated Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| 1 | 2-3일 | ⏳ Ready |
| 2 | 2-3일 | ⏳ Ready |
| 3 | 2-3일 | ⏳ Ready |
| 4 | 2-3일 | ⏳ Ready |
| **Total** | **~12일** | ⏳ |

---

**Sprint 72 상태:** ✅ **PLAN READY FOR IMPLEMENTATION**

**선행 조건:** Sprint 71 완료 (✅ 완료)

---

## 🎯 Phase Selection

Choose one phase to start:

**[1]** WebSocket Real-Time Updates (최우선: 라이브 대시보드)  
**[2]** Advanced Cost Optimization (비용 절감)  
**[3]** Custom Rule Builder (유연성)  
**[4]** Third-Party Integrations (확장성)

> Type your choice (1-4) to start implementation
