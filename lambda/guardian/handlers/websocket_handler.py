"""WebSocket API Gateway 핸들러
$connect, $disconnect, $default 라우트 처리
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

lambda_dir = str(Path(__file__).parent.parent.parent)
if lambda_dir not in sys.path:
    sys.path.insert(0, lambda_dir)

from guardian.responders.connection_manager import ConnectionManager
from guardian.responders.notification_buffer import NotificationBuffer
from guardian.responders.websocket_notifier import WebSocketNotifier
from guardian.realtime.dashboard_broadcaster import DashboardBroadcaster
import boto3
import asyncio

# 전역 인스턴스
ws_notifier = WebSocketNotifier()
conn_manager = ConnectionManager(ttl_seconds=300)
notification_buffer = NotificationBuffer(batch_window=10)

# DashboardBroadcaster 인스턴스
try:
    apigateway = boto3.client('apigatewaymanagementapi')
    dashboard_broadcaster = DashboardBroadcaster(apigateway)
except Exception as e:
    dashboard_broadcaster = None


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Build a standardised Lambda error response."""
    return {"statusCode": status_code, "body": json.dumps({"error": message})}


def _json_response(status_code: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a standardised Lambda JSON response."""
    return {"statusCode": status_code, "body": json.dumps(data)}


def _get_connection_id(event: Dict[str, Any]) -> str:
    """Extract connection ID from the API Gateway event."""
    return (event.get("requestContext") or {}).get("connectionId", "")


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the request body, falling back to the event itself for direct invocations."""
    body_str = event.get("body", "{}")
    try:
        return json.loads(body_str)
    except (json.JSONDecodeError, TypeError):
        return event


async def handle_connect(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """$connect 라우트 - 클라이언트 WebSocket 연결."""
    try:
        connection_id = _get_connection_id(event)
        query_params = event.get("queryStringParameters") or {}
        auth_token = query_params.get("token")

        if not connection_id:
            return _error_response(400, "Missing connection ID")
        if not auth_token:
            return _error_response(401, "Missing auth token")

        ws_result = await ws_notifier.connect_client(connection_id, auth_token)
        if ws_result.get("status") == "unauthorized":
            return _error_response(401, ws_result.get("error", "Unauthorized"))

        user_id = f"user-{connection_id[:8]}"
        await conn_manager.add_connection(
            connection_id,
            user_id,
            {
                "source": "websocket",
                "region": (event.get("requestContext") or {}).get("stage", "unknown"),
            },
        )

        return _json_response(
            200,
            {
                "status": "connected",
                "connection_id": connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        return _error_response(500, str(e))


async def handle_disconnect(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """$disconnect 라우트 - 클라이언트 WebSocket 연결 해제."""
    try:
        connection_id = _get_connection_id(event)
        if not connection_id:
            return _error_response(400, "Missing connection ID")

        await ws_notifier.disconnect_client(connection_id)
        result = await conn_manager.remove_connection(connection_id)

        return _json_response(
            200,
            {
                "status": "disconnected",
                "connection_id": connection_id,
                "duration_seconds": result.get("duration_seconds", 0),
            },
        )
    except Exception as e:
        return _error_response(500, str(e))


async def handle_default(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """$default 라우트 - 클라이언트로부터 수신한 메시지 처리."""
    try:
        connection_id = _get_connection_id(event)
        if not connection_id:
            return _error_response(400, "Missing connection ID")

        body_str = event.get("body", "{}")
        try:
            message_body = json.loads(body_str)
        except json.JSONDecodeError:
            return _error_response(400, "Invalid JSON body")

        await conn_manager.heartbeat(connection_id)
        result = await ws_notifier.handle_client_message(connection_id, message_body)
        await conn_manager.increment_message_count(connection_id)

        return _json_response(200, result)
    except Exception as e:
        return _error_response(500, str(e))


async def handle_threat_broadcast(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """위협 점수 브로드캐스트 — Lambda 직접 호출용 엔드포인트."""
    try:
        body = _parse_body(event)
        threat_score = body.get("threat_score", 0)
        severity = body.get("severity", "MEDIUM")

        if not isinstance(threat_score, (int, float)) or not (0 <= threat_score <= 10):
            return _error_response(400, "Invalid threat_score (0-10)")

        result = await ws_notifier.broadcast_threat_update(threat_score, severity)
        return _json_response(200, result)
    except Exception as e:
        return _error_response(500, str(e))


async def handle_anomaly_alert(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """이상 탐지 알림 전송 — Lambda 직접 호출용 엔드포인트."""
    try:
        body = _parse_body(event)
        connection_id = body.get("connection_id")
        anomaly_type = body.get("anomaly_type")
        details = body.get("details", {})

        if not connection_id:
            return _error_response(400, "Missing connection_id")
        if not anomaly_type:
            return _error_response(400, "Missing anomaly_type")

        result = await ws_notifier.send_anomaly_alert(connection_id, anomaly_type, details)
        return _json_response(200, result)
    except Exception as e:
        return _error_response(500, str(e))


async def handle_connection_stats(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """연결 통계 조회 — Lambda 직접 호출용 엔드포인트."""
    try:
        stats = {
            "ws_notifier": {"active_connections": ws_notifier.get_active_connections()},
            "conn_manager": conn_manager.get_stats(),
            "notification_buffer": notification_buffer.get_buffer_stats(),
        }
        return _json_response(200, stats)
    except Exception as e:
        return _error_response(500, str(e))


async def broadcast_threat_detected(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """위협 탐지 이벤트 실시간 브로드캐스트"""
    try:
        if not dashboard_broadcaster:
            return _error_response(500, "Dashboard broadcaster not initialized")

        body = _parse_body(event)
        threat = body.get("threat", {})

        await dashboard_broadcaster.on_threat_detected(threat)

        return _json_response(200, {
            "status": "broadcasted",
            "threat_id": threat.get("threat_id"),
            "active_connections": dashboard_broadcaster.get_active_connection_count()
        })
    except Exception as e:
        return _error_response(500, str(e))


async def broadcast_action_executed(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """작업 실행 이벤트 실시간 브로드캐스트"""
    try:
        if not dashboard_broadcaster:
            return _error_response(500, "Dashboard broadcaster not initialized")

        body = _parse_body(event)
        action = body.get("action", {})

        await dashboard_broadcaster.on_action_executed(action)

        return _json_response(200, {
            "status": "broadcasted",
            "action_id": action.get("action_id"),
            "active_connections": dashboard_broadcaster.get_active_connection_count()
        })
    except Exception as e:
        return _error_response(500, str(e))


async def broadcast_feedback_submitted(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """피드백 제출 이벤트 실시간 브로드캐스트"""
    try:
        if not dashboard_broadcaster:
            return _error_response(500, "Dashboard broadcaster not initialized")

        body = _parse_body(event)
        feedback = body.get("feedback", {})
        current_accuracy = body.get("current_accuracy", 0.0)

        await dashboard_broadcaster.on_feedback_submitted(feedback, current_accuracy)

        return _json_response(200, {
            "status": "broadcasted",
            "feedback_id": feedback.get("feedback_id"),
            "model_accuracy": round(current_accuracy, 4),
            "active_connections": dashboard_broadcaster.get_active_connection_count()
        })
    except Exception as e:
        return _error_response(500, str(e))


async def broadcast_playbook_status(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """플레이북 상태 변경 이벤트 실시간 브로드캐스트"""
    try:
        if not dashboard_broadcaster:
            return _error_response(500, "Dashboard broadcaster not initialized")

        body = _parse_body(event)
        playbook = body.get("playbook", {})

        await dashboard_broadcaster.on_playbook_status_changed(playbook)

        return _json_response(200, {
            "status": "broadcasted",
            "playbook_id": playbook.get("playbook_id"),
            "active_connections": dashboard_broadcaster.get_active_connection_count()
        })
    except Exception as e:
        return _error_response(500, str(e))


async def broadcast_metrics_updated(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """대시보드 메트릭 업데이트 이벤트 실시간 브로드캐스트"""
    try:
        if not dashboard_broadcaster:
            return _error_response(500, "Dashboard broadcaster not initialized")

        body = _parse_body(event)
        metrics = body.get("metrics", {})

        await dashboard_broadcaster.on_metrics_updated(metrics)

        return _json_response(200, {
            "status": "broadcasted",
            "active_connections": dashboard_broadcaster.get_active_connection_count()
        })
    except Exception as e:
        return _error_response(500, str(e))


def get_broadcaster_status(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """DashboardBroadcaster 상태 조회"""
    try:
        if not dashboard_broadcaster:
            return _error_response(500, "Dashboard broadcaster not initialized")

        return _json_response(200, {
            "active_connections": dashboard_broadcaster.get_active_connection_count(),
            "connection_ids": dashboard_broadcaster.get_active_connections(),
            "status": "operational" if dashboard_broadcaster.get_active_connection_count() >= 0 else "error"
        })
    except Exception as e:
        return _error_response(500, str(e))
