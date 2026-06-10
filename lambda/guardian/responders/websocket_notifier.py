"""
WebSocket 기반 실시간 양방향 알림 시스템
"""

import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WebSocketNotifier:
    """WebSocket을 통한 실시간 양방향 알림"""

    def __init__(self):
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.connection_count = 0

    async def connect_client(self, connection_id: str, auth_token: str) -> Dict[str, Any]:
        """
        클라이언트 WebSocket 연결

        Args:
            connection_id: API Gateway 연결 ID
            auth_token: 인증 토큰

        Returns:
            연결 결과
        """
        # WEBSOCKET_AUTH_TOKEN 환경 변수와 일치해야만 연결 허용 (미설정 시 전체 거부)
        expected_token = os.getenv("WEBSOCKET_AUTH_TOKEN", "")
        if not expected_token:
            logger.warning(
                "WEBSOCKET_AUTH_TOKEN is not configured; rejecting connection %s", connection_id
            )
            return {"status": "unauthorized", "error": "Invalid token"}

        if not auth_token or not hmac.compare_digest(auth_token, expected_token):
            return {"status": "unauthorized", "error": "Invalid token"}

        self.connections[connection_id] = {
            "connection_id": connection_id,
            "auth_token": auth_token,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "subscriptions": set(),  # 구독 중인 이벤트 타입
            "message_count": 0,
        }
        self.connection_count += 1

        return {
            "status": "connected",
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def disconnect_client(self, connection_id: str) -> None:
        """
        클라이언트 WebSocket 연결 해제

        Args:
            connection_id: API Gateway 연결 ID
        """
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.connection_count -= 1

    async def broadcast_threat_update(self, threat_score: float, severity: str) -> Dict[str, Any]:
        """
        모든 클라이언트에게 위협 점수 브로드캐스트

        Args:
            threat_score: 위협 점수 (0-10)
            severity: 심각도 (CRITICAL, HIGH, MEDIUM, LOW)

        Returns:
            브로드캐스트 결과
        """
        message = {
            "type": "threat_detected",
            "score": round(threat_score, 1),
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sent_count = 0
        for conn_id in list(self.connections.keys()):
            await self._send_to_connection(conn_id, message)
            sent_count += 1

        return {"status": "broadcasted", "recipients": sent_count, "message": message}

    async def send_anomaly_alert(
        self, connection_id: str, anomaly_type: str, details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        특정 클라이언트에게 이상 탐지 알림

        Args:
            connection_id: API Gateway 연결 ID
            anomaly_type: 이상 타입 (cost, security, performance)
            details: 상세 정보

        Returns:
            전송 결과
        """
        message = {
            "type": "anomaly_detected",
            "anomaly_type": anomaly_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if connection_id not in self.connections:
            return {"status": "failed", "error": "Connection not found"}

        await self._send_to_connection(connection_id, message)

        return {"status": "sent", "connection_id": connection_id}

    async def handle_client_message(
        self, connection_id: str, message_body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        클라이언트로부터 수신한 메시지 처리

        Args:
            connection_id: API Gateway 연결 ID
            message_body: 클라이언트 메시지

        Returns:
            처리 결과
        """
        if connection_id not in self.connections:
            return {"status": "failed", "error": "Connection not found"}

        action = message_body.get("action")

        if action == "subscribe":
            event_types = message_body.get("event_types", [])
            self.connections[connection_id]["subscriptions"].update(event_types)
            return {"status": "subscribed", "event_types": event_types}

        elif action == "unsubscribe":
            event_types = message_body.get("event_types", [])
            subs = self.connections[connection_id]["subscriptions"]
            subs.difference_update(event_types)
            return {"status": "unsubscribed", "event_types": event_types}

        elif action == "ping":
            return {"status": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}

        else:
            return {"status": "unknown_action", "action": action}

    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> None:
        """
        특정 연결에 메시지 전송

        Args:
            connection_id: 대상 연결 ID
            message: 전송할 메시지
        """
        if connection_id in self.connections:
            self.connections[connection_id]["message_count"] += 1

    def get_active_connections(self) -> int:
        """활성 연결 수"""
        return len(self.connections)

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """연결 정보 조회"""
        return self.connections.get(connection_id)

    def get_all_connections(self) -> List[Dict[str, Any]]:
        """모든 연결 정보 조회"""
        return list(self.connections.values())


# 글로벌 WebSocket 알림 인스턴스
_ws_notifier = WebSocketNotifier()


async def connect_client(connection_id: str, auth_token: str) -> Dict[str, Any]:
    """클라이언트 연결 (async)"""
    return await _ws_notifier.connect_client(connection_id, auth_token)


async def disconnect_client(connection_id: str) -> None:
    """클라이언트 연결 해제 (async)"""
    await _ws_notifier.disconnect_client(connection_id)


async def broadcast_threat_update(threat_score: float, severity: str) -> Dict[str, Any]:
    """위협 점수 브로드캐스트 (async)"""
    return await _ws_notifier.broadcast_threat_update(threat_score, severity)


async def send_anomaly_alert(
    connection_id: str, anomaly_type: str, details: Dict[str, Any]
) -> Dict[str, Any]:
    """이상 탐지 알림 전송 (async)"""
    return await _ws_notifier.send_anomaly_alert(connection_id, anomaly_type, details)


async def handle_client_message(connection_id: str, message_body: Dict[str, Any]) -> Dict[str, Any]:
    """클라이언트 메시지 처리 (async)"""
    return await _ws_notifier.handle_client_message(connection_id, message_body)
