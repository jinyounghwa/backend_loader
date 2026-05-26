import json
import asyncio
import logging
from typing import Dict, List, Any, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class DashboardBroadcaster:
    """위협 탐지, 작업 실행, 피드백을 실시간 대시보드에 브로드캐스트"""

    def __init__(self, apigateway_client):
        """
        Args:
            apigateway_client: API Gateway Management API 클라이언트
        """
        self.apigateway = apigateway_client
        self.active_connections: Dict[str, Any] = {}  # connection_id → ws_client
        self.message_queue: asyncio.Queue = asyncio.Queue()

    def register_connection(self, connection_id: str, ws_client: Any) -> None:
        """WebSocket 연결 등록"""
        self.active_connections[connection_id] = ws_client
        logger.info(f"WebSocket connection registered: {connection_id} (total: {len(self.active_connections)})")

    def unregister_connection(self, connection_id: str) -> None:
        """WebSocket 연결 제거"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"WebSocket connection removed: {connection_id} (remaining: {len(self.active_connections)})")

    async def on_threat_detected(self, threat: Dict[str, Any]) -> None:
        """
        위협 탐지 시 실시간 브로드캐스트

        Args:
            threat: {
                'threat_id': str,
                'threat_type': str,
                'severity': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
                'rule_id': str,
                'timestamp': str,
                'evidence': List[str],
                'account_id': str,
                'recommended_playbooks': List[str]
            }
        """
        message = {
            'type': 'threat_detected',
            'threat_id': threat.get('threat_id'),
            'threat_type': threat.get('threat_type'),
            'severity': threat.get('severity'),
            'rule_id': threat.get('rule_id'),
            'timestamp': threat.get('timestamp', datetime.utcnow().isoformat()),
            'evidence_count': len(threat.get('evidence', [])),
            'account_id': threat.get('account_id'),
            'recommended_playbooks': threat.get('recommended_playbooks', [])
        }

        await self.broadcast_to_all(message)
        logger.info(f"Threat {threat.get('threat_id')} broadcasted to {len(self.active_connections)} clients")

    async def on_action_executed(self, action: Dict[str, Any]) -> None:
        """
        작업 실행 시 실시간 업데이트

        Args:
            action: {
                'action_id': str,
                'playbook_id': str,
                'action_type': str,
                'status': 'PENDING' | 'EXECUTING' | 'SUCCESS' | 'FAILED',
                'timestamp': str,
                'cost': float
            }
        """
        message = {
            'type': 'action_executed',
            'action_id': action.get('action_id'),
            'playbook_id': action.get('playbook_id'),
            'action_type': action.get('action_type'),
            'status': action.get('status'),
            'timestamp': action.get('timestamp', datetime.utcnow().isoformat()),
            'cost': action.get('cost', 0)
        }

        await self.broadcast_to_all(message)
        logger.info(f"Action {action.get('action_id')} status update broadcasted")

    async def on_feedback_submitted(self, feedback: Dict[str, Any], current_accuracy: float) -> None:
        """
        피드백 제출 시 메트릭 업데이트

        Args:
            feedback: {
                'feedback_id': str,
                'threat_id': str,
                'is_correct': bool,
                'severity': str,
                'timestamp': str
            }
            current_accuracy: 현재 모델 정확도
        """
        message = {
            'type': 'feedback_submitted',
            'feedback_id': feedback.get('feedback_id'),
            'threat_id': feedback.get('threat_id'),
            'is_correct': feedback.get('is_correct'),
            'severity': feedback.get('severity'),
            'timestamp': feedback.get('timestamp', datetime.utcnow().isoformat()),
            'model_accuracy': round(current_accuracy, 4)
        }

        await self.broadcast_to_all(message)
        logger.info(f"Feedback {feedback.get('feedback_id')} update broadcasted")

    async def on_playbook_status_changed(self, playbook: Dict[str, Any]) -> None:
        """
        플레이북 상태 변경 시 브로드캐스트

        Args:
            playbook: {
                'playbook_id': str,
                'status': 'PENDING' | 'EXECUTING' | 'COMPLETED' | 'FAILED',
                'executed_actions': int,
                'total_actions': int,
                'timestamp': str
            }
        """
        message = {
            'type': 'playbook_status_changed',
            'playbook_id': playbook.get('playbook_id'),
            'status': playbook.get('status'),
            'executed_actions': playbook.get('executed_actions', 0),
            'total_actions': playbook.get('total_actions', 0),
            'progress': (
                playbook.get('executed_actions', 0) / playbook.get('total_actions', 1) * 100
                if playbook.get('total_actions', 0) > 0 else 0
            ),
            'timestamp': playbook.get('timestamp', datetime.utcnow().isoformat())
        }

        await self.broadcast_to_all(message)
        logger.info(f"Playbook {playbook.get('playbook_id')} status update broadcasted")

    async def on_metrics_updated(self, metrics: Dict[str, Any]) -> None:
        """
        대시보드 메트릭 업데이트

        Args:
            metrics: {
                'threats_detected_1h': int,
                'threats_mitigated_1h': int,
                'avg_response_time_ms': float,
                'total_cost_1h': float,
                'top_threat_types': List[str],
                'timestamp': str
            }
        """
        message = {
            'type': 'metrics_updated',
            'threats_detected_1h': metrics.get('threats_detected_1h', 0),
            'threats_mitigated_1h': metrics.get('threats_mitigated_1h', 0),
            'avg_response_time_ms': round(metrics.get('avg_response_time_ms', 0), 2),
            'total_cost_1h': round(metrics.get('total_cost_1h', 0), 2),
            'top_threat_types': metrics.get('top_threat_types', []),
            'timestamp': metrics.get('timestamp', datetime.utcnow().isoformat())
        }

        await self.broadcast_to_all(message)

    async def broadcast_to_all(self, message: Dict[str, Any]) -> None:
        """
        모든 연결된 클라이언트에 메시지 발송

        Args:
            message: 브로드캐스트할 메시지 딕셔너리
        """
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return

        disconnected_ids = []
        failed_count = 0

        for connection_id in list(self.active_connections.keys()):
            try:
                await self.apigateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message)
                )
            except Exception as e:
                logger.warning(f"Failed to send to {connection_id}: {e}")
                disconnected_ids.append(connection_id)
                failed_count += 1

        # 실패한 연결 제거
        for connection_id in disconnected_ids:
            self.unregister_connection(connection_id)

        if failed_count > 0:
            logger.warning(
                f"Broadcast complete: {len(self.active_connections) - failed_count}/{len(self.active_connections)} successful"
            )

    async def broadcast_to_account(self, account_id: str, message: Dict[str, Any]) -> None:
        """
        특정 계정의 클라이언트들만 메시지 발송

        Args:
            account_id: AWS 계정 ID
            message: 메시지
        """
        message_with_account = {**message, 'account_id': account_id}
        await self.broadcast_to_all(message_with_account)

    def get_active_connection_count(self) -> int:
        """활성 연결 수"""
        return len(self.active_connections)

    def get_active_connections(self) -> List[str]:
        """활성 연결 ID 목록"""
        return list(self.active_connections.keys())
