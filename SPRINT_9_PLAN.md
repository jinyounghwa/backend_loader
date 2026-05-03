# Sprint 9: Telegram 고급 명령어 + Gemini AI 통합

**상태**: 📋 Gemini 아키텍처 검증 대기
**계획 수립**: 2026-05-03
**시작 예정**: 2026-05-08
**완료 예정**: 2026-05-08 (3시간 개발 + 1시간 Gemini 검증)

---

## 목표

Telegram 봇에 3개 고급 명령어 추가 + Gemini AI 위협 분석 통합

---

## 현재 상황 분석

### 기존 기능
- `/status` - EC2, S3, 비용 상태 조회 ✅
- `/instances` - 인스턴스 목록 ✅
- `/stop {id}` - 인스턴스 중지 ✅
- `/threshold {amount}` - 비용 임계값 변경 ✅
- `/history [hours]` - 이벤트 로그 ✅
- `/help` - 명령어 도움말 ✅

### 추가할 기능 (Sprint 9)
1. **`/remediate <finding-id>`** - GuardDuty 발견사항 자동 대응
2. **`/export [csv|pdf|json]`** - 이벤트 및 비용 보고서 생성
3. **`/insights`** - Gemini AI로 최근 위협 패턴 분석

---

## Phase 1: 명령어 설계 (아키텍처 검증 필요)

### 1.1 `/remediate <finding-id>`

**목적**: GuardDuty 발견사항에 대한 자동 대응 실행

**플로우**:
```
사용자: /remediate finding-123
  ↓
telegram_bot.py: finding-id 파싱 + DynamoDB 조회
  ↓
remediation_service.py: 발견사항에 맞는 대응 실행
  ├─ EC2 관련 → EC2 중지
  ├─ S3 관련 → 퍼블릭 액세스 차단
  └─ IAM 관련 → 액세스 키 비활성화
  ↓
DynamoDB: remediation 히스토리 저장
  ↓
Telegram: 결과 리포트 (성공/실패)
```

**구현 세부사항**:
- **파싱**: `/remediate {finding-id}` → 정규표현식으로 finding-id 추출
  - 보안 검증: SQL injection 방지 + 사용자 권한 검증
- **조회**: `guardian-events` 테이블에서 finding-id로 검색
  - GSI 활용: `event_id + timestamp` 복합키
  - 검색 조건: `event_type="guardduty" AND event_id=finding-id`
- **대응 실행**:
  - 트랜잭션 안전성: 부분 실패 시 롤백
  - 예시: `{"resource_id": "i-123", "action": "stop_instance"}`
  - Idempotent: 이미 중지된 인스턴스 재실행 시에도 안전
- **저장**:
  - `guardian-responses` 테이블에 remediation 기록
  - 필드: `user_id, finding_id, action, status, timestamp`
- **응답**:
  ```
  ✅ Remediation successful for finding-123
  
  Finding: [GuardDuty Finding Title]
  Resource: i-123 (EC2 Instance)
  Action: Stopped instance
  Status: Completed (2s)
  
  Timestamp: 2026-05-08 14:30:45 UTC
  ```

**Gemini 검증 항목**:
- ⚠️ 명령어 파싱: 정규표현식 보안 (injection 방지)
- ⚠️ 트랜잭션: 부분 실패 시 롤백 전략 (원자성)
- ⚠️ Idempotency: 동일 명령어 재실행 시 안전성
- ⚠️ 권한: admin만 remediation 실행 가능?

---

### 1.2 `/export [csv|pdf|json]`

**목적**: 이벤트 및 비용 데이터를 보고서 형식으로 내보내기

