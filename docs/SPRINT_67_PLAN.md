# Sprint 67: Advanced Features & Optimization

**목표:** AWS Guardian의 모바일 앱, 고급 ML, 성능 최적화, 보안 강화  
**기간:** 2026-05-29 ~  
**누적 테스트 목표:** 236 (176 + 53 tests)

---

## 📋 Phase 1: Mobile App (iOS + Android) - 12 tests

### iOS (Swift) - CloudKit 동기화
**파일 구조:**
```
ios/
├── GuardianApp/
│   ├── ContentView.swift           # Main dashboard
│   ├── Models/
│   │   ├── Alert.swift             # Alert 모델
│   │   ├── Cost.swift              # Cost tracking
│   │   └── Threat.swift            # Threat data
│   ├── Managers/
│   │   ├── CloudKitManager.swift    # CloudKit 동기화
│   │   ├── WebSocketManager.swift   # WebSocket 연결
│   │   └── NotificationManager.swift# 로컬 알림
│   └── Views/
│       ├── AlertListView.swift
│       ├── CostChartView.swift
│       └─ SettingsView.swift
└── Tests/
    └── GuardianAppTests.swift      # 6 tests
```

**핵심 기능:**
1. ✅ CloudKit 동기화 (Dashboard ↔ iPhone)
2. ✅ 오프라인 모드 (로컬 캐시 사용)
3. ✅ 실시간 알림 (UNUserNotificationCenter)
4. ✅ 비용 추세 차트 (Charts 라이브러리)
5. ✅ 위협 타임라인
6. ✅ 푸시 알림 (APNs)

**Tests (6):**
```
✅ test_cloudkit_sync                # CloudKit 데이터 동기화
✅ test_offline_mode                 # 로컬 캐시 사용
✅ test_local_notifications         # UNUserNotificationCenter
✅ test_cost_chart_rendering        # Charts 라이브러리
✅ test_threat_timeline              # 위협 타임라인
✅ test_push_notifications          # APNs 통합
```

**Dependencies:**
```swift
.package(url: "https://github.com/scalessec/Charts.git", from: "4.1.0")
.package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.9.0")
```

---

### Android (Kotlin) - Firebase 통합
**파일 구조:**
```
android/
├── app/src/main/kotlin/com/aws/guardian/
│   ├── MainActivity.kt              # Entry point
│   ├── models/
│   │   ├── Alert.kt
│   │   ├── Cost.kt
│   │   └─ Threat.kt
│   ├── managers/
│   │   ├── FirebaseManager.kt       # Firebase Realtime DB
│   │   ├── WebSocketManager.kt      # WebSocket
│   │   └─ NotificationManager.kt    # Firebase Cloud Messaging
│   ├── ui/
│   │   ├── dashboard/DashboardScreen.kt
│   │   ├── alerts/AlertListScreen.kt
│   │   ├── charts/CostChartScreen.kt
│   │   └─ settings/SettingsScreen.kt
│   └── network/
│       └─ ApiClient.kt              # Retrofit
├── app/build.gradle.kts            # Dependencies
└── Tests/
    └── GuardianTests.kt             # 6 tests
```

**핵심 기능:**
1. ✅ Firebase Realtime DB 동기화
2. ✅ 오프라인 지속성 (Firebase offline)
3. ✅ FCM 푸시 알림
4. ✅ 비용 추세 차트 (MPAndroidChart)
5. ✅ 위협 타임라인
6. ✅ 자동 재연결

**Tests (6):**
```
✅ test_firebase_sync               # Firebase 동기화
✅ test_offline_persistence         # 로컬 지속성
✅ test_fcm_notifications           # Firebase Cloud Messaging
✅ test_cost_chart_rendering        # MPAndroidChart
✅ test_threat_timeline              # 위협 목록
✅ test_auto_reconnect              # WebSocket 자동 재연결
```

**Dependencies:**
```kotlin
implementation("com.google.firebase:firebase-database-ktx:21.0.0")
implementation("com.google.firebase:firebase-messaging-ktx:23.4.0")
implementation("com.github.PhilJay:MPAndroidChart:v3.1.0")
implementation("com.squareup.retrofit2:retrofit:2.11.0")
```

