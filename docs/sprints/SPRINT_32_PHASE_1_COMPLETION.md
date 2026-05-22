# Sprint 32 Phase 1: 감사 로그 쿼리 API - 완료

**Status:** ✅ PHASE 1 COMPLETED  
**Date:** 2026-05-22  
**Target Achieved:** HTTP API Gateway, GetAuditLogs Lambda, 쿼리 필터링, 17개 테스트

---

## Sprint 32 Phase 1 완료 요약

Sprint 31의 DynamoDB 감사 로그 저장소를 기반으로, Phase 1은 **감사 로그 쿼리 REST API**를 완성했습니다. 외부 클라이언트가 `GET /audit-logs` 엔드포인트로 WebSocket 이벤트 기록을 조회할 수 있습니다.

---

## 구현 내용

### 1. HTTP API Gateway 추가 (`sam/template.yaml`)

**변경사항:**

#### A. API Gateway 리소스
```yaml
AuditApiGateway:
  Type: AWS::ApiGatewayV2::Api
  Properties:
    Name: ${ProjectName}-audit-api
    ProtocolType: HTTP  # REST API보다 빠르고 저렴
    Description: WebSocket Audit Logs Query API
```

**선택 이유:**
- HTTP API: $0.30/1M requests (저렴)
- REST API: $3.50/1M requests (비쌈)
- 기능: 감시 로그 조회는 간단하므로 HTTP API로 충분

#### B. API Stage & Auto Deploy
```yaml
AuditApiStage:
  Type: AWS::ApiGatewayV2::Stage
  Properties:
    ApiId: !Ref AuditApiGateway
    StageName: !Ref Environment
    AutoDeploy: true
```

#### C. Route & Integration
```yaml
AuditApiRoute:
  Type: AWS::ApiGatewayV2::Route
  Properties:
    RouteKey: 'GET /audit-logs'  # 쿼리 문자열 파라미터 지원
    
AuditApiIntegration:
  Type: AWS::ApiGatewayV2::Integration
  Properties:
    IntegrationType: AWS_PROXY
    PayloadFormatVersion: '2.0'  # HTTP API 페이로드 형식
```

---

### 2. GetAuditLogs Lambda 함수 (`lambda/guardian/handlers/audit_api_handler.py`)

**파일 크기:** 80+ 줄

**핸들러 함수:**
```python
def handle_get_audit_logs(event, context):
    """
    HTTP API 요청 처리
    
    Query String Parameters:
    - connection_id (필수): 조회할 연결 ID
    - start_time (선택): ISO 8601 시작 시간
    - end_time (선택): ISO 8601 종료 시간
    - event_type (선택): $connect, $disconnect, message, broadcast
    
    Response (200):
    {
      "items": [audit log entries],
      "count": N,
      "connection_id": "abc123",
      "filters": { start_time, end_time, event_type }
    }
    """
```

**기능:**
- ✅ Query string 파라미터 파싱
- ✅ connection_id 필수 검증
- ✅ AuditLogger.query_with_filters() 호출
- ✅ JSON 응답 포맷팅
- ✅ 에러 처리 (400/500)

---

### 3. 감사 로거 필터링 확장 (`lambda/guardian/handlers/audit_logger.py`)

**메서드 추가:**
```python
@staticmethod
def query_with_filters(
    connection_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    event_type: Optional[str] = None
) -> list:
    """
    DynamoDB Query + 메모리 필터링
    
    1. connection_id로 PK 기준 조회 (DynamoDB Query)
    2. 메모리에서 추가 필터링:
       - ISO 8601 문자열 비교로 시간 범위 필터
       - event_type 정확 일치 필터
    """
```

**장점:**
- DynamoDB Query는 PK만 지원 → 메모리 필터링으로 유연함
- ISO 8601 형식은 문자열 비교로 정렬 가능
- 대량 결과는 페이지네이션 추가 가능 (Phase 2)

---

### 4. API 테스트 (`tests/cloudformation/test_audit_api.py`)

**파일 크기:** 320+ 줄  
**테스트 수:** 17개 (모두 통과 ✅)

**테스트 범주:**