**플로우**:
```
사용자: /export csv --days 7 --severity high
  ↓
telegram_bot.py: 옵션 파싱 (format, days, severity)
  ↓
event_exporter.py: DynamoDB 쿼리
  ├─ GSI: SeverityTimestampIndex 활용
  ├─ 필터: severity >= high AND timestamp > 7d ago
  └─ 결과: 100-1000 이벤트
  ↓
변환: CSV/PDF/JSON 형식 변환
  ├─ CSV: pandas로 테이블 생성
  ├─ PDF: fpdf2로 보고서 생성 (헤더, 표, 요약)
  └─ JSON: 구조화된 JSON 배열
  ↓
저장: /tmp/report_[timestamp].{csv|pdf|json}
  ↓
Telegram: 파일 업로드 (최대 50MB)
```

**구현 세부사항**:
- **옵션 파싱**:
  ```
  /export csv --days 7 --severity high --limit 100
  → format="csv", days=7, severity="high", limit=100
  ```
  - 정규표현식: `--(\w+) (\w+)` 매칭
  - 기본값: format="csv", days=7, severity=None, limit=500
- **DynamoDB 쿼리**:
  - GSI: `SeverityTimestampIndex` (Sprint 3에서 생성)
  - 쿼리: `severity >= :sev AND timestamp > :time`
  - 페이지네이션: 1000개 제한 + 반복 쿼리
  - RCU 최적화: Query 사용 (Scan 대비 99% 절감)
- **변환**:
  - **CSV**: 열 = `timestamp, severity, event_type, resource_id, message, status`
  - **PDF**: 
    - 헤더: 생성 시간, 필터 조건, 이벤트 수
    - 본문: 이벤트 테이블 (10줄/페이지)
    - 요약: 심각도별 분포 (차트)
  - **JSON**: 배열 형식 (자동화 도구 연동용)
- **파일 저장**:
  - 경로: `/tmp/report_{timestamp}_{format}.{ext}`
  - 크기 제한: 50MB (Telegram 제한)
  - 대용량 처리: Lambda temp storage 활용 (512MB 한도)
- **응답**:
  ```
  📊 Report generated successfully
  
  Format: CSV
  Events: 523
  Filters: severity >= high, days <= 7
  File: report_20260508_1430.csv (2.3 MB)
  
  (파일 업로드)
  ```

**Gemini 검증 항목**:
- ⚠️ 정규표현식: 옵션 파싱 보안
- ⚠️ DynamoDB 쿼리: Query vs Scan (RCU 최적화)
- ⚠️ 메모리: 대용량 파일 생성 시 Lambda 메모리 (512MB vs 1GB)
- ⚠️ 타임아웃: 15분 제한 내 대용량 쿼리 + 변환 완료

---

### 1.3 `/insights`

**목적**: Gemini AI로 최근 24시간 위협 패턴 분석 및 권장사항 생성

**플로우**:
```
사용자: /insights
  ↓
telegram_bot.py: 명령어 인식
  ↓
event_exporter.py: 최근 24시간 이벤트 수집
  ├─ 쿼리: timestamp > 24h ago (모든 severity)
  ├─ 집계: 심각도별, 타입별 통계
  └─ 결과: JSON 형식
  ↓
gemini_threat_analyzer.py: Gemini API 호출
  ├─ 프롬프트: 이벤트 데이터 + 컨텍스트
  ├─ 요청: 위협 분석 + 권장사항 (한글)
  └─ 응답: Gemini 분석 결과
  ↓
Telegram: 분석 결과 포맷팅 + 전송
```

**구현 세부사항**:
- **데이터 수집**:
  ```python
  # DynamoDB GSI 쿼리
  events = query_events(
    filter={
      "timestamp": {"gte": now - timedelta(hours=24)},
    },
    projection=["event_type", "severity", "resource_id", "message"]
  )
  
  # 집계
  summary = {
    "total_events": len(events),
    "by_severity": {"CRITICAL": 5, "HIGH": 12, "MEDIUM": 20},
    "by_type": {"guardduty": 15, "cloudtrail": 10, "ec2": 12},
    "affected_resources": [...]
  }
  ```