---

## 📋 Phase 2: Advanced ML (15 tests)

### Anomaly Detection 개선
**파일:** `lambda/guardian/ml/advanced_anomaly_detection.py`

**1. Gaussian Mixture Model (GMM)**
```python
class GaussianMixtureDetector:
    def fit(self, data: List[Dict], n_components=3):
        """Fit GMM for multi-modal anomaly detection"""
        # 여러 정상 패턴 학습 (예: 업무시간 vs 밤시간)
    
    def predict(self, data: List[Dict]) -> List[float]:
        """Predict anomaly scores using GMM"""
        # 각 관측값이 어느 분포에도 맞지 않으면 이상
```

**2. Local Outlier Factor (LOF)**
```python
class LocalOutlierDetector:
    def fit(self, data: List[Dict], k=5):
        """Local density-based outlier detection"""
        # 이웃의 밀도와 비교하여 이상탐지
    
    def predict(self, data: List[Dict]) -> List[float]:
        """Anomaly scores based on local density"""
```

**Tests (5):**
```
✅ test_gaussian_mixture_fit
✅ test_gaussian_mixture_predict
✅ test_local_outlier_factor
✅ test_anomaly_detector_ensemble     # 여러 모델 결합
✅ test_anomaly_confidence_score      # 신뢰도 점수
```

### Forecasting 개선
**파일:** `lambda/guardian/ml/advanced_forecasting.py`

**1. Facebook Prophet**
```python
class ProphetForecaster:
    def __init__(self):
        self.prophet = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=True
        )
    
    def forecast(self, df, periods=30):
        """Forecast with automatic seasonality detection"""
        # 계절성 + 추세 + 휴일 효과 자동 감지
```

**2. Dynamic ARIMA**
```python
class DynamicARIMAForecaster:
    def optimize_arima_params(self, data, max_p=5, max_d=2, max_q=5):
        """Auto-optimize ARIMA(p,d,q) using AIC"""
        # 데이터에 최적의 파라미터 자동 선택
    
    def forecast(self, data, steps=7):
        """Forecast with optimized parameters"""
```

**Tests (5):**
```
✅ test_prophet_forecast
✅ test_prophet_seasonality
✅ test_dynamic_arima_optimization
✅ test_dynamic_arima_forecast
✅ test_forecast_model_selection     # Best model 자동 선택
```

### 피드백 루프
**파일:** `lambda/guardian/ml/feedback_loop.py`

```python
class FeedbackLoop:
    def log_prediction_feedback(self, prediction_id, actual_value, user_feedback):
        """기존 예측과 실제값 비교"""
        # MAPE 계산, 정확도 추적
    
    def retrain_from_feedback(self, lookback_days=30):
        """피드백 기반 모델 자동 재학습"""
        # 사용자 확인된 이상은 재학습에 포함
    
    def drift_detection(self):
        """시간 경과에 따른 데이터 분포 변화 감지"""
        # Kolmogorov-Smirnov 검정
```

**Tests (5):**
```
✅ test_prediction_feedback_logging
✅ test_retrain_from_feedback
✅ test_drift_detection
✅ test_model_comparison
✅ test_feedback_quality_metrics
```

---

## 📋 Phase 3: Performance & Scale (14 tests)

### 배치 처리 최적화
**파일:** `lambda/guardian/optimization/batch_processor.py`

```python
class BatchProcessor:
    def parallelize_cost_queries(self, accounts: List[str], days=30):
        """멀티 AWS 계정의 비용 병렬 조회 (ThreadPoolExecutor)"""
        # 10개 계정 → 1초 (순차: 10초)
    
    def batch_cloudtrail_processing(self, events: List[Dict]):
        """CloudTrail 이벤트 배치 처리"""
        # 1000개 이벤트 한번에 처리
    
    def dynamodb_batch_write(self, items: List[Dict]):
        """DynamoDB batch_write_item (최대 25개)"""
```

