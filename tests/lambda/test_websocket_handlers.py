"""
Sprint 30 Phase 2: WebSocket 핸들러 & 메시지 압축 테스트
"""

import asyncio
import json
import os
import sys
import unittest
from pathlib import Path

os.environ["AWS_ENV"] = "localstack"
os.environ["WEBSOCKET_AUTH_TOKEN"] = "valid_token"
from guardian.handlers.websocket_handler import (
    handle_anomaly_alert,
    handle_connect,
    handle_connection_stats,
    handle_default,
    handle_disconnect,
    handle_threat_broadcast,
)
from guardian.responders.ws_compression import (
    WebSocketMessageCompressor,
    compress_message,
    decompress_message,
    get_compression_stats,
)


class TestWebSocketHandlers(unittest.TestCase):
    """WebSocket 핸들러 테스트"""

    def create_event(
        self,
        connection_id: str = "conn-123",
        token: str = "valid_token",
        body: dict = None,
        route: str = "connect",
    ) -> dict:
        """테스트용 Lambda 이벤트 생성"""
        event = {
            "requestContext": {"connectionId": connection_id, "routeKey": route, "stage": "prod"},
            "queryStringParameters": {"token": token} if route == "connect" else None,
            "body": json.dumps(body) if body else None,
        }
        return event

    def test_handle_connect_success(self):
        """연결 성공"""
        event = self.create_event()
        result = asyncio.run(handle_connect(event, None))

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "connected")
        self.assertEqual(body["connection_id"], "conn-123")

    def test_handle_connect_missing_token(self):
        """토큰 누락"""
        event = {"requestContext": {"connectionId": "conn-123"}, "queryStringParameters": None}
        result = asyncio.run(handle_connect(event, None))

        self.assertEqual(result["statusCode"], 401)

    def test_handle_connect_invalid_token(self):
        """유효하지 않은 토큰"""
        event = self.create_event(token="invalid")
        result = asyncio.run(handle_connect(event, None))

        self.assertEqual(result["statusCode"], 401)

    def test_handle_disconnect(self):
        """연결 해제"""
        # 먼저 연결
        connect_event = self.create_event()
        asyncio.run(handle_connect(connect_event, None))

        # 연결 해제
        disconnect_event = {"requestContext": {"connectionId": "conn-123"}}
        result = asyncio.run(handle_disconnect(disconnect_event, None))

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "disconnected")

    def test_handle_default_subscribe(self):
        """구독 메시지 처리"""
        # 먼저 연결
        connect_event = self.create_event()
        asyncio.run(handle_connect(connect_event, None))

        # 구독 메시지
        default_event = {
            "requestContext": {"connectionId": "conn-123"},
            "body": json.dumps({"action": "subscribe", "event_types": ["threat", "anomaly"]}),
        }
        result = asyncio.run(handle_default(default_event, None))

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "subscribed")

    def test_handle_default_ping(self):
        """핑 메시지 처리"""
        # 먼저 연결
        connect_event = self.create_event()
        asyncio.run(handle_connect(connect_event, None))

        # 핑 메시지
        default_event = {
            "requestContext": {"connectionId": "conn-123"},
            "body": json.dumps({"action": "ping"}),
        }
        result = asyncio.run(handle_default(default_event, None))

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "pong")

    def test_handle_default_invalid_json(self):
        """유효하지 않은 JSON"""
        default_event = {"requestContext": {"connectionId": "conn-123"}, "body": "invalid json"}
        result = asyncio.run(handle_default(default_event, None))

        self.assertEqual(result["statusCode"], 400)

    def test_handle_threat_broadcast(self):
        """위협 점수 브로드캐스트"""
        event = {"body": json.dumps({"threat_score": 7.5, "severity": "HIGH"})}
        result = asyncio.run(handle_threat_broadcast(event, None))

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "broadcasted")
        self.assertEqual(body["message"]["score"], 7.5)

    def test_handle_threat_broadcast_invalid_score(self):
        """유효하지 않은 위협 점수"""
        event = {"body": json.dumps({"threat_score": 15, "severity": "HIGH"})}  # > 10
        result = asyncio.run(handle_threat_broadcast(event, None))

        self.assertEqual(result["statusCode"], 400)

    def test_handle_anomaly_alert(self):
        """이상 탐지 알림"""
        # 먼저 연결
        connect_event = self.create_event()
        asyncio.run(handle_connect(connect_event, None))

        # 이상 탐지 알림
        event = {
            "body": json.dumps(
                {
                    "connection_id": "conn-123",
                    "anomaly_type": "cost",
                    "details": {"daily_cost": 150.0, "threshold": 100.0},
                }
            )
        }
        result = asyncio.run(handle_anomaly_alert(event, None))

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["status"], "sent")

    def test_handle_connection_stats(self):
        """연결 통계 조회"""
        # 연결 추가
        connect_event = self.create_event()
        asyncio.run(handle_connect(connect_event, None))

        # 통계 조회
        event = {}
        result = asyncio.run(handle_connection_stats(event, None))

        self.assertEqual(result["statusCode"], 200)
        stats = json.loads(result["body"])
        self.assertIn("ws_notifier", stats)
        self.assertIn("conn_manager", stats)
        self.assertIn("notification_buffer", stats)


