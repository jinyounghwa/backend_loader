# Sprint 38: 실시간 규칙 평가 및 성능 최적화

> 규칙 엔진을 실시간으로 동작시키고, 성능을 최적화하며, 사용자 인터페이스를 개선합니다.

---

## 현황

**완료된 스프린트:**
- Sprint 35: 규칙 테스트 및 배포 시스템 (22 tests)
- Sprint 36: 배포 인식 규칙 평가 및 자동 대응 (36 tests)
- Sprint 37: 고급 자동 대응 확장 - Lambda/RDS/VPC (56 tests)

**누적 진행:**
- 총 테스트: 263개
- 구현된 기능:
  - 규칙 관리 및 검증
  - 규칙 Dry-Run 테스트
  - 규칙 배포 및 롤백
  - 배포 인식 이상 탐지
  - 기본 및 고급 자동 대응
  - 다중 서비스 지원 (EC2, S3, Lambda, RDS, VPC)
  - 대응 감사 로깅

---

## Sprint 38 목표

**Phase 1: 실시간 규칙 평가 (15 tests)**
- EventBridge 규칙 생성 (1분/5분/1시간 주기)
- Lambda 함수 배포 (StreamProcessor 핸들러)
- DynamoDB Streams 처리 파이프라인
- CloudWatch 메트릭 통합

**Phase 2: 규칙 성능 최적화 (10 tests)**
- 규칙 캐싱 시스템 (Redis 또는 메모리)
- 병렬 규칙 평가 (asyncio)
- 배치 처리 최적화
- 성능 벤치마킹

**Phase 3: 비용 관리 기능 (8 tests)**
- AWS Cost Explorer 통합
- 비용 이상 탐지
- 리소스별 비용 추적
- 비용 최적화 권장사항

**Phase 4: 대시보드 UI 개선 (12 tests)**
- 실시간 규칙 상태 모니터링
- 대응 히스토리 시각화
- 비용 추이 그래프
- 규칙 성능 통계

**Phase 5: 다중 계정 지원 (10 tests)**
- AWS Organizations 통합
- 계정별 역할 관리
- 크로스 계정 규칙 배포
- 계정별 권한 제어

---

## 상세 구현 계획

### Phase 1: 실시간 규칙 평가

**1.1. EventBridge 규칙 생성 (sam/template.yaml)**

```yaml
RuleEvaluationSchedule:
  Type: AWS::Events::Rule
  Properties:
    ScheduleExpression: 'rate(1 minute)'  # 1분마다 실행
    State: ENABLED
    Targets:
      - Arn: !GetAtt RuleEvaluationLambda.Arn
        RoleArn: !GetAtt EventBridgeRole.Arn

# 추가 규칙 (5분, 1시간)
RuleEvaluationSchedule5M:
  Type: AWS::Events::Rule
  Properties:
    ScheduleExpression: 'rate(5 minutes)'

RuleEvaluationSchedule1H:
  Type: AWS::Events::Rule
  Properties:
    ScheduleExpression: 'rate(1 hour)'
```

**1.2. RuleEvaluationHandler (lambda/guardian/handlers/rule_evaluation_handler.py)**

```python
class RuleEvaluationHandler:
    def __init__(self, rules_repo, detector, responder, audit_repo):
        self.rules = rules_repo
        self.detector = detector
        self.responder = responder
        self.audit = audit_repo
    
    def handle_evaluation(self, event):
        """
        활성화된 규칙으로 최근 로그 분석
        Returns: 탐지된 위협 목록 + 대응 실행 결과
        """
        # 1. ACTIVE 규칙 로드
        rules = self.rules.list_active_rules()
        
        # 2. 병렬로 규칙 평가
        threats = self.detector.detect_anomalies()
        
        # 3. 각 위협에 대해 대응 실행
        for threat in threats:
            rule = self.rules.get_rule(threat.rule_id)
            response = self.responder.orchestrate(rule, threat)
            
            # 4. 감사 로그 기록
            self.audit.record_evaluation(threat, response)
```

**1.3. StreamProcessor 업데이트 (lambda/guardian/handlers/stream_processor.py)**

- DynamoDB Streams 이벤트 처리
- 배치 처리 (배치 크기: 10, 윈도우: 5초)
- 에러 재시도 로직

### Phase 2: 규칙 성능 최적화

**2.1. RuleCache (lambda/guardian/storage/rule_cache.py)**