#### A. API Gateway 검증 (3개)
- ✅ `test_audit_api_gateway_exists` - 리소스 존재
- ✅ `test_audit_api_gateway_name` - !Sub 문법
- ✅ `test_audit_api_stage` - 자동 배포 설정

#### B. Route & Integration 검증 (4개)
- ✅ `test_audit_api_integration_exists` - Integration 리소스
- ✅ `test_audit_api_route_exists` - GET /audit-logs 라우트
- ✅ `test_audit_api_route_to_integration` - 라우트→Integration 연결
- ✅ `test_integration_lambda_uri` - Lambda ARN 참조

#### C. Lambda 함수 검증 (3개)
- ✅ `test_get_audit_logs_function_exists` - 함수 리소스
- ✅ `test_get_audit_logs_handler` - handler 경로 확인
- ✅ `test_get_audit_logs_environment_variables` - 환경변수

#### D. 권한 검증 (3개)
- ✅ `test_get_audit_logs_function_permission_exists` - 권한 리소스
- ✅ `test_get_audit_logs_permission_principal` - API Gateway 호출
- ✅ `test_get_audit_logs_permission_source` - SourceArn 참조

#### E. 출력값/통합 검증 (4개)
- ✅ `test_audit_api_endpoint_output_exists` - 출력값 존재
- ✅ `test_audit_api_endpoint_format` - !Sub 형식
- ✅ `test_audit_api_endpoint_export` - Export 이름 형식
- ✅ `test_integration_payload_format` - PayloadFormatVersion

**테스트 결과:**
```
17 passed in 0.19s ✅

누적 CloudFormation 테스트:
- Phase 1 (Sprint 31): 19 tests
- Phase 2 (Sprint 31): 22 tests
- Phase 3 (Sprint 31): 17 tests
- Phase 1 (Sprint 32): 17 tests
──────────────────────────
합계: 75 tests PASS ✅
```

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| API 게이트웨이 | AWS ApiGatewayV2 (HTTP) |
| Lambda 통합 | AWS_PROXY (2.0 페이로드) |
| 백엔드 조회 | DynamoDB Query + 메모리 필터링 |
| 응답 포맷 | JSON (items, count, filters) |
| 테스트 | Python unittest + pytest (17개) |

---

## 사용 시나리오

### 1. Compliance - 전체 감시 추적
```bash
curl "https://api.example.com/audit-logs?connection_id=abc123"

# 응답: 연결 시작부터 종료까지 모든 이벤트
{
  "items": [
    { "event_type": "$connect", "timestamp": "2026-05-22T15:30:45Z", "status": "success" },
    { "event_type": "message", "timestamp": "2026-05-22T15:31:00Z", "message_type": "broadcast" },
    { "event_type": "$disconnect", "timestamp": "2026-05-22T16:30:45Z", "status": "success" }
  ],
  "count": 3,
  "connection_id": "abc123"
}
```

### 2. Troubleshooting - 시간 범위 조회
```bash
# 오류 발생 시간대 로그 조회
curl "https://api.example.com/audit-logs?connection_id=abc123&start_time=2026-05-22T14:00:00Z&end_time=2026-05-22T14:30:00Z"

# 응답: 해당 시간대의 이벤트만 반환
```

### 3. 보안 조사 - 이벤트 타입 필터
```bash
# 모든 broadcast 이벤트 조회
curl "https://api.example.com/audit-logs?connection_id=abc123&event_type=broadcast"

# 응답: broadcast 이벤트만 반환
```

### 4. 조합 필터
```bash
# 특정 시간대의 error 상태 메시지만
curl "https://api.example.com/audit-logs?connection_id=abc123&start_time=2026-05-22T15:00:00Z&end_time=2026-05-22T16:00:00Z&event_type=message"
```

---

## 성공 기준 검증

