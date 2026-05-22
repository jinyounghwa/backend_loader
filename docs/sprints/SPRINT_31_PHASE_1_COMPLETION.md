# Sprint 31 Phase 1: SAM/CloudFormation 배포 - 완료

**Status:** ✅ PHASE 1 COMPLETED  
**Date:** 2026-05-22  
**Target Achieved:** CloudFormation/SAM 템플릿 작성, 리소스 정의, 테스트 검증

---

## Sprint 31 Phase 1 완료 요약

Sprint 30 Phase 2의 완전한 WebSocket 핸들러와 메시지 압축 시스템을 기반으로, Phase 1은 **AWS SAM/CloudFormation 인프라 배포 자동화**를 완성했습니다.

---

## 구현 내용

### 1. CloudFormation SAM 템플릿 (`sam/template.yaml`)

**파일 크기:** 400+ 줄  
**Format:** YAML (AWS CloudFormation)

**주요 리소스:**

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

# 파라미터
Parameters:
  Environment:        # dev, staging, prod
    Type: String
    Default: prod
  ProjectName:        # aws-guardian
    Type: String
    Default: aws-guardian

# 리소스
Resources:
  # WebSocket API Gateway
  GuardianWebSocketApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      ProtocolType: WEBSOCKET
      RouteSelectionExpression: $request.body.action

  # IAM 역할
  WebSocketLambdaRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument: (Lambda 신뢰 정책)
      Policies:
        - execute-api:ManageConnections 권한

  # Lambda 함수 (6개)
  ConnectFunction:        # $connect 라우트
  DisconnectFunction:     # $disconnect 라우트
  DefaultFunction:        # $default 라우트
  BroadcastFunction:      # 위협 점수 브로드캐스트
  AnomalyAlertFunction:   # 이상 탐지 알림
  ConnectionStatsFunction:# 연결 통계 조회

  # API 통합 (3개)
  ConnectIntegration:     # AWS_PROXY
  DisconnectIntegration:  # AWS_PROXY
  DefaultIntegration:     # AWS_PROXY

  # API 라우트 (3개)
  ConnectRoute:           # $connect
  DisconnectRoute:        # $disconnect
  DefaultRoute:           # $default

  # API Stage
  ApiStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      AutoDeploy: true
      LoggingLevel: INFO
      DataTraceEnabled: true
      ThrottleSettings:
        BurstLimit: 100
        RateLimit: 50

  # CloudWatch 로그
  WebSocketApiLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      RetentionInDays: 30

# 출력값
Outputs:
  WebSocketApiId:         # API ID 내보내기
  WebSocketApiEndpoint:   # WSS 엔드포인트 (wss://...)
  ConnectFunctionArn:     # Lambda ARN
  DisconnectFunctionArn:
  BroadcastFunctionArn:
  Environment:            # 배포 환경
  ProjectName:            # 프로젝트명
```

**특징:**
- ✅ 매개변수화된 배포 (dev/staging/prod 지원)
- ✅ 자동 내보내기 (CloudFormation Export)
- ✅ 환경 변수 주입 (WEBSOCKET_API_ID, WEBSOCKET_API_ENDPOINT)
- ✅ 30일 로그 보유 설정
- ✅ API 쓰로틀링 설정 (Burst: 100, Rate: 50)
- ✅ 자동 배포 설정 (AutoDeploy: true)

---

### 2. SAM 배포 설정 (`sam/samconfig.toml`)

**파일 크기:** 79 줄

**프로파일:**

```toml
[default]
[default.build]
  cached = true
  parallel = true
  use_container = false
  build_dir = ".aws-sam/build"

[default.package]
  s3_bucket = "aws-guardian-deployments"
  s3_prefix = "lambda-builds"
  region = "us-east-1"

[default.deploy]
  stack_name = "aws-guardian-websocket"
  s3_bucket = "aws-guardian-deployments"
  s3_prefix = "lambda-builds"
  region = "us-east-1"
  confirm_changeset = false
  capabilities = "CAPABILITY_IAM"
  parameter_overrides = "Environment=prod"
  tags = ["Project=aws-guardian", "Environment=prod", "ManagedBy=SAM"]

# 개발 프로파일
[dev]
[dev.deploy]
  stack_name = "aws-guardian-websocket-dev"
  parameter_overrides = "Environment=dev"

# 스테이징 프로파일
[staging]
[staging.deploy]
  stack_name = "aws-guardian-websocket-staging"
  parameter_overrides = "Environment=staging"

# 프로덕션 프로파일
[prod]
[prod.deploy]
  stack_name = "aws-guardian-websocket-prod"
  confirm_changeset = true
  parameter_overrides = "Environment=prod"