class TestWebSocketMessageCompression(unittest.TestCase):
    """WebSocket 메시지 압축 테스트"""

    def setUp(self):
        self.compressor = WebSocketMessageCompressor(
            compression_enabled=True, min_size_bytes=100  # 테스트용 작은 크기
        )

    def test_compress_small_message(self):
        """작은 메시지는 압축하지 않음"""
        message = {"type": "ping"}

        result = self.compressor.compress_message(message)

        self.assertEqual(result["type"], "uncompressed")
        self.assertIn("data", result)

    def test_compress_large_message(self):
        """큰 메시지 압축"""
        message = {"type": "bulk_data", "data": "x" * 10000}  # 10KB

        result = self.compressor.compress_message(message)

        # 큰 메시지는 압축됨
        if result["type"] == "compressed":
            self.assertLess(result["compressed_size"], result["original_size"])

    def test_decompress_message(self):
        """메시지 해제"""
        original = {
            "type": "alert",
            "severity": "HIGH",
            "message": "Critical threat detected: " + "x" * 500,  # 500바이트 추가
        }

        # 압축
        compressed = self.compressor.compress_message(original)

        # 해제
        decompressed = self.compressor.decompress_message(compressed["data"])

        self.assertEqual(decompressed["type"], original["type"])
        self.assertEqual(decompressed["severity"], original["severity"])

    def test_compression_disabled(self):
        """압축 비활성화"""
        compressor = WebSocketMessageCompressor(compression_enabled=False)

        message = {"data": "x" * 10000}
        result = compressor.compress_message(message)

        self.assertEqual(result["type"], "uncompressed")

    def test_compression_ratio(self):
        """압축 비율 계산"""
        message = {"type": "data", "content": "A" * 5000}  # 5KB 반복 데이터

        result = self.compressor.compress_message(message)

        if result["type"] == "compressed":
            ratio = result["ratio"]
            # 반복 데이터는 50% 이하로 압축되어야 함
            self.assertLess(ratio, 50)

    def test_compression_stats(self):
        """압축 통계"""
        # 여러 메시지 압축
        for i in range(5):
            message = {"id": i, "data": "x" * 1000}
            self.compressor.compress_message(message)

        stats = self.compressor.get_compression_stats()

        self.assertEqual(stats["total_messages"], 5)
        self.assertIn("avg_compression_ratio", stats)
        self.assertGreater(stats["total_original_bytes"], 0)

    def test_invalid_decompression(self):
        """유효하지 않은 압축 데이터"""
        result = self.compressor.decompress_message("invalid_base64!!!")

        self.assertIn("error", result)

    def test_roundtrip_compression(self):
        """압축-해제 왕복"""
        original = {
            "type": "complex",
            "nested": {"level": 1, "items": [1, 2, 3, 4, 5], "data": "x" * 2000},
        }

        # 압축
        compressed = compress_message(original)

        # 해제
        decompressed = decompress_message(compressed["data"])

        self.assertEqual(decompressed, original)

    def test_compression_stats_api(self):
        """압축 통계 API"""
        # 메시지 몇 개 처리
        for i in range(3):
            compress_message({"id": i, "data": "x" * 2000})

        stats = get_compression_stats()

        self.assertGreaterEqual(stats["total_messages"], 3)
        self.assertIn("total_original_bytes", stats)
        self.assertIn("total_bytes_saved", stats)


if __name__ == "__main__":
    unittest.main()
