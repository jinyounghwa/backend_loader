"""
Sprint 30: WebSocket 실시간 알림 & 알림 배칭 테스트
WebSocketNotifier, NotificationBuffer, PriorityQueue, ConnectionManager
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path

os.environ["AWS_ENV"] = "localstack"
os.environ["WEBSOCKET_AUTH_TOKEN"] = "valid_token"
from guardian.responders.connection_manager import (
    ConnectionManager,
)
from guardian.responders.notification_buffer import (
    NotificationBuffer,
)
from guardian.responders.priority_queue import (
    PriorityNotificationQueue,
)
from guardian.responders.websocket_notifier import (
    WebSocketNotifier,
)


class TestWebSocketNotifier(unittest.TestCase):
    """WebSocket 알림 테스트"""

    def setUp(self):
        self.notifier = WebSocketNotifier()

    def test_connect_client_success(self):
        """클라이언트 연결 성공"""
        result = asyncio.run(self.notifier.connect_client("conn-123", "valid_token"))

        self.assertEqual(result["status"], "connected")
        self.assertEqual(result["connection_id"], "conn-123")
        self.assertIn("timestamp", result)

    def test_connect_client_invalid_token(self):
        """유효하지 않은 토큰으로 연결 실패"""
        result = asyncio.run(self.notifier.connect_client("conn-123", "invalid"))

        self.assertEqual(result["status"], "unauthorized")

    def test_disconnect_client(self):
        """클라이언트 연결 해제"""
        asyncio.run(self.notifier.connect_client("conn-123", "valid_token"))
        asyncio.run(self.notifier.disconnect_client("conn-123"))

        self.assertNotIn("conn-123", self.notifier.connections)

    def test_broadcast_threat_update(self):
        """위협 점수 브로드캐스트"""
        asyncio.run(self.notifier.connect_client("conn-1", "valid_token"))
        asyncio.run(self.notifier.connect_client("conn-2", "valid_token"))

        result = asyncio.run(self.notifier.broadcast_threat_update(7.5, "HIGH"))

        self.assertEqual(result["status"], "broadcasted")
        self.assertEqual(result["recipients"], 2)
        self.assertEqual(result["message"]["score"], 7.5)
        self.assertEqual(result["message"]["severity"], "HIGH")

    def test_send_anomaly_alert(self):
        """이상 탐지 알림"""
        asyncio.run(self.notifier.connect_client("conn-123", "valid_token"))

        result = asyncio.run(
            self.notifier.send_anomaly_alert(
                "conn-123", "cost", {"daily_cost": 150.0, "threshold": 100.0}
            )
        )

        self.assertEqual(result["status"], "sent")

    def test_handle_client_subscribe(self):
        """클라이언트 구독 처리"""
        asyncio.run(self.notifier.connect_client("conn-123", "valid_token"))

        result = asyncio.run(
            self.notifier.handle_client_message(
                "conn-123", {"action": "subscribe", "event_types": ["threat", "anomaly"]}
            )
        )

        self.assertEqual(result["status"], "subscribed")
        self.assertEqual(result["event_types"], ["threat", "anomaly"])

    def test_get_active_connections(self):
        """활성 연결 수"""
        asyncio.run(self.notifier.connect_client("conn-1", "valid_token"))
        asyncio.run(self.notifier.connect_client("conn-2", "valid_token"))

        self.assertEqual(self.notifier.get_active_connections(), 2)


class TestNotificationBuffer(unittest.TestCase):
    """알림 배칭 버퍼 테스트"""

    def setUp(self):
        self.buffer = NotificationBuffer(batch_window=1)

    def test_add_single_event(self):
        """단일 이벤트 추가"""
        result = asyncio.run(
            self.buffer.add_event({"check_type": "EC2", "severity": "HIGH", "instance_id": "i-123"})
        )

        self.assertEqual(result["status"], "buffered")
        self.assertEqual(result["buffered_count"], 1)

    def test_batch_same_events(self):
        """동일 이벤트 배칭"""
        # 5개 동일 이벤트 추가
        for i in range(5):
            asyncio.run(
                self.buffer.add_event(
                    {"check_type": "EC2", "severity": "HIGH", "instance_id": f"i-{i}"}
                )
            )

        # 모두 같은 키로 배치됨
        self.assertEqual(len(self.buffer.buffer), 1)
        self.assertEqual(len(self.buffer.buffer["EC2:HIGH"]), 5)

    def test_different_events_separate_batches(self):
        """서로 다른 이벤트는 별도 배치"""
        asyncio.run(self.buffer.add_event({"check_type": "EC2", "severity": "HIGH"}))
        asyncio.run(self.buffer.add_event({"check_type": "S3", "severity": "MEDIUM"}))

        self.assertEqual(len(self.buffer.buffer), 2)

    def test_flush_key(self):
        """키별 flush"""
        asyncio.run(
            self.buffer.add_event({"check_type": "EC2", "severity": "HIGH", "instance_id": "i-1"})
        )
        asyncio.run(
            self.buffer.add_event({"check_type": "EC2", "severity": "HIGH", "instance_id": "i-2"})
        )

        result = asyncio.run(self.buffer.flush_key("EC2:HIGH"))

        self.assertEqual(result["status"], "flushed")
        self.assertEqual(result["message_count"], 2)
        self.assertEqual(result["message"]["type"], "batched_events")
        self.assertEqual(result["message"]["count"], 2)

    def test_force_flush_all(self):
        """모든 버퍼 강제 flush"""
        asyncio.run(self.buffer.add_event({"check_type": "EC2", "severity": "HIGH"}))
        asyncio.run(self.buffer.add_event({"check_type": "S3", "severity": "MEDIUM"}))

        messages = asyncio.run(self.buffer.force_flush_all())

        self.assertEqual(len(messages), 2)
        self.assertEqual(len(self.buffer.buffer), 0)

    def test_get_buffer_stats(self):
        """버퍼 통계"""
        for _ in range(3):
            asyncio.run(self.buffer.add_event({"check_type": "EC2", "severity": "HIGH"}))

        stats = self.buffer.get_buffer_stats()

        self.assertEqual(stats["total_events_processed"], 3)
        self.assertEqual(stats["current_pending_events"], 3)


class TestPriorityNotificationQueue(unittest.TestCase):
    """우선순위 큐 테스트"""

    def setUp(self):
        self.queue = PriorityNotificationQueue(max_batch_size=10)

    def test_enqueue_notification(self):
        """알림 큐 추가"""
        result = self.queue.enqueue({"severity": "HIGH", "message": "Test alert"})

        self.assertEqual(result["status"], "enqueued")
        self.assertEqual(result["severity"], "HIGH")
        self.assertEqual(self.queue.size(), 1)

    def test_priority_ordering(self):
        """우선순위 순서"""
        # LOW, CRITICAL, MEDIUM 순서로 추가
        self.queue.enqueue({"severity": "LOW", "id": 1})
        self.queue.enqueue({"severity": "CRITICAL", "id": 2})
        self.queue.enqueue({"severity": "MEDIUM", "id": 3})

        # CRITICAL 먼저 나와야 함
        first = self.queue.dequeue()
        self.assertEqual(first["severity"], "CRITICAL")

        second = self.queue.dequeue()
        self.assertEqual(second["severity"], "MEDIUM")

        third = self.queue.dequeue()
        self.assertEqual(third["severity"], "LOW")

    def test_dequeue_batch(self):
        """배치 추출"""
        for i in range(5):
            self.queue.enqueue({"severity": "HIGH", "id": i})

        batch = self.queue.dequeue_batch(size=3)

        self.assertEqual(len(batch), 3)
        self.assertEqual(self.queue.size(), 2)

    def test_peek_notification(self):
        """최상위 알림 조회"""
        self.queue.enqueue({"severity": "HIGH", "id": 1})
        self.queue.enqueue({"severity": "CRITICAL", "id": 2})

        peeked = self.queue.peek()
        self.assertEqual(peeked["id"], 2)  # CRITICAL이 최상위
        self.assertEqual(self.queue.size(), 2)  # 크기 변화 없음

    def test_get_stats(self):
        """큐 통계"""
        self.queue.enqueue({"severity": "CRITICAL"})
        self.queue.enqueue({"severity": "HIGH"})
        self.queue.enqueue({"severity": "HIGH"})

        stats = self.queue.get_stats()

        self.assertEqual(stats["current_queue_size"], 3)
        self.assertEqual(stats["by_severity"]["CRITICAL"], 1)
        self.assertEqual(stats["by_severity"]["HIGH"], 2)


class TestConnectionManager(unittest.TestCase):
    """연결 관리자 테스트"""

    def setUp(self):
        self.manager = ConnectionManager(ttl_seconds=10)

    def test_add_connection(self):
        """연결 추가"""
        result = asyncio.run(self.manager.add_connection("conn-123", "user-456"))

        self.assertEqual(result["status"], "added")
        self.assertEqual(result["conn_id"], "conn-123")

    def test_remove_connection(self):
        """연결 제거"""
        asyncio.run(self.manager.add_connection("conn-123", "user-456"))
        result = asyncio.run(self.manager.remove_connection("conn-123"))

        self.assertEqual(result["status"], "removed")
        self.assertNotIn("conn-123", self.manager.connections)

    def test_heartbeat(self):
        """하트비트"""
        asyncio.run(self.manager.add_connection("conn-123", "user-456"))

        result = asyncio.run(self.manager.heartbeat("conn-123"))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["heartbeat_count"], 1)

    def test_is_connection_alive(self):
        """연결 상태 확인"""
        asyncio.run(self.manager.add_connection("conn-123", "user-456"))

        self.assertTrue(self.manager.is_connection_alive("conn-123"))

    def test_get_connection_info(self):
        """연결 정보 조회"""
        asyncio.run(self.manager.add_connection("conn-123", "user-456"))

        info = self.manager.get_connection_info("conn-123")

        self.assertEqual(info["conn_id"], "conn-123")
        self.assertEqual(info["user_id"], "user-456")
        self.assertTrue(info["is_alive"])

    def test_get_connections_by_user(self):
        """사용자별 연결 조회"""
        asyncio.run(self.manager.add_connection("conn-1", "user-456"))
        asyncio.run(self.manager.add_connection("conn-2", "user-456"))
        asyncio.run(self.manager.add_connection("conn-3", "user-789"))

        connections = self.manager.get_connections_by_user("user-456")

        self.assertEqual(len(connections), 2)

    def test_get_stats(self):
        """연결 통계"""
        asyncio.run(self.manager.add_connection("conn-1", "user-1"))
        asyncio.run(self.manager.add_connection("conn-2", "user-2"))

        stats = self.manager.get_stats()

        self.assertEqual(stats["current_active"], 2)
        self.assertEqual(stats["total_added"], 2)


if __name__ == "__main__":
    unittest.main()