| 항목 | 목표 | 결과 | 상태 |
|------|------|------|------|
| HTTP API Gateway | 1개 생성 | AuditApiGateway | ✅ |
| 라우트 | GET /audit-logs | 정의됨 | ✅ |
| Lambda 함수 | GetAuditLogs | 구현됨 (80줄) | ✅ |
| 권한 | API→Lambda 호출 | GetAuditLogsFunctionPermission | ✅ |
| 필터링 | 3가지 필터 | query_with_filters() | ✅ |
| 테스트 | 12개 이상 | 17/17 PASS | ✅ |
| 출력값 | API 엔드포인트 | AuditApiEndpoint | ✅ |
| 누적 테스트 | 70개 | 75/75 PASS | ✅ |

---

## 구현된 파일 목록

### 수정 파일
1. `sam/template.yaml` (1000줄 → 1150줄)
   - AuditApiGateway, AuditApiStage, AuditApiIntegration, AuditApiRoute
   - GetAuditLogsFunction, GetAuditLogsFunctionPermission
   - AuditApiEndpoint 출력값

2. `lambda/guardian/handlers/audit_logger.py` (+50줄)
   - query_with_filters() 메서드 추가

### 신규 파일
1. `lambda/guardian/handlers/audit_api_handler.py` (80+ 줄)
   - handle_get_audit_logs() HTTP 핸들러
   
2. `tests/cloudformation/test_audit_api.py` (320+ 줄)
   - 17개 CloudFormation 테스트

---

## 기술 고려사항

### DynamoDB 쿼리 최적화
**문제**: DynamoDB Query는 PK(connection_id) 기준만 가능
**해결**: 메모리 필터링
- PK로 전체 로그 조회 (빠름)
- 메모리에서 시간/이벤트 타입 필터 (유연함)
- 대량 결과: 페이지네이션으로 확장 가능

### 시간 범위 필터링
**구현**: ISO 8601 문자열 비교
- `timestamp >= start_time AND timestamp <= end_time`
- 예: "2026-05-22T15:30:45.123Z" 문자열 비교로 정렬 가능
- 나노초 정밀도 지원

### 응답 형식
**설계**:
```json
{
  "items": [audit log array],
  "count": number,
  "connection_id": string,
  "filters": { start_time, end_time, event_type }  // 반영된 필터
}
```

### 에러 처리
- **400 Bad Request**: connection_id 누락
- **500 Internal Server Error**: DynamoDB 오류, 예외
- **200 OK**: 빈 결과도 200 반환 (items: [])

---

## 다음 단계 (Sprint 32 Phase 2+)

### Phase 2: 웹 대시보드
**목표**: 감시 로그 시각화

**계획:**
- React 기반 대시보드
- 이벤트 타임라인 시각화
- 필터링 UI (date range picker, event type 선택)
- 페이지네이션

### Phase 3: 멀티 계정 지원
**목표**: 여러 AWS 계정 감시 로그 통합

**계획:**
- Cross-account DynamoDB Streams
- 중앙 집중식 감시 저장소
- 계정별 필터링

---

## 검증 체크리스트

- ✅ SAM 템플릿: HTTP API, Route, Lambda, 권한 추가
- ✅ audit_api_handler.py: HTTP 이벤트 파싱 + 필터링
- ✅ audit_logger.py: query_with_filters() 메서드 추가
- ✅ 17개 API 테스트 모두 PASS
- ✅ 누적 테스트: 75/75 PASS
- ✅ Git 커밋: "feat: Sprint 32 Phase 1 - 감사 로그 쿼리 API"

---

## 커밋 히스토리

```
git commit -m "feat: Sprint 32 Phase 1 - 감사 로그 쿼리 API"
```

---

**Sprint 32 Phase 1 완료!** 🎉

AWS Guardian의 WebSocket 감시 로그를 외부에서 조회할 수 있는 **쿼리 API**가 완성되었습니다:
- ✅ HTTP API Gateway: GET /audit-logs 엔드포인트
- ✅ GetAuditLogs Lambda: 쿼리 파라미터 필터링 지원
- ✅ 시간 범위 + 이벤트 타입 필터링
- ✅ 17/17 테스트 PASS
- ✅ 누적 75/75 테스트 PASS (Sprint 31 + Sprint 32 Phase 1)

**다음 단계: Sprint 32 Phase 2 - 웹 대시보드 (React UI)** 🎨