```python
class RuleCache:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get_active_rules(self):
        """캐시된 활성화 규칙 반환"""
        if self._is_valid():
            return self.cache['active_rules']
        
        # 캐시 미스: DB에서 로드
        rules = self.refresh()
        return rules
    
    def refresh(self):
        """규칙 캐시 새로고침"""
        rules = db.list_active_rules()
        self.cache['active_rules'] = rules
        self.cache['timestamp'] = time.time()
        return rules
```

**2.2. 병렬 규칙 평가**

```python
async def evaluate_rules_parallel(threats, rules):
    """병렬로 규칙 평가"""
    tasks = [
        evaluate_rule_async(threat, rule)
        for threat in threats
        for rule in rules
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### Phase 3: 비용 관리

**3.1. CostAnalyzer (lambda/guardian/analyzers/cost_analyzer.py)**

```python
class CostAnalyzer:
    def analyze_daily_cost(self, account_id):
        """당일 누적 비용 분석"""
        cost = self.explorer.get_daily_cost(account_id)
        
        if cost > self.threshold:
            return Threat(
                threat_id=f"cost-{account_id}",
                severity=cost // 100,  # $100당 심각도 1 증가
                message=f"Daily cost ${cost} exceeds threshold"
            )
    
    def get_resource_costs(self, account_id):
        """리소스별 비용 분석"""
        return self.explorer.get_costs_by_resource(
            account_id,
            granularity='DAILY',
            group_by=['SERVICE']
        )
```

**3.2. 비용 이상 탐지**

- 어제 대비 비용 증가율 > 50%
- 예상 월말 비용 > 설정값
- 미사용 리소스 비용 (유휴 EC2, 데이터 전송 등)

### Phase 4: 대시보드 UI 개선

**4.1. RealTimeMonitoringDashboard (apps/web/src/components/Dashboard/RealTimeMonitoring.tsx)**

```typescript
export const RealTimeMonitoring: React.FC = () => {
  const [activeRules, setActiveRules] = useState<Rule[]>([]);
  const [recentThreats, setRecentThreats] = useState<Threat[]>([]);
  const [metrics, setMetrics] = useState<Metrics>();
  
  useEffect(() => {
    // WebSocket으로 실시간 업데이트
    const ws = new WebSocket('/api/guardian/realtime');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'threat') {
        setRecentThreats(prev => [data.threat, ...prev].slice(0, 10));
      } else if (data.type === 'response') {
        updateResponseStatus(data.response);
      }
    };
    
    return () => ws.close();
  }, []);
  
  return (
    <div>
      <RulesStatus rules={activeRules} />
      <ThreatsTimeline threats={recentThreats} />
      <PerformanceMetrics metrics={metrics} />
      <CostMonitor />
    </div>
  );
};
```

**4.2. ResponseHistoryVisualization (apps/web/src/components/Dashboard/ResponseHistory.tsx)**

- 시간별 대응 실행 횟수 그래프
- 성공/실패 비율
- 평균 대응 시간
- 규칙별 효과도 분석

### Phase 5: 다중 계정 지원

**5.1. AccountManager (lambda/guardian/managers/account_manager.py)**

```python
class AccountManager:
    def get_cross_account_role(self, account_id, role_name):
        """크로스 계정 역할 ARN 생성"""
        return f"arn:aws:iam::{account_id}:role/{role_name}"
    
    def assume_role(self, account_id, role_name):
        """다른 계정의 역할 가정"""
        sts = boto3.client('sts')
        response = sts.assume_role(
            RoleArn=self.get_cross_account_role(account_id, role_name),
            RoleSessionName='GuardianCrossAccount',
            DurationSeconds=900
        )
        return response['Credentials']
    
    def list_accounts(self):
        """AWS Organizations의 모든 계정 조회"""
        orgs = boto3.client('organizations')
        paginator = orgs.get_paginator('list_accounts')
        
        accounts = []
        for page in paginator.paginate():
            accounts.extend(page['Accounts'])
        
        return accounts
