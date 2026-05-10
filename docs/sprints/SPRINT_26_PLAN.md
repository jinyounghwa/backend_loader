# Sprint 26: 대시보드 UI & ML 위협 감지

**Status:** 📋 PLANNED  
**Target:** 웹 대시보드 UI 완성, ML 기반 위협 감지, 고급 알림 기능

---

## Sprint 26 Overview

Sprint 25에서 구축한 API를 기반으로 완전한 대시보드 UI를 개발하고, ML 기반 위협 탐지 알고리즘 구현:

1. **대시보드 UI** - React 컴포넌트 (Status, Events, Actions)
2. **실시간 업데이트** - WebSocket 또는 SSE
3. **ML 위협 감지** - 이상 탐지 알고리즘
4. **고급 알림** - Slack, PagerDuty 통합

---

## 6.1: 대시보드 UI 개발

### 페이지 구조

**`/dashboard` - 메인 대시보드**
```
┌─────────────────────────────────┐
│ AWS Guardian Dashboard          │
├─────────────────────────────────┤
│ Health Status                   │
│ ┌────────┬────────┬────────┐   │
│ │  EC2   │   S3   │  Cost  │   │
│ │Healthy │Healthy │ Alert  │   │
│ └────────┴────────┴────────┘   │
├─────────────────────────────────┤
│ Recent Events (Last 10)         │
│ ┌────────────────────────────┐  │
│ │ HIGH | Cost | $15.50 | 1h  │  │
│ │ INFO | EC2  | Secure | 2h  │  │
│ └────────────────────────────┘  │
├─────────────────────────────────┤
│ Quick Actions                   │
│ [Stop Instance] [Block Bucket]  │
└─────────────────────────────────┘
```

### 핵심 컴포넌트

```tsx
// components/StatusCard.tsx
<StatusCard 
  title="EC2"
  status="healthy"
  stats={{
    total: 8,
    running: 6,
    issues: 0
  }}
/>

// components/EventLog.tsx
<EventLog
  events={events}
  onFilter={handleFilter}
/>

// components/ActionHistory.tsx
<ActionHistory
  limit={10}
/>
```

---

## 6.2: 실시간 업데이트

### WebSocket 구현

```ts
// lib/guardian-ws.ts
class GuardianWebSocket {
  connect() {
    this.ws = new WebSocket('wss://api/guardian/events/stream');
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.notifyListeners(data);
    };
  }
}
```

### 또는 SSE (Server-Sent Events)

```ts
// api/guardian/events/stream/route.ts
export async function GET() {
  const stream = new ReadableStream({
    start(controller) {
      const interval = setInterval(() => {
        controller.enqueue(`data: ${JSON.stringify(event)}\n\n`);
      }, 5000);
    }
  });
  return new Response(stream);
}
```

---

## 6.3: ML 위협 감지

### 이상 탐지 알고리즘

```python
# lambda/guardian/ml/anomaly_detector.py
import numpy as np
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1)
        self.baseline = {}
    
    async def detect(self, metrics):
        """
        metrics: {
            'daily_cost': 15.5,
            'api_calls': 1200,
            'error_rate': 0.02,
            'instance_count': 8
        }
        """
        X = self.prepare_features(metrics)
        score = self.model.decision_function(X)[0]
        
        if score < -0.5:  # 이상
            return {
                'is_anomaly': True,
                'confidence': abs(score),
                'reason': self.explain_anomaly(metrics)
            }
        return {'is_anomaly': False}
```

### 위협 점수 계산

```python
def calculate_threat_score(findings):
    """
    0-10 점수
    - 공개 S3 버킷: 3점
    - 비인가 리전 EC2: 2점
    - 높은 비용 증가: 1점
    - 비정상 API 활동: 2점
    """
    score = 0
    if findings['public_buckets'] > 0:
        score += 3
    if findings['unauthorized_regions'] > 0:
        score += 2
    if findings['cost_spike']:
        score += 1
    if findings['anomalous_api_activity']:
        score += 2
    
    return min(10, score)
```