- **Gemini 프롬프트**:
  ```
  다음은 지난 24시간 AWS 환경에서 탐지된 위협 데이터입니다.
  
  [JSON 형식 데이터]
  
  다음을 한글로 분석해주세요:
  1. 주요 위협 패턴 (3-5가지)
  2. 우선순위별 대응 조치
  3. 추가 모니터링 영역
  
  간결하고 실행 가능한 형식으로 작성해주세요.
  ```

- **API 통합**:
  - SDK: `google.generativeai` (Python)
  - 모델: `gemini-1.5-flash` (빠른 응답)
  - 비용: 약 $0.001/호출 (전체 요청량 기준)
  - 에러 처리: API 실패 시 → 기본 통계만 제공 (fallback)

- **응답 예시**:
  ```
  🔍 위협 분석 보고서 (지난 24시간)
  
  📊 요약
  - 총 이벤트: 37개
  - 심각도 분포: 🔴 5 🟠 12 🟡 20
  - 영향 리소스: EC2 (12), S3 (8), IAM (17)
  
  ⚠️ 주요 위협 패턴
  1. GuardDuty: Cryptocurrency mining 시도 (5건)
     → 대응: EC2 인스턴스 검사 + 중지
  2. CloudTrail: 비정상적인 IAM 권한 변경 (3건)
     → 대응: IAM 감사 + 권한 재설정
  3. S3: 퍼블릭 버킷 정책 변경 감지 (2건)
     → 대응: 퍼블릭 액세스 차단
  
  ✅ 권장사항
  - GuardDuty Agent 업데이트 (최신 탐지 규칙)
  - CloudTrail 로그 분석 강화 (실시간)
  - S3 정책 변경 알림 설정
  
  🔐 다음 조치
  /remediate {finding-id}로 자동 대응 실행 가능
  ```

**Gemini 검증 항목**:
- ⚠️ 프롬프트: 한글 품질 + 정확성 + 실행 가능성
- ⚠️ 보안: API 키 관리 (SSM Parameter Store)
- ⚠️ 비용: Gemini API 호출 빈도 (매 요청 $0.001+)
- ⚠️ 신뢰성: API 실패 시 fallback 전략

---

## Phase 2: 구현 세부사항

### 수정 파일: `lambda/guardian/responders/telegram_bot.py`

**추가 메서드**:
```python
@bot.on_message(command="remediate")
async def handle_remediate(message: Message):
    """GuardDuty 발견사항 자동 대응"""
    # 1. 파싱: /remediate {finding-id}
    # 2. DynamoDB 조회: finding-id로 세부사항 검색
    # 3. remediation_service.py 호출
    # 4. 결과 리포트

@bot.on_message(command="export")
async def handle_export(message: Message):
    """이벤트 및 비용 보고서 생성"""
    # 1. 파싱: /export [csv|pdf|json] --options
    # 2. event_exporter.py 호출
    # 3. 파일 생성 + 업로드

@bot.on_message(command="insights")
async def handle_insights(message: Message):
    """Gemini AI 위협 분석"""
    # 1. 데이터 수집: 최근 24시간 이벤트
    # 2. gemini_threat_analyzer.py 호출
    # 3. 분석 결과 포맷팅 + 전송
```

### 신규 파일: `lambda/guardian/analyzers/gemini_threat_analyzer.py`

```python
from google import generativeai as genai
import json

class GeminiThreatAnalyzer:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def analyze_threats(self, events: dict) -> str:
        """Gemini로 위협 분석"""
        prompt = f"""
        AWS 위협 데이터 분석:
        {json.dumps(events, indent=2, ensure_ascii=False)}
        
        다음을 한글로 분석:
        1. 주요 위협 패턴
        2. 우선순위 대응 조치
        3. 추가 모니터링 영역
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Fallback: 기본 통계만 제공
            return self._generate_fallback_analysis(events)
    
    def _generate_fallback_analysis(self, events: dict) -> str:
        """API 실패 시 fallback 분석"""
        ...
```

### 신규 파일: `lambda/guardian/reporters/event_exporter.py`