**Tests (4):**
```
✅ test_parallel_cost_queries
✅ test_cloudtrail_batch_processing
✅ test_dynamodb_batch_operations
✅ test_throughput_optimization
```

### 캐싱 레이어
**파일:** `lambda/guardian/optimization/cache_layer.py`

```python
class CacheLayer:
    def __init__(self):
        self.memory_cache = {}  # In-memory (Lambda warmup)
        self.dynamodb_cache = DynamoDBCache()  # Persistent
        self.cloudfront = CloudFrontCache()    # CDN
    
    def get_cost_data(self, account_id, days=7):
        """3-level 캐싱: Memory → DynamoDB → Cost Explorer"""
        # 대부분의 쿼리는 메모리 캐시에서 반환 (< 10ms)
    
    def invalidate_cache(self, key):
        """캐시 무효화 (새 데이터 도착 시)"""
```

**Tests (4):**
```
✅ test_memory_cache_hit_rate
✅ test_dynamodb_cache_ttl
✅ test_cloudfront_cache_headers
✅ test_cache_invalidation
```

### 모니터링 & Observability
**파일:** `lambda/guardian/optimization/observability.py`

```python
class Observability:
    def log_to_cloudwatch(self, log_group, metrics):
        """CloudWatch Metrics (Lambda duration, error rate, cost)"""
    
    def trace_with_xray(self, function_name):
        """AWS X-Ray 트레이싱"""
        # Lambda → boto3 → AWS API 호출 경로 시각화
    
    def generate_performance_report(self):
        """주간 성능 보고서"""
        # P50, P95, P99 latency
```

**Tests (6):**
```
✅ test_cloudwatch_metrics
✅ test_xray_tracing
✅ test_lambda_duration_tracking
✅ test_error_rate_calculation
✅ test_cost_optimization_impact
✅ test_performance_report_generation
```

---

## 📋 Phase 4: Security Hardening (12 tests)

### 암호화
**파일:** `lambda/guardian/security/encryption.py`

```python
class EncryptionManager:
    def __init__(self):
        self.kms = boto3.client('kms')
    
    def encrypt_sensitive_data(self, data, key_id):
        """KMS로 민감한 데이터 암호화 (저장)"""
        # API keys, credentials, PII
    
    def decrypt_data(self, encrypted_data, key_id):
        """KMS로 데이터 복호화"""
    
    def enable_dynamodb_encryption(self, table_name):
        """DynamoDB 저장 암호화 (SSE-KMS)"""
    
    def enable_s3_encryption(self, bucket_name):
        """S3 저장 암호화 (SSE-KMS)"""
```

**Tests (3):**
```
✅ test_kms_encryption_decryption
✅ test_dynamodb_sse_kms
✅ test_s3_sse_kms
```

### VPC 격리
**파일:** `terraform/security/vpc.tf`

```hcl
# Private Lambda (NAT Gateway 없이)
resource "aws_lambda_function" "guardian_isolated" {
  vpc_config {
    subnet_ids         = [aws_subnet.private.id]
    security_group_ids = [aws_security_group.lambda.id]
  }
}

# VPC Endpoint for AWS services
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_endpoint_type = "Gateway"
  service_name      = "com.amazonaws.us-east-1.dynamodb"
  vpc_id            = aws_vpc.main.id
}
```

**Tests (3):**
```
✅ test_lambda_vpc_isolation
✅ test_vpc_endpoint_connectivity
✅ test_security_group_rules
```

### 감사 로깅
**파일:** `lambda/guardian/security/audit_logging.py`

```python
class AuditLogger:
    def log_action(self, action, user_id, resource_id, details):
        """모든 작업 기록"""
        # CREATE, UPDATE, DELETE, REMEDIATE, DEPLOY
        # DynamoDB AuditTable에 저장
    
    def list_audit_logs(self, resource_id, start_time, end_time):
        """감사 로그 조회"""
    
    def generate_audit_report(self, period='monthly'):
        """월간 감사 보고서"""
```

**Tests (3):**
```
✅ test_action_logging
✅ test_audit_log_query
✅ test_audit_report_generation
```