```

**5.2. 계정별 권한 제어**

- IAM 역할별 규칙 가시성
- 계정별 대응 실행 권한
- 감사 로그 계정 필터링

---

## 파일 목록 (Phase별)

### Phase 1: 실시간 규칙 평가 (15 tests)
| 파일 | 설명 |
|------|------|
| `sam/template.yaml` | EventBridge 규칙 + Lambda 매핑 |
| `lambda/guardian/handlers/rule_evaluation_handler.py` | 규칙 평가 핸들러 (신규) |
| `lambda/guardian/handlers/stream_processor.py` | DynamoDB Streams 처리 (수정) |
| `tests/backend/test_rule_evaluation_realtime.py` | 실시간 평가 테스트 (신규) |

### Phase 2: 성능 최적화 (10 tests)
| 파일 | 설명 |
|------|------|
| `lambda/guardian/storage/rule_cache.py` | 규칙 캐시 시스템 (신규) |
| `lambda/guardian/detectors/parallel_evaluator.py` | 병렬 규칙 평가 (신규) |
| `tests/backend/test_rule_performance.py` | 성능 벤치마킹 테스트 (신규) |

### Phase 3: 비용 관리 (8 tests)
| 파일 | 설명 |
|------|------|
| `lambda/guardian/analyzers/cost_analyzer.py` | 비용 분석 엔진 (신규) |
| `lambda/guardian/storage/cost_history.py` | 비용 이력 저장소 (신규) |
| `tests/backend/test_cost_analysis.py` | 비용 분석 테스트 (신규) |

### Phase 4: 대시보드 UI (12 tests)
| 파일 | 설명 |
|------|------|
| `apps/web/src/components/Dashboard/RealTimeMonitoring.tsx` | 실시간 모니터링 대시보드 (신규) |
| `apps/web/src/components/Dashboard/ResponseHistory.tsx` | 대응 히스토리 시각화 (신규) |
| `apps/web/src/app/api/guardian/realtime/route.ts` | WebSocket API (신규) |
| `tests/frontend/test_realtime_dashboard.tsx` | UI 테스트 (신규) |

### Phase 5: 다중 계정 (10 tests)
| 파일 | 설명 |
|------|------|
| `lambda/guardian/managers/account_manager.py` | 계정 관리자 (신규) |
| `lambda/guardian/storage/cross_account_role.py` | 크로스 계정 역할 저장소 (신규) |
| `tests/backend/test_multi_account.py` | 다중 계정 테스트 (신규) |

---

## 구현 순서

1. **Phase 1**: 실시간 이벤트 처리 (기초 인프라)
2. **Phase 2**: 성능 최적화 (프로덕션 준비)
3. **Phase 3**: 비용 관리 (부가 기능)
4. **Phase 4**: UI 개선 (사용자 경험)
5. **Phase 5**: 다중 계정 (확장성)

---

## 기술 스택 (Sprint 38)

| 레이어 | 기술 |
|--------|------|
| 실시간 처리 | AWS EventBridge, DynamoDB Streams, Lambda |
| 캐싱 | Redis (선택) 또는 메모리 캐시 |
| 병렬 처리 | asyncio, concurrent.futures |
| 비용 분석 | AWS Cost Explorer API |
| WebSocket | Socket.io 또는 AWS API Gateway WebSocket |
| 프론트엔드 | React 19, Next.js 16, TailwindCSS |

---

## 성공 지표

| 메트릭 | 목표 |
|--------|------|
| 규칙 평가 지연 | < 30초 |
| 캐시 히트율 | > 80% |
| 병렬 처리 속도 향상 | 2-3배 |
| 대시보드 업데이트 지연 | < 2초 |
| 다중 계정 지원 | 10+ 계정 |
| 테스트 커버리지 | 55 tests, 100% PASS |

---

## 다음 스프린트 후 상태

**테스트 진행:**
- Sprint 38: 55 tests
- 누적: 318 tests

**구현 완료:**
- 실시간 규칙 평가 엔진
- 고성능 규칙 캐싱 시스템
- 비용 이상 탐지
- 개선된 사용자 대시보드
- 다중 AWS 계정 지원

**배포 준비:**
- v2.0 릴리스 (실시간 처리 + 성능)
- 프로덕션 환경 배포 문서
- 모니터링 및 알림 설정

---

## Notes

- Phase 별 테스트는 순차적으로 진행
- 각 Phase 완료 후 전체 테스트 재실행
- 성능 벤치마킹은 Phase 2에서 실시
- WebSocket은 선택적 (REST 폴링으로도 가능)
- Redis 캐싱은 선택적 (메모리 캐시로 시작)

---

**준비 상태: ✅ 준비 완료**

Sprint 38은 Sprint 37의 기초 위에 실시간 처리와 성능 최적화를 더하여 프로덕션 준비를 완성합니다.
