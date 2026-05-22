"""
WebSocket API Gateway 핸들러
$connect, $disconnect, $default 라우트 처리
"""

import json
from typing import Dict, Any
from datetime import datetime, timezone

# AWS Guardian 모듈
import sys
from pathlib import Path
lambda_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(lambda_dir))

from guardian.responders.websocket_notifier import WebSocketNotifier
from guardian.responders.connection_manager import ConnectionManager
from guardian.responders.notification_buffer import NotificationBuffer


# 전역 인스턴스
ws_notifier = WebSocketNotifier()
conn_manager = ConnectionManager(ttl_seconds=300)
notification_buffer = NotificationBuffer(batch_window=10)


async def handle_connect(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    $connect 라우트 - 클라이언트 WebSocket 연결

    Query parameters:
        token: 인증 토큰

    Returns:
        {statusCode: 200/401, body: JSON}
    """
    try:
        # 연결 ID와 토큰 추출
        connection_id = event.get("requestContext", {}).get("connectionId")
        query_params = event.get("queryStringParameters") or {}
        auth_token = query_params.get("token")

        if not connection_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing connection ID"})
            }

        if not auth_token:
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Missing auth token"})
            }

        # WebSocket 연결 수립
        ws_result = await ws_notifier.connect_client(connection_id, auth_token)

        if ws_result.get("status") == "unauthorized":
            return {
                "statusCode": 401,
                "body": json.dumps(ws_result)
            }

        # 연결 관리자에 등록
        user_id = f"user-{connection_id[:8]}"  # 간단한 사용자 ID
        await conn_manager.add_connection(connection_id, user_id, {
            "source": "websocket",
            "region": event.get("requestContext", {}).get("stage", "unknown")
        })

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "connected",
                "connection_id": connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


async def handle_disconnect(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    $disconnect 라우트 - 클라이언트 WebSocket 연결 해제

    Returns:
        {statusCode: 200, body: JSON}
    """
    try:
        connection_id = event.get("requestContext", {}).get("connectionId")

        if not connection_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing connection ID"})
            }

        # WebSocket 연결 해제
        await ws_notifier.disconnect_client(connection_id)

        # 연결 관리자에서 제거
        result = await conn_manager.remove_connection(connection_id)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "disconnected",
                "connection_id": connection_id,
                "duration_seconds": result.get("duration_seconds", 0)
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


async def handle_default(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    $default 라우트 - 클라이언트로부터 수신한 메시지 처리

    Message format:
        {
            "action": "subscribe" | "unsubscribe" | "ping",
            "event_types": ["threat", "anomaly"],  // subscribe/unsubscribe용
        }

    Returns:
        {statusCode: 200, body: JSON}
    """
    try:
        connection_id = event.get("requestContext", {}).get("connectionId")
        body_str = event.get("body", "{}")

        if not connection_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing connection ID"})
            }

        # 메시지 파싱
        try:
            message_body = json.loads(body_str)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid JSON body"})
            }

        # 하트비트 갱신
        await conn_manager.heartbeat(connection_id)

        # 클라이언트 메시지 처리
        result = await ws_notifier.handle_client_message(connection_id, message_body)

        # 메시지 카운트 증가
        await conn_manager.increment_message_count(connection_id)

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


async def handle_threat_broadcast(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    위협 점수 브로드캐스트
    Lambda 직접 호출용 엔드포인트

    Body:
        {
            "threat_score": 7.5,
            "severity": "HIGH"
        }

    Returns:
        {statusCode: 200, body: JSON}
    """
    try:
        # 요청 본문 파싱
        body_str = event.get("body", "{}")
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError:
            body = event  # 직접 호출의 경우

        threat_score = body.get("threat_score", 0)
        severity = body.get("severity", "MEDIUM")

        if not isinstance(threat_score, (int, float)) or threat_score < 0 or threat_score > 10:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid threat_score (0-10)"})
            }

        # 브로드캐스트
        result = await ws_notifier.broadcast_threat_update(threat_score, severity)

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


async def handle_anomaly_alert(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    이상 탐지 알림 전송
    Lambda 직접 호출용 엔드포인트

    Body:
        {
            "connection_id": "conn-123",
            "anomaly_type": "cost",
            "details": {"daily_cost": 150.0, "threshold": 100.0}
        }

    Returns:
        {statusCode: 200, body: JSON}
    """
    try:
        # 요청 본문 파싱
        body_str = event.get("body", "{}")
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError:
            body = event

        connection_id = body.get("connection_id")
        anomaly_type = body.get("anomaly_type")
        details = body.get("details", {})

        if not connection_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing connection_id"})
            }

        if not anomaly_type:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing anomaly_type"})
            }

        # 이상 탐지 알림 전송
        result = await ws_notifier.send_anomaly_alert(
            connection_id,
            anomaly_type,
            details
        )

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


async def handle_connection_stats(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    연결 통계 조회
    Lambda 직접 호출용 엔드포인트

    Returns:
        {statusCode: 200, body: JSON}
    """
    try:
        stats = {
            "ws_notifier": {
                "active_connections": ws_notifier.get_active_connections()
            },
            "conn_manager": conn_manager.get_stats(),
            "notification_buffer": notification_buffer.get_buffer_stats()
        }

        return {
            "statusCode": 200,
            "body": json.dumps(stats)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