---

## 6.4: 고급 알림

### Slack 통합

```python
# lambda/guardian/responders/slack.py
class SlackResponder:
    async def send_alert(self, event):
        """Send alert to Slack channel"""
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        payload = {
            'text': f"🚨 {event['severity']} Alert",
            'attachments': [{
                'color': self.get_color(event['severity']),
                'title': event['title'],
                'text': event['message'],
                'fields': [
                    {'title': 'Check', 'value': event['check_type']},
                    {'title': 'Time', 'value': event['timestamp']}
                ]
            }]
        }
        await requests.post(webhook_url, json=payload)
```

### PagerDuty 통합

```python
# lambda/guardian/responders/pagerduty.py
class PagerDutyResponder:
    async def create_incident(self, event):
        """Create PagerDuty incident for critical events"""
        if event['severity'] != 'CRITICAL':
            return
        
        incident = {
            'type': 'incident',
            'title': event['title'],
            'service': {'id': self.service_id, 'type': 'service_reference'},
            'urgency': 'high',
            'body': {
                'type': 'incident_body',
                'details': event['message']
            }
        }
        await self.pagerduty_client.create(incident)
```

---

## 6.5: 성능 최적화

### 캐시 전략

```python
# 1시간 캐시
@cache.cached(ttl=3600)
def get_ec2_status():
    return fetch_ec2_data()

# 5분 캐시
@cache.cached(ttl=300)
def get_cost_data():
    return fetch_cost_data()

# 캐시 없음 (실시간)
def get_recent_events():
    return fetch_events()
```

### 데이터베이스 최적화

```sql
-- 인덱스 추가
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_severity ON events(severity);
CREATE INDEX idx_events_check_type ON events(check_type);

-- 파티셔닝
ALTER TABLE events 
PARTITION BY RANGE (YEAR(timestamp)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026)
);
```

---

## 6.6: 테스트

### UI 컴포넌트 테스트

```tsx
// __tests__/components/StatusCard.test.tsx
describe('StatusCard', () => {
  it('displays health status correctly', () => {
    const { getByText } = render(
      <StatusCard status="healthy" title="EC2" />
    );
    expect(getByText('healthy')).toBeInTheDocument();
  });
});
```

### API 통합 테스트

```python
# tests/test_guardian_api.py
@pytest.mark.asyncio
async def test_status_api():
    response = await client.get('/api/guardian/status')
    assert response.status_code == 200
    assert 'ec2' in response.json()
```

---

## 6.7: 배포

### Next.js 배포

```bash
# Vercel 배포
vercel deploy

# 또는 AWS Amplify
amplify publish
```

### Lambda 업데이트

```bash
# ML 모델 배포
sam deploy -t sam-ml.yaml

# 환경 변수 업데이트
aws lambda update-function-configuration \
  --function-name guardianML \
  --environment Variables='{
    "MODEL_BUCKET":"s3://guardian-models",
    "SLACK_WEBHOOK_URL":"https://hooks.slack.com/..."
  }'
```

---

## 6.8: 성공 기준

✅ **대시보드**
- 상태 페이지 로드 < 1초
- 이벤트 로그 실시간 업데이트
- 반응형 디자인 (모바일 포함)

✅ **ML 감지**
- 이상 탐지 정확도 > 80%
- 오탐율 < 5%
- 실시간 위협 점수 계산

✅ **알림**
- Slack 메시지 전달 < 10초
- PagerDuty 인시던트 생성 < 5초

---

## 6.9: 다음 단계 (Sprint 27)

- 모바일 앱 (React Native)
- 고급 보고서 (PDF 생성)
- 자동 치료 (자동 격리)
- 대규모 환경 지원 (1000+ 리소스)

---

**Sprint 26 준비 완료!** 🚀
