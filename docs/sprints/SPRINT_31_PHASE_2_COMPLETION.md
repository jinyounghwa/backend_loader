# Sprint 31 Phase 2: CloudWatch 모니터링 & 대시보드 - 완료

**Status:** ✅ PHASE 2 COMPLETED  
**Date:** 2026-05-22  
**Target Achieved:** CloudWatch Dashboard, Alarms, 메트릭 정의, 실시간 모니터링 시스템

---

## Sprint 31 Phase 2 완료 요약

Sprint 31 Phase 1의 SAM/CloudFormation 배포 자동화를 기반으로, Phase 2는 **실시간 모니터링과 자동 알림 시스템**을 완성했습니다. CloudWatch Dashboard와 Alarms를 통해 WebSocket 시스템의 상태를 실시간으로 감시하고 이상 상황을 자동 알림할 수 있습니다.

---

## 구현 내용

### 1. SAM 템플릿 업데이트 (`sam/template.yaml`)

**변경사항:**

#### A. IAM 권한 추가
- **CloudWatchMetricsPolicy** 정책 추가:
  - `cloudwatch:PutMetricData` - 메트릭 발행 권한
  - `cloudwatch:GetMetricStatistics` - 메트릭 조회 권한
  - Resource: `*` (CloudWatch에 대한 모든 리소스)

#### B. SNS Topic 리소스
```yaml
WebSocketAlertsTopic:
  Type: AWS::SNS::Topic
  Properties:
    TopicName: ${ProjectName}-websocket-alerts
    DisplayName: WebSocket Monitoring Alerts
```
- 알람 알림의 중앙 허브 역할
- 이메일, SMS, Lambda 등 다양한 구독자 지원

#### C. CloudWatch Dashboard
**대시보드 이름:** `${ProjectName}-websocket-dashboard`

**4개 섹션 (Widget):**

1. **WebSocket Metrics Overview** (메인 메트릭)
   - ActiveConnections (평균)
   - MessageThroughput (합계)
   - ThreatScore (평균)
   - ConnectionDuration (평균)

2. **Error Monitoring** (오류 모니터링)
   - ConnectionErrors (합계)
   - DisconnectionErrors (합계)

3. **Connection Duration** (연결 지연)
   - ConnectionDuration (평균)
   - ConnectionDuration (최대값)

4. **Performance Metrics** (성능 메트릭)
   - MessageCompressionRatio (평균)
   - BroadcastLatency (평균)

#### D. CloudWatch Alarms (3개)

| Alarm | 메트릭 | 조건 | 기간 | 알림 |
|-------|--------|------|------|------|
| **ConnectionErrorAlarm** | ConnectionErrors | Sum >= 5 | 5분 | SNS |
| **MessageLatencyAlarm** | MessageProcessingLatency | Average >= 5000ms | 2 기간(120초) | SNS |
| **ThreatScoreAlarm** | ThreatScore | Maximum >= 80 | 5분 | SNS |

#### E. 환경 변수 추가
모든 Lambda 함수에 추가:
```yaml
Environment:
  Variables:
    CLOUDWATCH_NAMESPACE: 'aws-guardian/websocket'
    METRICS_ENABLED: 'true'
```

#### F. 출력값 추가
```yaml
Outputs:
  DashboardURL: CloudWatch 콘솔 대시보드 직접 링크
  SNSTopicArn: 알림 구독 및 설정용 SNS Topic ARN
```

---

### 2. 메트릭 정의 & 수집

**메트릭 네임스페이스:** `aws-guardian/websocket`

**수집 메트릭 (9개):**

| 메트릭 | 단위 | 설명 |
|--------|------|------|
| **ActiveConnections** | Count | 현재 활성 WebSocket 연결 수 |
| **MessageThroughput** | Count/Second | 처리된 메시지 수/초 |
| **ThreatScore** | None (0-100) | 감지된 위협 점수 |
| **MessageProcessingLatency** | Milliseconds | 메시지 처리 소요 시간 |
| **ConnectionDuration** | Milliseconds | 연결 유지 시간 |
| **ConnectionErrors** | Count | 연결 오류 발생 횟수 |
| **DisconnectionErrors** | Count | 연결 종료 오류 발생 횟수 |
| **MessageCompressionRatio** | Percent | 메시지 압축률 |
| **BroadcastLatency** | Milliseconds | 위협 브로드캐스트 지연시간 |

**메트릭 Dimensions (선택사항):**
- `ConnectionId` - 특정 연결 단위 추적
- `Region` - AWS 지역별 추적
- `FunctionName` - Lambda 함수별 추적

---

### 3. CloudWatch 테스트 (`tests/cloudformation/test_cloudwatch_alarms.py`)

**파일 크기:** 350+ 줄  
**테스트 수:** 22개 (모두 통과 ✅)

**테스트 범주:**

