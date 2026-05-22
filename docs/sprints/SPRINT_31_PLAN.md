# Sprint 31: WebSocket 배포 & 모니터링 시스템

**Status:** 📋 PLANNED  
**Target:** SAM/CloudFormation 배포, CloudWatch 모니터링, 감사 로깅

---

## Sprint 31 Overview

Sprint 30의 완전한 실시간 알림 시스템을 기반으로, Sprint 31은 **인프라 배포 자동화**와 **운영 모니터링**에 집중합니다.

---

## Phase 31.1: SAM/CloudFormation 배포 (이번 구현)

### WebSocket API Gateway 리소스

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  # WebSocket API
  GuardianWebSocketApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: GuardianWebSocket
      ProtocolType: WEBSOCKET
      RouteSelectionExpression: $request.body.action
      Description: Real-time threat notifications

  # $connect 라우트
  ConnectRouteFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: guardian-websocket-connect
      Handler: lambda/guardian/handlers/websocket_handler.handle_connect
      Runtime: python3.12
      Environment:
        Variables:
          WEBSOCKET_API_ID: !Ref GuardianWebSocketApi

  # $disconnect 라우트
  DisconnectRouteFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: guardian-websocket-disconnect
      Handler: lambda/guardian/handlers/websocket_handler.handle_disconnect
      Runtime: python3.12

  # $default 라우트
  DefaultRouteFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: guardian-websocket-default
      Handler: lambda/guardian/handlers/websocket_handler.handle_default
      Runtime: python3.12

  # 브로드캐스트 함수
  BroadcastFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: guardian-threat-broadcast
      Handler: lambda/guardian/handlers/websocket_handler.handle_threat_broadcast
      Runtime: python3.12
      Environment:
        Variables:
          WEBSOCKET_API_ID: !Ref GuardianWebSocketApi

  # 연결 테이블 (선택사항)
  ConnectionTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: GuardianWebSocketConnections
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: connectionId
          AttributeType: S
        - AttributeName: userId
          AttributeType: S
      KeySchema:
        - AttributeName: connectionId
          KeyType: HASH
        - AttributeName: userId
          KeyType: RANGE
      TTL:
        AttributeName: expiresAt
        Enabled: true
```

### 라우트 통합

```yaml
  # $connect 라우트
  ConnectRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref GuardianWebSocketApi
      RouteKey: $connect
      AuthorizationType: NONE
      Target: !Sub integrations/${ConnectIntegration}

  ConnectIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref GuardianWebSocketApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !Sub arn:aws:apigatewayv2:${AWS::Region}:lambda:path/2015-03-31/functions/${ConnectRouteFunction.Arn}/invocations

  # $disconnect 라우트
  DisconnectRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref GuardianWebSocketApi
      RouteKey: $disconnect
      Target: !Sub integrations/${DisconnectIntegration}

  # $default 라우트
  DefaultRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref GuardianWebSocketApi
      RouteKey: $default
      Target: !Sub integrations/${DefaultIntegration}

  # Stage
  ApiStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      ApiId: !Ref GuardianWebSocketApi
      StageName: prod
      AutoDeploy: true
      LoggingLevel: INFO
      DataTraceEnabled: true
```

---

## Phase 31.2: CloudWatch 모니터링 (다음 계획)

### 메트릭 정의

```python
# 위협 점수 변동
ThreatScoreChange:
  - MetricName: threat_score_updated
  - Dimensions: [account_id, severity]
  - Unit: Count

# WebSocket 연결 수
ActiveConnections:
  - MetricName: websocket_active_connections
  - Dimensions: [region]
  - Unit: Count

# 메시지 처리량
MessageThroughput:
  - MetricName: websocket_messages_processed
  - Dimensions: [message_type, severity]
  - Unit: Count/Second

# 압축 효율
CompressionRatio:
  - MetricName: message_compression_ratio
  - Dimensions: [none]
  - Unit: Percent
```

### CloudWatch 대시보드

```yaml
DashboardName: GuardianWebSocketMonitoring
Widgets:
  - ThreatScoreGauge
  - ActiveConnectionsLineChart
  - MessageThroughputBarChart
  - CompressionRatioLineChart
  - ErrorRateLineChart
  - LatencyP99Histogram
```

---

## Phase 31.3: 감사 로깅 (다음 계획)

### 감사 로그 항목

```python
class AuditLog:
    timestamp: datetime
    connection_id: str
    user_id: str
    action: str  # connect, disconnect, message, broadcast
    details: Dict
    result: str  # success, failed
    error: Optional[str]
```

### 저장소

```python
# DynamoDB: GuardianAuditLogs
# GSI: user_id-timestamp
# TTL: 90일
```

---

## Phase 31.4: 성능 대시보드 (다음 계획)

### 메트릭

```
- P50/P95/P99 지연시간
- 연결당 메시지 처리량
- CPU/메모리 사용률
- 에러율 (5xx, 4xx)
- 배치 효율
```

---

## 성공 기준

✅ **CloudFormation 배포**
- SAM 템플릿 작성
- 모든 리소스 정의
- 배포 자동화

✅ **CloudWatch 모니터링**
- 메트릭 수집
- 대시보드 구성
- 알람 설정

✅ **감사 로깅**
- 모든 이벤트 기록
- 감사 추적 가능
- 법규 준수

---

**Sprint 31 계획 완료!** 📋