### 접근 제어 (IAM)
**파일:** `terraform/security/iam.tf`

```hcl
# Lambda 실행 역할 (최소 권한)
resource "aws_iam_role" "lambda_execution" {
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Cost Explorer 읽기 권한만
resource "aws_iam_role_policy" "cost_explorer_read" {
  role = aws_iam_role.lambda_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ce:GetCostAndUsage"
      ]
      Resource = "*"
    }]
  })
}
```

**Tests (3):**
```
✅ test_lambda_iam_policy
✅ test_cross_account_assume_role
✅ test_principle_of_least_privilege
```

---

## 📊 Sprint 67 Test Summary

| Phase | 제목 | 테스트 | 파일 |
|-------|------|--------|------|
| 1️⃣ | Mobile App (iOS/Android) | 12 | `ios/`, `android/` |
| 2️⃣ | Advanced ML (GMM/LOF/Prophet) | 15 | `lambda/guardian/ml/` |
| 3️⃣ | Performance & Scale | 14 | `lambda/guardian/optimization/` |
| 4️⃣ | Security Hardening | 12 | `lambda/guardian/security/`, `terraform/` |
| **합계** | **Sprint 67** | **53** | - |

---

## 📈 Cumulative Progress

```
Sprint 65:  122 tests ✅
Sprint 66:   54 tests ✅ (176 total)
Sprint 67:   53 tests ⏳ (229 planned)

그 이후:
Sprint 68+:  Advanced Cloud-Native (멀티-리전, auto-remediation, 웹훅)
Final:       236+ tests (완전한 AWS Guardian v2.0)
```

---

## 🛠️ Technical Stack (Sprint 67)

### Mobile
- **iOS:** Swift 5.9, CloudKit, UNUserNotificationCenter
- **Android:** Kotlin, Firebase Realtime DB, FCM

### Backend
- **ML:** scikit-learn, pmdarima (Prophet), statsmodels (ARIMA)
- **Performance:** ThreadPoolExecutor, asyncio, DynamoDB TTL
- **Observability:** CloudWatch, AWS X-Ray
- **Security:** KMS, IAM, CloudTrail

### Infrastructure
- **IaC:** Terraform (VPC, Security Groups, IAM)
- **Monitoring:** CloudWatch Dashboards, X-Ray Service Map

---

## ✅ Success Criteria

- [ ] 모바일 앱 (iOS/Android): 12 tests PASS
- [ ] 고급 ML: 15 tests PASS
- [ ] 성능 최적화: 14 tests PASS
- [ ] 보안 강화: 12 tests PASS
- [ ] 누적 테스트: 229/236 PASS (97%)
- [ ] 평균 Lambda 응답시간 < 500ms
- [ ] CloudWatch 모니터링 대시보드 배포
- [ ] KMS 암호화 적용
- [ ] VPC 격리 완료

---

## 📅 Estimated Timeline

| Phase | 작업 | 기간 | 상태 |
|-------|------|------|------|
| 1 | iOS 앱 개발 | 2-3일 | ⏳ Ready |
| 1 | Android 앱 개발 | 2-3일 | ⏳ Ready |
| 2 | ML 모델 개선 | 2-3일 | ⏳ Ready |
| 3 | 성능 최적화 | 2일 | ⏳ Ready |
| 4 | 보안 강화 | 2-3일 | ⏳ Ready |
| **합계** | **Sprint 67** | **~12일** | ⏳ |

---

## 🎯 Next Steps

1. **Phase 1 시작:** 모바일 앱 (iOS CloudKit, Android Firebase)
2. **Phase 2 시작:** 고급 ML (Gaussian Mixture Model, Prophet)
3. **Phase 3 시작:** 성능 최적화 (배치 처리, 캐싱)
4. **Phase 4 시작:** 보안 강화 (KMS, VPC, 감사 로깅)

---

**Sprint 67 상태:** ⏳ **READY TO START**

**선행 조건 완료:**
- ✅ Sprint 66 완료 (176 tests)
- ✅ AWS Guardian Core 완성
- ✅ 실시간 알림 & ML 기초 구축
