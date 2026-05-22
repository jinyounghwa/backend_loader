# Sprint 30: WebSocket 실시간 알림 & 대시보드 UI 개선

**Status:** 📋 PLANNED  
**Target:** WebSocket 양방향 통신, 실시간 위협 점수 UI, 알림 배칭 & 큐잉

---

## Sprint 30 Overview

Sprint 29에서 달성한 지능형 비용 분석과 리소스 최적화 제안을 기반으로, Sprint 30은 **실시간 사용자 경험** 개선과 **알림 시스템 최적화**에 집중합니다.

---

## 10.1: WebSocket 실시간 알림

### WebSocket 기반 양방향 통신

```python
# lambda/guardian/responders/websocket_notifier.py
class WebSocketNotifier:
    """WebSocket을 통한 실시간 양방향 알림"""
    
    async def connect_client(self, connection_id, auth_token):
        """클라이언트 연결"""
        session = await self._validate_auth(auth_token)
        await self._store_connection(connection_id, session)
        return {"status": "connected"}
    
    async def broadcast_threat_update(self, threat_score, severity):
        """모든 클라이언트에게 위협 점수 브로드캐스트"""
        message = {
            "type": "threat_detected",
            "score": threat_score,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        connections = await self._get_active_connections()
        for conn_id in connections:
            await self._send_to_connection(conn_id, message)
    
    async def disconnect_client(self, connection_id):
        """클라이언트 연결 해제"""
        await self._remove_connection(connection_id)
```

### API Gateway WebSocket 통합

```python
# lambda/guardian/handlers/websocket_handler.py
async def handle_websocket_connect(event, context):
    """$connect 라우트"""
    connection_id = event["requestContext"]["connectionId"]
    auth_token = event.get("queryStringParameters", {}).get("token")
    
    result = await ws_notifier.connect_client(connection_id, auth_token)
    return {"statusCode": 200, "body": json.dumps(result)}

async def handle_websocket_disconnect(event, context):
    """$disconnect 라우트"""
    connection_id = event["requestContext"]["connectionId"]
    await ws_notifier.disconnect_client(connection_id)
    return {"statusCode": 200}

async def handle_websocket_default(event, context):
    """$default 라우트 - 클라이언트 메시지 수신"""
    connection_id = event["requestContext"]["connectionId"]
    body = json.loads(event.get("body", "{}"))
    
    # 클라이언트의 요청 처리 (예: 필터 설정, 구독 변경)
    await ws_notifier.handle_client_message(connection_id, body)
    return {"statusCode": 200}
```

---

## 10.2: 실시간 위협 점수 대시보드 UI

### 위협 게이지 컴포넌트