```

**특징:**
- ✅ 환경별 스택 네이밍 (dev/staging/prod)
- ✅ S3 배포 저장소 설정
- ✅ IAM 권한 설정 (CAPABILITY_IAM)
- ✅ 자동 빌드 캐싱 및 병렬 처리
- ✅ 프로덕션 변경사항 확인 필수 설정
- ✅ 모든 리소스 태그 자동 설정

---

### 3. CloudFormation 템플릿 검증 테스트

**파일:** `tests/cloudformation/test_websocket_template.py`  
**테스트 수:** 19개 (모두 통과 ✅)

**테스트 범주:**

#### TestWebSocketTemplate (14개)
- ✅ `test_template_structure` - AWSTemplateFormatVersion, Transform 검증
- ✅ `test_parameters` - Environment, ProjectName 파라미터 검증
- ✅ `test_websocket_api` - API Gateway 리소스 타입 및 프로토콜
- ✅ `test_lambda_functions` - 6개 Lambda 함수 정의
- ✅ `test_lambda_permissions` - 4개 Lambda 권한 (API Gateway 호출)
- ✅ `test_api_integrations` - 3개 API 통합 (AWS_PROXY)
- ✅ `test_api_routes` - $connect, $disconnect, $default 라우트
- ✅ `test_api_stage` - AutoDeploy, LoggingLevel, DataTraceEnabled
- ✅ `test_cloudwatch_logs` - 로그 그룹 (30일 보유)
- ✅ `test_iam_role` - Lambda 신뢰 정책 및 권한
- ✅ `test_outputs` - 7개 출력값 정의
- ✅ `test_exports` - CloudFormation Export 설정
- ✅ `test_tags` - 리소스 태그 검증
- ✅ `test_environment_variables` - WEBSOCKET_API_ID, WEBSOCKET_API_ENDPOINT

#### TestSamConfig (2개)
- ✅ `test_samconfig_exists` - samconfig.toml 파일 존재
- ✅ `test_samconfig_readable` - samconfig.toml 읽기 가능

#### TestTemplateValidation (3개)
- ✅ `test_no_hardcoded_values` - 하드코딩된 계정 ID 없음
- ✅ `test_parameter_usage` - !Ref ProjectName, !Ref Environment 사용
- ✅ `test_no_missing_permissions` - 모든 API 호출 함수의 권한 정의

**테스트 결과:**
```
19 passed in 0.14s ✅

전체 테스트 합계:
- Sprint 25-30 Phase 2: 151 tests
- Sprint 31 Phase 1: 19 tests
──────────────────────
누적: 170 tests PASS ✅
```

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 템플릿 형식 | AWS CloudFormation (SAM) |
| API 게이트웨이 | AWS ApiGatewayV2 (WebSocket) |
| Lambda 통합 | AWS Serverless Function |
| 배포 자동화 | AWS SAM CLI |
| 패키징 | S3 (aws-guardian-deployments) |
| 로깅 | AWS CloudWatch Logs |
| 액세스 제어 | AWS IAM |
| 모니터링 | CloudWatch (기본 로깅) |

---

## 배포 방식

### SAM 빌드 및 배포

```bash
# 템플릿 검증
aws cloudformation validate-template --template-body file://sam/template.yaml

# SAM 빌드
sam build --template sam/template.yaml

# SAM 배포 (개발 환경)
sam deploy --config-env dev --guided

# SAM 배포 (프로덕션 환경)
sam deploy --config-env prod

# 스택 상태 확인
aws cloudformation describe-stacks \
  --stack-name aws-guardian-websocket-prod \
  --region us-east-1
```

### 출력값 조회

```bash
# WebSocket API 엔드포인트 조회
aws cloudformation describe-stacks \
  --stack-name aws-guardian-websocket-prod \
  --query 'Stacks[0].Outputs' \
  --region us-east-1

# 결과 예시:
# WebSocketApiEndpoint: wss://abc123def.execute-api.us-east-1.amazonaws.com/prod
# WebSocketApiId: abc123def
```

---

## 통합 아키텍처

```
CloudFormation Stack (aws-guardian-websocket)
├── WebSocket API Gateway (WEBSOCKET 프로토콜)
│   ├── $connect 라우트 → ConnectFunction (인증, 등록)
│   ├── $disconnect 라우트 → DisconnectFunction (정리)
│   ├── $default 라우트 → DefaultFunction (메시지 처리)
│   └── Stage (prod/dev/staging, AutoDeploy)
│
├── Lambda 함수들 (Role: WebSocketLambdaRole)
│   ├── ConnectFunction
│   ├── DisconnectFunction
│   ├── DefaultFunction
│   ├── BroadcastFunction
│   ├── AnomalyAlertFunction
│   └── ConnectionStatsFunction
│
├── IAM Role (WebSocketLambdaRole)
│   ├── Trust Policy: lambda.amazonaws.com
│   ├── ManagedPolicy: AWSLambdaBasicExecutionRole
│   └── Policy: execute-api:ManageConnections
│
└── CloudWatch Logs (/aws/apigateway/aws-guardian-websocket)
    └── Retention: 30 days