#### A. Dashboard 검증 (4개)
- ✅ `test_dashboard_resource_exists` - 대시보드 리소스 존재
- ✅ `test_dashboard_name_format` - 올바른 !Sub 문법
- ✅ `test_dashboard_body_valid_json` - Dashboard Body JSON 문법
- ✅ `test_dashboard_has_multiple_sections` - 4개 섹션 위젯 포함

#### B. Alarms 검증 (8개)
- ✅ `test_connection_error_alarm_exists` - ConnectionErrorAlarm 정의
- ✅ `test_message_latency_alarm_exists` - MessageLatencyAlarm 정의
- ✅ `test_threat_score_alarm_exists` - ThreatScoreAlarm 정의
- ✅ `test_alarm_configuration_properties` - 필수 속성 검증
- ✅ `test_alarm_connected_to_sns_topic` - SNS Topic 연결
- ✅ `test_connection_error_alarm_threshold` - 임계값 5개 이상
- ✅ `test_message_latency_alarm_threshold` - 임계값 5000ms 이상
- ✅ `test_threat_score_alarm_threshold` - 임계값 80 이상

#### C. SNS Topic 검증 (3개)
- ✅ `test_sns_topic_exists` - WebSocketAlertsTopic 리소스
- ✅ `test_sns_topic_name_format` - !Sub 문법 사용
- ✅ `test_sns_topic_display_name` - DisplayName 설정

#### D. IAM 권한 검증 (4개)
- ✅ `test_cloudwatch_metrics_iam_policy` - CloudWatchMetrics 정책
- ✅ `test_cloudwatch_metrics_policy_actions` - PutMetricData 액션
- ✅ `test_environment_variables_cloudwatch_namespace` - NAMESPACE 환경변수
- ✅ `test_environment_variables_metrics_enabled` - METRICS_ENABLED 환경변수

#### E. 출력값 검증 (3개)
- ✅ `test_dashboard_url_output` - DashboardURL 출력값
- ✅ `test_sns_topic_arn_output` - SNSTopicArn 출력값
- ✅ `test_output_exports_format` - 올바른 Export 형식

**테스트 결과:**
```
22 passed in 0.22s ✅

누적 테스트:
- Phase 1: 19 tests
- Phase 2: 22 tests
──────────────
합계: 41 tests PASS ✅
```

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 모니터링 | AWS CloudWatch Metrics |
| 대시보드 | AWS CloudWatch Dashboard |
| 알림 | AWS CloudWatch Alarms + SNS |
| 메트릭 네임스페이스 | aws-guardian/websocket |
| 대시보드 구성 | CloudFormation JSON |
| 테스트 | Python unittest + pytest |

---

## 대시보드 사용 방법

### 1. 대시보드 접근
```bash
# CloudWatch 콘솔 접근
aws cloudformation describe-stacks \
  --stack-name aws-guardian-websocket-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue' \
  --output text
```

또는 위의 출력값(DashboardURL)의 링크를 직접 클릭

### 2. 메트릭 조회
```bash
# 특정 메트릭 조회 (최근 1시간)
aws cloudwatch get-metric-statistics \
  --namespace aws-guardian/websocket \
  --metric-name ActiveConnections \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### 3. 알람 상태 확인
```bash
# 모든 Alarms 상태
aws cloudwatch describe-alarms \
  --alarm-name-prefix aws-guardian-websocket \
  --output table
```

### 4. SNS 구독 설정 (알림 수신)
```bash
# SNS Topic ARN 조회
aws cloudformation describe-stacks \
  --stack-name aws-guardian-websocket-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`SNSTopicArn`].OutputValue' \
  --output text

# 이메일 구독
aws sns subscribe \
  --topic-arn <SNS_TOPIC_ARN> \
  --protocol email \
  --notification-endpoint your-email@example.com