```typescript
// src/components/Dashboard/ThreatGauge.tsx
import { useEffect, useState } from 'react';

export function ThreatGauge() {
  const [threatScore, setThreatScore] = useState<number>(0);
  const [isLive, setIsLive] = useState<boolean>(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;
    const token = localStorage.getItem('auth_token');
    
    // WebSocket 연결
    const connectWebSocket = () => {
      ws = new WebSocket(
        `wss://${process.env.REACT_APP_API_GATEWAY_ENDPOINT}/prod?token=${token}`
      );
      
      ws.onopen = () => {
        setIsLive(true);
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'threat_detected') {
          setThreatScore(data.score);
          setLastUpdate(new Date(data.timestamp));
          
          // 높은 위협 → 시각 피드백
          if (data.score > 7) {
            playAlertSound();
          }
        }
      };
      
      ws.onclose = () => {
        setIsLive(false);
        // 5초 후 재연결 시도
        setTimeout(connectWebSocket, 5000);
      };
    };
    
    connectWebSocket();
    
    return () => {
      if (ws) ws.close();
    };
  }, []);

  const getGaugeColor = (score: number): string => {
    if (score < 3) return '#10b981'; // 녹색
    if (score < 5) return '#f59e0b'; // 주황색
    if (score < 7) return '#ef4444'; // 빨강색
    return '#dc2626'; // 진빨강
  };

  return (
    <div className="threat-gauge-container">
      <div className="gauge-wrapper">
        <svg viewBox="0 0 100 100" className="gauge">
          {/* 배경 원 */}
          <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" strokeWidth="8" />
          
          {/* 위협 점수 원호 */}
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke={getGaugeColor(threatScore)}
            strokeWidth="8"
            strokeDasharray={`${threatScore * 14.14} 282.8`}
            transform="rotate(-90 50 50)"
            className="gauge-fill"
          />
          
          {/* 중앙 텍스트 */}
          <text x="50" y="50" textAnchor="middle" dominantBaseline="central" className="gauge-text">
            {threatScore.toFixed(1)}
          </text>
          <text x="50" y="65" textAnchor="middle" fontSize="10" fill="#666">
            / 10
          </text>
        </svg>
      </div>

      <div className="gauge-info">
        <div className="status-badge">
          {isLive ? (
            <>
              <span className="status-indicator live" />
              🟢 Live
            </>
          ) : (
            <>
              <span className="status-indicator offline" />
              ⚫ Reconnecting...
            </>
          )}
        </div>
        
        {lastUpdate && (
          <div className="last-update">
            Updated {Math.round((Date.now() - lastUpdate.getTime()) / 1000)}s ago
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## 10.3: 알림 배칭 & 큐잉 시스템

### 알림 버퍼 관리

```python
# lambda/guardian/responders/notification_buffer.py
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import asyncio

class NotificationBuffer:
    """동일 이벤트 병합 및 배칭"""
    
    def __init__(self, batch_window: int = 10):
        """
        Args:
            batch_window: 배칭 윈도우 (초)
        """
        self.batch_window = batch_window
        self.buffer: Dict[str, List[Dict]] = defaultdict(list)
        self.pending_flushes: Dict[str, asyncio.Task] = {}
    
    def _get_event_key(self, event: Dict[str, Any]) -> str:
        """이벤트 고유키 생성"""
        return f"{event['check_type']}:{event['severity']}"
    
    async def add_event(self, event: Dict[str, Any]) -> None:
        """이벤트 버퍼에 추가"""
        key = self._get_event_key(event)
        self.buffer[key].append(event)
        
        # 이미 flush 예약된 경우 스킵
        if key in self.pending_flushes:
            return
        
        # batch_window 후 flush 예약
        task = asyncio.create_task(self._flush_after_delay(key))
        self.pending_flushes[key] = task
    
    async def _flush_after_delay(self, key: str) -> None:
        """배칭 윈도우 후 알림 전송"""
        await asyncio.sleep(self.batch_window)
        await self.flush_key(key)
    
    async def flush_key(self, key: str) -> None:
        """특정 키의 버퍼 비우기"""
        if key not in self.buffer or not self.buffer[key]:
            return
        
        events = self.buffer[key]
        count = len(events)
        
        # 합성 메시지
        message = self._create_batched_message(events, count)
        
        # 전송
        await send_notification(message)
        
        # 정리
        del self.buffer[key]
        if key in self.pending_flushes:
            del self.pending_flushes[key]
    
    def _create_batched_message(self, events: List[Dict], count: int) -> Dict:
        """여러 이벤트를 하나의 메시지로 병합"""
        if count == 1:
            return events[0]
        
        return {
            "type": "batched_events",
            "count": count,
            "check_type": events[0]["check_type"],
            "severity": events[0]["severity"],
            "first_event_time": events[0]["timestamp"],
            "last_event_time": events[-1]["timestamp"],
            "summary": f"{count}개의 동일한 {events[0]['severity']} 이벤트 감지",
            "events": events
        }
    
    async def force_flush_all(self) -> None:
        """모든 버퍼 강제 비우기"""
        keys = list(self.buffer.keys())
        for key in keys:
            await self.flush_key(key)

# 글로벌 버퍼 인스턴스
_notification_buffer = NotificationBuffer(batch_window=10)

async def add_notification_event(event: Dict[str, Any]) -> None:
    """알림 이벤트 추가"""
    await _notification_buffer.add_event(event)

async def force_flush_notifications() -> None:
    """모든 대기 중인 알림 즉시 전송"""
    await _notification_buffer.force_flush_all()
```

### 우선순위 큐

```python
# lambda/guardian/responders/notification_queue.py
import heapq
from typing import Tuple

class PriorityNotificationQueue:
    """우선순위 기반 알림 큐"""
    
    PRIORITY_MAP = {
        "CRITICAL": 1,
        "HIGH": 2,
        "MEDIUM": 3,
        "LOW": 4
    }
    
    def __init__(self, max_batch_size: int = 50):
        self.queue: List[Tuple[int, Dict]] = []
        self.max_batch_size = max_batch_size
    
    def enqueue(self, notification: Dict[str, Any]) -> None:
        """알림을 우선순위에 따라 큐에 추가"""
        severity = notification.get("severity", "LOW")
        priority = self.PRIORITY_MAP.get(severity, 4)
        
        heapq.heappush(self.queue, (priority, notification))
    
    def dequeue_batch(self, size: int = None) -> List[Dict]:
        """우선순위 순으로 배치 추출"""
        batch_size = size or self.max_batch_size
        batch = []
        
        for _ in range(min(batch_size, len(self.queue))):
            _, notification = heapq.heappop(self.queue)
            batch.append(notification)
        
        return batch
    
    def size(self) -> int:
        """큐 크기"""
        return len(self.queue)
```

---

## 10.4: 대시보드 UI 개선

### 실시간 메트릭 카드

```typescript
// src/components/Dashboard/MetricsCard.tsx
export interface MetricData {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'stable';
  trendPercent?: number;
  color?: 'success' | 'warning' | 'danger';
}

export function MetricsCard({ data }: { data: MetricData }) {
  const getTrendIcon = () => {
    switch (data.trend) {
      case 'up':
        return '📈';
      case 'down':
        return '📉';
      default:
        return '→';
    }
  };

  return (
    <div className={`metric-card metric-${data.color || 'default'}`}>
      <div className="metric-label">{data.label}</div>
      <div className="metric-value">{data.value}</div>
      
      {data.trend && (
        <div className="metric-trend">
          {getTrendIcon()} {data.trendPercent?.toFixed(1)}%
        </div>
      )}
    </div>
  );
}
```

### 실시간 로그 스트림

```typescript
// src/components/Dashboard/EventStream.tsx
export function EventStream() {
  const [events, setEvents] = useState<Event[]>([]);
  const [filter, setFilter] = useState<'all' | 'critical' | 'high'>('all');

  useEffect(() => {
    let eventSource: EventSource | null = null;
    const token = localStorage.getItem('auth_token');

    const connectSSE = () => {
      eventSource = new EventSource(
        `/api/guardian/events/stream?token=${token}&filter=${filter}`
      );

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setEvents(prev => [data, ...prev.slice(0, 99)]);
      };

      eventSource.onerror = () => {
        eventSource?.close();
        setTimeout(connectSSE, 5000);
      };
    };

    connectSSE();

    return () => {
      eventSource?.close();
    };
  }, [filter]);

  return (
    <div className="event-stream">
      <div className="filter-buttons">
        <button
          onClick={() => setFilter('all')}
          className={filter === 'all' ? 'active' : ''}
        >
          All Events
        </button>
        <button
          onClick={() => setFilter('critical')}
          className={filter === 'critical' ? 'active' : ''}
        >
          Critical Only
        </button>
        <button
          onClick={() => setFilter('high')}
          className={filter === 'high' ? 'active' : ''}
        >
          High & Above
        </button>
      </div>

      <div className="events-list">
        {events.map((event, idx) => (
          <EventCard key={idx} event={event} />
        ))}
      </div>
    </div>
  );
}
```

---

## 10.5: 성능 최적화

### WebSocket 메시지 압축

```python
# lambda/guardian/responders/ws_compression.py
import gzip
import json

def compress_message(message: Dict[str, Any]) -> bytes:
    """메시지를 gzip으로 압축"""
    json_str = json.dumps(message)
    return gzip.compress(json_str.encode())

def decompress_message(compressed: bytes) -> Dict[str, Any]:
    """압축된 메시지 해제"""
    json_str = gzip.decompress(compressed).decode()
    return json.loads(json_str)
```

### 연결 상태 관리

```python
# lambda/guardian/responders/connection_manager.py
class ConnectionManager:
    """WebSocket 연결 생명주기 관리"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.connections: Dict[str, Dict] = {}
        self.ttl = ttl_seconds
    
    async def add_connection(self, conn_id: str, user_id: str) -> None:
        """연결 추가"""
        self.connections[conn_id] = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "last_heartbeat": datetime.now(timezone.utc)
        }
    
    async def heartbeat(self, conn_id: str) -> None:
        """하트비트 갱신"""
        if conn_id in self.connections:
            self.connections[conn_id]["last_heartbeat"] = datetime.now(timezone.utc)
    
    async def cleanup_stale_connections(self) -> int:
        """만료된 연결 정리"""
        now = datetime.now(timezone.utc)
        stale = [
            conn_id for conn_id, meta in self.connections.items()
            if (now - meta["last_heartbeat"]).total_seconds() > self.ttl
        ]
        
        for conn_id in stale:
            del self.connections[conn_id]
        
        return len(stale)
```

---

## 10.6: 테스트 전략

### WebSocket 테스트

```python
# tests/lambda/test_websocket.py
@pytest.mark.asyncio
async def test_websocket_connect():
    """WebSocket 연결"""
    notifier = WebSocketNotifier()
    result = await notifier.connect_client("conn-123", valid_token)
    
    assert result["status"] == "connected"

@pytest.mark.asyncio
async def test_broadcast_threat_update():
    """위협 점수 브로드캐스트"""
    notifier = WebSocketNotifier()
    
    # 2개 클라이언트 연결
    await notifier.connect_client("conn-1", token1)
    await notifier.connect_client("conn-2", token2)
    
    # 브로드캐스트
    await notifier.broadcast_threat_update(7.5, "HIGH")
    
    # 메시지 수신 확인
    messages = await get_broadcast_messages()
    assert len(messages) == 2

@pytest.mark.asyncio
async def test_notification_batching():
    """알림 배칭"""
    buffer = NotificationBuffer(batch_window=1)
    
    # 5개 동일 이벤트 추가
    for i in range(5):
        await buffer.add_event({
            "check_type": "EC2",
            "severity": "HIGH",
            "instance_id": f"i-{i}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    # 배칭 윈도우 대기
    await asyncio.sleep(1.5)
    
    # 1개 배치된 메시지로 전송됨
    sent = await get_sent_notifications()
    assert len(sent) == 1
    assert sent[0]["count"] == 5
```

---

## 10.7: 성공 기준

✅ **WebSocket 실시간 알림**
- 연결 수립: < 1초
- 메시지 전달: < 500ms
- 동시 연결: 1000+ 지원
- 배칭 효율: 90%+ (반복 이벤트)

✅ **대시보드 UI**
- 위협 점수 갱신: < 1초
- 메트릭 렌더링: < 300ms
- 이벤트 스트림: < 500ms
- 반응형 디자인 (모바일/태블릿)

✅ **알림 시스템**
- 버퍼링: 동일 이벤트 90% 이상 병합
- 큐잉: 우선순위 순서 보장
- 메모리: 1000+ 알림 안정적 관리

---

## 10.8: 다음 단계 (Sprint 31)

- **모바일 앱** (React Native 또는 Flutter)
- **자동 치료** (자동 격리, 자동 스케일링)
- **감사 로그** (모든 변경사항 추적)
- **다중 계정 지원**

---

**Sprint 30 준비 완료!** 🚀

AWS Guardian의 실시간 알림 시스템이 완성됩니다.