```

---

## 성공 기준 검증

| 항목 | 목표 | 결과 | 상태 |
|------|------|------|------|
| SAM 템플릿 | 모든 리소스 정의 | 400+ 줄 완성 | ✅ |
| 파라미터 | 환경별 구성 | dev/staging/prod | ✅ |
| Lambda 함수 | 6개 정의 | 모두 정의 | ✅ |
| API 라우트 | 3개 라우트 | $connect/$disconnect/$default | ✅ |
| IAM 역할 | 권한 정의 | execute-api:ManageConnections | ✅ |
| 템플릿 검증 | 19개 테스트 | 19/19 PASS | ✅ |
| 배포 설정 | samconfig.toml | 79줄 완성 | ✅ |
| 출력값 | CloudFormation Export | 7개 출력 | ✅ |

---

## 구현된 파일 목록

### 핵심 인프라
- `sam/template.yaml` - CloudFormation/SAM 템플릿 (400+ 줄)
  - GuardianWebSocketApi (WebSocket API)
  - WebSocketLambdaRole (IAM 역할)
  - 6개 Lambda 함수
  - 3개 API 통합
  - 3개 API 라우트
  - ApiStage (자동 배포)
  - WebSocketApiLogGroup (30일 보유)

- `sam/samconfig.toml` - SAM 배포 설정 (79 줄)
  - [default] 프로파일
  - [dev], [staging], [prod] 프로파일
  - 환경별 스택 네이밍

### 테스트 파일
- `tests/cloudformation/test_websocket_template.py` - CloudFormation 검증 (새 파일)
  - TestWebSocketTemplate: 14개 테스트
  - TestSamConfig: 2개 테스트
  - TestTemplateValidation: 3개 테스트
  - 모두 PASS ✅

---

## 다음 단계 (Sprint 31 Phase 2+)

### Phase 2: CloudWatch 모니터링
- 메트릭 정의 (threat_score, active_connections, message_throughput)
- 대시보드 구성 (threat, connections, throughput, latency)
- 알람 설정 (에러율, 지연시간)

### Phase 3: 감사 로깅
- DynamoDB 감사 로그 테이블
- 이벤트 로깅 (connect, disconnect, message, broadcast)
- 90일 TTL 설정

### Phase 4: 성능 대시보드
- P50/P95/P99 지연시간
- 메시지 처리량
- CPU/메모리 사용률
- 배치 효율

---

## 기술 하이라이트

### CloudFormation 모범 사례
- ✅ 매개변수화된 템플릿 (환경별 배포)
- ✅ 자동 내보내기 (다른 스택에서 참조 가능)
- ✅ IAM 권한 최소화 (execute-api:ManageConnections만)
- ✅ 환경 변수 주입 (!Sub, !Ref 사용)
- ✅ 자동 배포 설정 (AutoDeploy: true)
- ✅ 로깅 및 모니터링 구성

### SAM 특징
- ✅ Serverless 함수 축약 표기법
- ✅ 자동 권한 관리 (부분)
- ✅ 환경별 배포 프로파일
- ✅ S3 기반 패키지 관리

---

## 검증 체크리스트

- ✅ CloudFormation 템플릿 작성 (400+ 줄)
- ✅ SAM 배포 설정 (samconfig.toml)
- ✅ 6개 Lambda 함수 정의
- ✅ 3개 API 라우트 설정 ($connect/$disconnect/$default)
- ✅ IAM 역할 및 권한 정의
- ✅ CloudWatch 로그 설정 (30일 보유)
- ✅ 환경별 파라미터 (dev/staging/prod)
- ✅ 7개 출력값 정의
- ✅ 19개 CloudFormation 테스트 (모두 PASS)
- ✅ 누적 테스트 170/170 PASS

---

## 커밋 히스토리

```
✨ Sprint 31 Phase 1: SAM/CloudFormation 배포 자동화
```

---

**Sprint 31 Phase 1 완료!** 🎉

AWS Guardian의 WebSocket 배포 인프라가 완성되었습니다:
- ✅ 400+ 줄 CloudFormation/SAM 템플릿
- ✅ 환경별 배포 설정 (dev/staging/prod)
- ✅ 19/19 템플릿 검증 테스트 통과
- ✅ 누적 170/170 테스트 PASS

**AWS Guardian 실시간 알림 시스템의 인프라 배포가 준비 완료되었습니다!** 🚀☁️