```

---

## 임계값 설정 근거

### ConnectionErrorAlarm: 5개 이상
- 정상: 연결 오류 거의 없음
- 경고: 5분에 5개 이상 오류 = 불안정한 연결
- 용도: 네트워크/인프라 문제 조기 감지

### MessageLatencyAlarm: 5000ms (5초) 이상
- 정상: 메시지 처리 < 1000ms
- 경고: 평균 5초 이상 = 성능 저하
- 2 기간: 오탈동 방지 (1분 이상 지속되어야 알람)
- 용도: Lambda 시간 초과, 메모리 부족 감지

### ThreatScoreAlarm: 80 이상
- 0-40: 정상 (낮음)
- 40-70: 주의 (중간)
- 70-100: 위험 (높음)
- 임계값 80: 심각한 위협 즉시 알림
- 용도: 보안 위협 즉시 대응

---

## 성공 기준 검증

| 항목 | 목표 | 결과 | 상태 |
|------|------|------|------|
| CloudWatch Dashboard | 4개 섹션 | 4개 위젯 구성 | ✅ |
| CloudWatch Alarms | 3개 정의 | 3개 완성 | ✅ |
| SNS Topic | 알림 채널 | 설정 완료 | ✅ |
| IAM 권한 | 메트릭 권한 | PutMetricData 추가 | ✅ |
| 환경 변수 | NAMESPACE, ENABLED | 모든 함수에 추가 | ✅ |
| 테스트 | 20개 이상 | 22/22 PASS | ✅ |
| 출력값 | Dashboard/SNS URL | 2개 출력값 추가 | ✅ |

---

## 구현된 파일 목록

### 수정 파일
1. `sam/template.yaml` (520+ 줄 → 약 900줄로 확대)
   - CloudWatchMetricsPolicy IAM 정책 추가
   - WebSocketAlertsTopic SNS 리소스 추가
   - WebSocketDashboard CloudWatch Dashboard 추가
   - ConnectionErrorAlarm CloudWatch Alarm 추가
   - MessageLatencyAlarm CloudWatch Alarm 추가
   - ThreatScoreAlarm CloudWatch Alarm 추가
   - CLOUDWATCH_NAMESPACE, METRICS_ENABLED 환경변수 추가
   - DashboardURL, SNSTopicArn 출력값 추가

### 신규 파일
1. `tests/cloudformation/test_cloudwatch_alarms.py` (350+ 줄)
   - TestCloudWatchDashboard: 4개 테스트
   - TestCloudWatchAlarms: 8개 테스트
   - TestSNSTopic: 3개 테스트
   - TestCloudWatchMetricsIAM: 4개 테스트
   - TestCloudWatchOutputs: 3개 테스트
   - 모두 PASS ✅

---

## 다음 단계 (Sprint 31 Phase 3)

### Phase 3: 감사 로깅
**목표:** 모든 이벤트를 DynamoDB에 기록하고 감사 추적(Audit Trail) 구성

**계획:**
- DynamoDB 감사 로그 테이블 추가
  - PK: `event_id`
  - SK: `timestamp`
  - Attributes: event_type, user_id, action, resource, result, changes
- 이벤트 로깅 (4가지):
  - `$connect` - 연결 성공/실패
  - `$disconnect` - 연결 종료
  - `message` - 메시지 처리
  - `broadcast` - 위협 브로드캐스트
- 90일 TTL 설정 (자동 삭제)
- 감사 로그 조회 Lambda 함수

**예상 테스트:** 10+ 테스트

---

## 기술 하이라이트

### CloudWatch Dashboard
- **Infrastructure as Code**: Dashboard를 CloudFormation JSON으로 정의 → 재현 가능
- **다중 섹션 시각화**: 4개 섹션으로 위협, 연결, 메시지, 성능 분리 모니터링
- **자동 갱신**: 60초 주기로 자동 갱신 (대시보드 개설 시)

### CloudWatch Alarms
- **다중 조건**: Sum, Average, Maximum 등 다양한 통계 활용
- **평가 기간**: 단일 기간(즉시 감지)과 다중 기간(오탈동 방지) 혼합
- **자동 알림**: SNS 통합으로 이메일/SMS/웹훅 지원

### 메트릭 수집
- **네임스페이스 관리**: `aws-guardian/websocket` 단일 네임스페이스 사용
- **확장 가능성**: Dimensions 통해 연결/함수/리전 단위 추적 가능
- **비용 효율**: 9개 메트릭 < AWS 무료 티어 (10개 무료)

---

## 검증 체크리스트

- ✅ SAM 템플릿 업데이트 (IAM, Dashboard, Alarms, 환경변수, 출력값)
- ✅ 22개 CloudWatch 테스트 생성 및 모두 PASS
- ✅ Phase 1 (19개) + Phase 2 (22개) = 41개 테스트 PASS
- ✅ Git 커밋: "feat: Sprint 31 Phase 2 - CloudWatch 모니터링 & 대시보드"
- ✅ 대시보드 4개 섹션 검증
- ✅ 3개 Alarms 임계값 검증
- ✅ SNS Topic 알림 채널 검증

---

## 커밋 히스토리

```
3532dbf feat: Sprint 31 Phase 2 - CloudWatch 모니터링 & 대시보드
```

---

**Sprint 31 Phase 2 완료!** 🎉

AWS Guardian의 WebSocket 시스템이 **실시간 모니터링**과 **자동 알림**을 갖추었습니다:
- ✅ CloudWatch Dashboard: 4개 섹션 실시간 시각화
- ✅ CloudWatch Alarms: 3개 자동 알림 (연결, 지연, 위협)
- ✅ SNS Integration: 이메일/SMS/웹훅 알림 지원
- ✅ 22/22 테스트 통과

**다음 단계: Sprint 31 Phase 3 - 감사 로깅** 🔐