```python
import pandas as pd
from datetime import timedelta
from dynamodb import query_events

class EventExporter:
    def export_to_csv(self, events: list) -> str:
        """CSV로 내보내기"""
        df = pd.DataFrame(events)
        path = f"/tmp/report_{timestamp}.csv"
        df.to_csv(path, index=False)
        return path
    
    def export_to_pdf(self, events: list, summary: dict) -> str:
        """PDF로 내보내기 (fpdf2)"""
        from fpdf import FPDF
        pdf = FPDF()
        # 헤더, 테이블, 요약 추가
        path = f"/tmp/report_{timestamp}.pdf"
        pdf.output(path)
        return path
    
    def export_to_json(self, events: list) -> str:
        """JSON으로 내보내기"""
        import json
        path = f"/tmp/report_{timestamp}.json"
        with open(path, 'w') as f:
            json.dump(events, f, indent=2, default=str)
        return path
```

---

## Phase 3: 성능 및 보안 고려사항

### 성능 최적화
| 항목 | 전략 | 예상 효과 |
|------|------|---------|
| DynamoDB 쿼리 | GSI 활용 (Query vs Scan) | RCU 99% 절감 |
| 대용량 파일 | 페이지네이션 + 스트리밍 | 메모리 50% 절감 |
| Gemini API | 캐싱 (동일 요청 반복 방지) | API 호출 50% 절감 |

### 보안 고려사항
| 영역 | 위험 | 대책 |
|------|------|------|
| 명령어 파싱 | SQL injection | 정규표현식 검증 + 파라미터 바인딩 |
| 트랜잭션 | 부분 실패 | 원자성 보장 (DynamoDB TransactWriteItems) |
| API 키 | 노출 | SSM Parameter Store 저장 |
| 권한 | 무단 사용 | admin/user 역할 확인 |

---

## Gemini 협업 체크리스트

### Phase 1: 아키텍처 검증 (Gemini 리뷰 필수)
- [ ] `/remediate` 설계: 트랜잭션 안전성, 권한 검증
- [ ] `/export` 설계: 쿼리 최적화, 메모리 효율성
- [ ] `/insights` 설계: 프롬프트 품질, API 비용
- [ ] 정규표현식: 보안 (injection 방지)
- [ ] Idempotency: 재시도 안전성

### Phase 2: 구현 (Claude Code)
- [ ] telegram_bot.py 확장
- [ ] gemini_threat_analyzer.py 구현
- [ ] event_exporter.py 구현
- [ ] 의존성 설치 (pandas, fpdf2, google-generativeai)

### Phase 3: 검증 (선택적 코드 리뷰)
- [ ] 명령어 보안 테스트
- [ ] 대용량 쿼리 성능 테스트
- [ ] Gemini 프롬프트 품질 평가

---

## 환경변수 설정 (Phase 2에서)

```bash
# .env.local에 추가
GEMINI_API_KEY=<Google AI Studio에서 생성>

# SSM Parameter Store에 저장 (프로덕션)
aws ssm put-parameter \
  --name /guardian/gemini-api-key \
  --value $GEMINI_API_KEY \
  --type SecureString
```

---

## 예상 소요시간

| Phase | 작업 | 시간 |
|-------|------|------|
| 1 | Gemini 아키텍처 검증 | 30분 (비동기) |
| 2 | 구현 (telegram_bot, analyzers, reporters) | 2시간 |
| 3 | 통합 테스트 + Telegram 명령어 테스트 | 1시간 |
| **총합** | | **3.5시간** |

---

## 다음 스프린트 (Sprint 10)

**목표**: 성능 최적화 + 모니터링 강화
- Lambda 콜드 스타트 단축 (<500ms)
- CloudWatch 대시보드 확장
- 비용 추이 분석

---

## 참고 자료

- [Gemini API 문서](https://ai.google.dev/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [DynamoDB Query vs Scan](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html)
- [Lambda 함수 메모리 제한](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-package.html)
