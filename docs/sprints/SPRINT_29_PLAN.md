# Sprint 29: 실시간 알림 강화 & 고급 분석

**Status:** 📋 PLANNED  
**Target:** WebSocket 기반 실시간 알림, 고급 분석 기능, 리소스 최적화 제안

---

## Sprint 29 Overview

Sprint 28에서 달성한 병렬 처리와 ML 고도화를 기반으로, Sprint 29는 **실시간 사용자 경험** 개선과 **지능형 분석** 기능에 집중합니다.

---

## 9.1: 실시간 알림 강화

### WebSocket 기반 양방향 통신

```typescript
// lib/guardian-ws.ts
class GuardianWebSocket {
  connect(token: string) {
    this.ws = new WebSocket(`wss://api/guardian/stream?token=${token}`);
    
    this.ws.onmessage = (event) => {
      const { type, data } = JSON.parse(event.data);
      
      if (type === 'threat_detected') {
        this.notifyUser(data);
        this.playAlert();
      } else if (type === 'anomaly_score_updated') {
        this.updateDashboard(data);
      }
    };
  }
  
  disconnect() {
    this.ws?.close();
  }
}
```

### SSE (Server-Sent Events) 개선

```typescript
// api/guardian/events/stream/route.ts
export async function GET(request: Request) {
  const token = new URL(request.url).searchParams.get('token');
  
  // 토큰 검증
  if (!token) return new Response('Unauthorized', { status: 401 });
  
  const stream = new ReadableStream({
    async start(controller) {
      const interval = setInterval(async () => {
        const events = await getRecentEvents(token);
        events.forEach(event => {
          controller.enqueue(`data: ${JSON.stringify(event)}\n\n`);
        });
      }, 5000);
      
      request.signal.addEventListener('abort', () => {
        clearInterval(interval);
        controller.close();
      });
    }
  });
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive'
    }
  });
}
```

### 푸시 알림 최적화

```python
# lambda/guardian/responders/push_notifier.py
class PushNotifier:
    async def send_priority_alert(self, event):
        """우선순위별 알림 전송"""
        if event['severity'] == 'CRITICAL':
            # 즉시 전송 + 보조 채널 (SMS, 전화)
            await self.send_immediate(event)
        elif event['severity'] == 'HIGH':
            # 배치 처리 (30초)
            await self.send_batched(event, delay=30)
        else:
            # 정규 스케줄 (5분)
            await self.queue_scheduled(event, delay=300)
```

---

## 9.2: 고급 분석

### 월별 비용 추세 리포트

```python
# lambda/guardian/analytics/cost_analyzer.py
class CostAnalyzer:
    async def generate_monthly_report(self, account_id, month):
        """월별 비용 추이 분석"""
        daily_costs = await self.get_daily_costs(account_id, month)
        
        # 트렌드 분석
        trend = self._analyze_trend(daily_costs)
        
        # 이상 탐지
        anomalies = await self.detector.detect_cost_anomalies(daily_costs)
        
        # 카테고리별 분석
        breakdown = await self._get_category_breakdown(account_id, month)
        
        return {
            'month': month,
            'total_cost': sum(daily_costs),
            'daily_average': sum(daily_costs) / len(daily_costs),
            'trend': trend,
            'anomalies': anomalies,
            'breakdown': breakdown,
            'forecast_next_month': self._forecast(daily_costs)
        }
```

### 리소스 최적화 제안

```python
# lambda/guardian/analytics/optimization_suggester.py
class OptimizationSuggester:
    async def suggest_optimizations(self, findings):
        """비용 절감 최적화 제안"""
        suggestions = []
        
        # 1. 미사용 리소스 식별
        unused_resources = await self._find_unused(findings)
        for resource in unused_resources:
            suggestions.append({
                'type': 'terminate_unused',
                'resource': resource,
                'potential_savings': resource['monthly_cost'],
                'priority': 'high'
            })
        
        # 2. 오버프로비저닝 식별
        overprovisioned = await self._find_overprovisioned(findings)
        for resource in overprovisioned:
            suggestions.append({
                'type': 'downsize',
                'resource': resource,
                'potential_savings': resource['monthly_cost'] * 0.4,
                'priority': 'medium'
            })
        
        # 3. Reserved Instance 추천
        ri_opportunities = await self._find_ri_opportunities(findings)
        suggestions.extend(ri_opportunities)
        
        return sorted(suggestions, key=lambda x: x['potential_savings'], reverse=True)
```

---

## 9.3: 대시보드 고도화

### 실시간 위협 점수 표시

```tsx
// src/components/Dashboard/ThreatScoreLive.tsx
export function ThreatScoreLive() {
  const [threatScore, setThreatScore] = useState(0);
  const [isLive, setIsLive] = useState(false);
  
  useEffect(() => {
    const stream = new EventSource('/api/guardian/threats/stream');
    
    stream.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setThreatScore(data.score);
      setIsLive(true);
      
      // 1분 후 자동으로 오프라인 표시
      setTimeout(() => setIsLive(false), 60000);
    };
    
    return () => stream.close();
  }, []);
  
  return (
    <div className="threat-score">
      <div className="score-gauge">
        <svg viewBox="0 0 100 100">
          {/* 0-10 점수 게이지 */}
          <circle cx="50" cy="50" r="45" fill="none" stroke="#eee" strokeWidth="10"/>
          <circle 
            cx="50" 
            cy="50" 
            r="45" 
            fill="none" 
            stroke={getColor(threatScore)} 
            strokeWidth="10"
            strokeDasharray={`${threatScore * 14.14} 141.4`}
          />
          <text x="50" y="60" textAnchor="middle" fontSize="24" fontWeight="bold">
            {threatScore.toFixed(1)}
          </text>
        </svg>
      </div>
      <div className="status">
        {isLive ? '🟢 Live' : '⚫ Offline'}
      </div>
    </div>
  );
}
```

### 예측 분석 그래프

```tsx
// src/components/Dashboard/ForecastChart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

export function ForecastChart() {
  const [forecast, setForecast] = useState([]);
  
  useEffect(() => {
    fetch('/api/guardian/forecast')
      .then(r => r.json())
      .then(data => setForecast(data));
  }, []);
  
  return (
    <LineChart width={500} height={300} data={forecast}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="date" />
      <YAxis label={{ value: 'Cost ($)', angle: -90, position: 'insideLeft' }} />
      <Tooltip />
      <Line 
        type="monotone" 
        dataKey="actual" 
        stroke="#0070f3" 
        name="Actual Cost"
      />
      <Line 
        type="monotone" 
        dataKey="forecast" 
        stroke="#50e3c2" 
        strokeDasharray="5 5"
        name="Forecast"
      />
      <Line 
        type="monotone" 
        dataKey="upper_bound" 
        stroke="#ff6b6b" 
        strokeDasharray="3 3"
        name="Upper Bound (95%)"
      />
    </LineChart>
  );
}
```

---

## 9.4: 성능 최적화

### 알림 배칭 & 큐잉

```python
# 동일 이벤트 10초 내 반복 → 1개로 병합
notification_cache = {}
BATCH_WINDOW = 10  # seconds

async def send_notification_batched(event):
    key = f"{event['check_type']}:{event['severity']}"
    
    if key in notification_cache:
        # 이미 전송된 이벤트 → 캐시 갱신
        notification_cache[key].append(event)
    else:
        # 새 이벤트 → 즉시 전송 + 캐시
        await send_notification(event)
        notification_cache[key] = [event]
        
        # BATCH_WINDOW 후 캐시 정리
        await asyncio.sleep(BATCH_WINDOW)
        del notification_cache[key]
```

### 데이터 캐싱

```python
# Redis 캐시로 분석 결과 저장 (5분 TTL)
@cache.cached(ttl=300, key='threat_score_{account_id}')
async def get_current_threat_score(account_id):
    return await detector.analyze_threats(account_id)
```

---

## 9.5: API 엔드포인트

### 신규 엔드포인트

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/api/guardian/threats/stream` | GET | 실시간 위협 점수 SSE |
| `/api/guardian/forecast` | GET | 비용 예측 (다음 30일) |
| `/api/guardian/optimizations` | GET | 최적화 제안 |
| `/api/guardian/reports/monthly` | GET | 월별 비용 리포트 |

---

## 9.6: 테스트

### WebSocket 테스트

```typescript
// __tests__/api/guardian-ws.test.ts
describe('GuardianWebSocket', () => {
  it('connects and receives threat updates', async () => {
    const ws = new GuardianWebSocket();
    await ws.connect(token);
    
    // 위협 업데이트 수신
    const threat = await new Promise(resolve => {
      ws.onThreatUpdate = resolve;
    });
    
    expect(threat.score).toBeGreaterThan(0);
  });
});
```

### 분석 테스트

```python
# tests/test_cost_analyzer.py
@pytest.mark.asyncio
async def test_monthly_report_generation():
    analyzer = CostAnalyzer()
    report = await analyzer.generate_monthly_report('123456789', '2026-05')
    
    assert report['total_cost'] > 0
    assert report['trend'] in ['increasing', 'decreasing', 'stable']
    assert 'anomalies' in report
```

---

## 9.7: 성공 기준

✅ **실시간 알림**
- 웹소켓 연결: < 1초
- 알림 전달: < 5초 (CRITICAL)
- 배팅 효율: 90%+ (반복 이벤트)

✅ **고급 분석**
- 월별 리포트: < 10초 생성
- 최적화 제안: 정확도 > 80%
- 예측 분석: 오차율 < 10%

✅ **대시보드**
- 위협 점수 갱신: < 3초
- 그래프 렌더링: < 500ms
- 반응형 디자인

---

## 9.8: 다음 단계 (Sprint 30)

- **모바일 앱** (React Native 또는 Flutter)
- **자동 치료** (자동 격리, 자동 스케일링)
- **감사 로그** (모든 변경사항 추적)

---

**Sprint 29 준비 완료!** 🚀
