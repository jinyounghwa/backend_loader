import pytest
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
from guardian.realtime.dashboard_broadcaster import DashboardBroadcaster


class TestDashboardBroadcaster:
    """DashboardBroadcaster 테스트"""

    @pytest.fixture
    def mock_apigateway(self):
        """Mock API Gateway 클라이언트"""
        mock = AsyncMock()
        mock.post_to_connection = AsyncMock()
        return mock

    @pytest.fixture
    def broadcaster(self, mock_apigateway):
        return DashboardBroadcaster(mock_apigateway)

    @pytest.mark.asyncio
    async def test_websocket_connect(self, broadcaster):
        """클라이언트 연결 → 정상 등록"""
        connection_id = "abc123"
        ws_client = Mock()

        broadcaster.register_connection(connection_id, ws_client)

        assert connection_id in broadcaster.active_connections
        assert broadcaster.get_active_connection_count() == 1

    @pytest.mark.asyncio
    async def test_websocket_disconnect(self, broadcaster):
        """클라이언트 해제 → 정상 제거"""
        connection_id = "abc123"
        broadcaster.register_connection(connection_id, Mock())

        broadcaster.unregister_connection(connection_id)

        assert connection_id not in broadcaster.active_connections
        assert broadcaster.get_active_connection_count() == 0

    @pytest.mark.asyncio
    async def test_broadcast_threat_detected(self, broadcaster, mock_apigateway):
        """위협 탐지 → 모든 클라이언트에 브로드캐스트"""
        broadcaster.register_connection("conn1", Mock())
        broadcaster.register_connection("conn2", Mock())

        threat = {
            'threat_id': 'threat_1',
            'threat_type': 'connection_spike',
            'severity': 'HIGH',
            'rule_id': 'rule_1',
            'timestamp': datetime.utcnow().isoformat(),
            'evidence': ['log1', 'log2'],
            'account_id': 'acc_123',
            'recommended_playbooks': ['pb_1', 'pb_2']
        }

        await broadcaster.on_threat_detected(threat)

        # 2개 연결에 각각 메시지 전송되어야 함
        assert mock_apigateway.post_to_connection.call_count == 2

        # 메시지 내용 검증
        call_args = mock_apigateway.post_to_connection.call_args_list[0]
        message_data = json.loads(call_args.kwargs['Data'])
        assert message_data['type'] == 'threat_detected'
        assert message_data['threat_id'] == 'threat_1'
        assert message_data['severity'] == 'HIGH'

    @pytest.mark.asyncio
    async def test_broadcast_action_executed(self, broadcaster, mock_apigateway):
        """작업 실행 → 모든 클라이언트에 브로드캐스트"""
        broadcaster.register_connection("conn1", Mock())

        action = {
            'action_id': 'action_1',
            'playbook_id': 'pb_1',
            'action_type': 'stop_instance',
            'status': 'SUCCESS',
            'timestamp': datetime.utcnow().isoformat(),
            'cost': 0.0
        }

        await broadcaster.on_action_executed(action)

        mock_apigateway.post_to_connection.assert_called_once()
        call_args = mock_apigateway.post_to_connection.call_args_list[0]
        message_data = json.loads(call_args.kwargs['Data'])
        assert message_data['type'] == 'action_executed'
        assert message_data['status'] == 'SUCCESS'

    @pytest.mark.asyncio
    async def test_broadcast_feedback_submitted(self, broadcaster, mock_apigateway):
        """피드백 제출 → 메트릭 업데이트 브로드캐스트"""
        broadcaster.register_connection("conn1", Mock())

        feedback = {
            'feedback_id': 'fb_1',
            'threat_id': 'threat_1',
            'is_correct': True,
            'severity': 'HIGH',
            'timestamp': datetime.utcnow().isoformat()
        }

        await broadcaster.on_feedback_submitted(feedback, current_accuracy=0.85)

        mock_apigateway.post_to_connection.assert_called_once()
        call_args = mock_apigateway.post_to_connection.call_args_list[0]
        message_data = json.loads(call_args.kwargs['Data'])
        assert message_data['type'] == 'feedback_submitted'
        assert message_data['model_accuracy'] == 0.85

    @pytest.mark.asyncio
    async def test_broadcast_failure_resilience(self, broadcaster, mock_apigateway):
        """일부 클라이언트 실패 → 나머지 계속 작동"""
        broadcaster.register_connection("conn1", Mock())
        broadcaster.register_connection("conn2", Mock())
        broadcaster.register_connection("conn3", Mock())

        # conn2에 대해서만 실패 시뮬레이션
        async def side_effect(**kwargs):
            if kwargs['ConnectionId'] == 'conn2':
                raise Exception("Connection closed")

        mock_apigateway.post_to_connection.side_effect = side_effect

        threat = {
            'threat_id': 'threat_1',
            'threat_type': 'connection_spike',
            'severity': 'HIGH',
            'rule_id': 'rule_1',
            'timestamp': datetime.utcnow().isoformat(),
            'evidence': [],
            'account_id': 'acc_123',
            'recommended_playbooks': []
        }

        await broadcaster.on_threat_detected(threat)

        # 실패한 연결 제거되어야 함
        assert 'conn2' not in broadcaster.active_connections
        assert 'conn1' in broadcaster.active_connections
        assert 'conn3' in broadcaster.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_playbook_status(self, broadcaster, mock_apigateway):
        """플레이북 상태 변경 → 브로드캐스트"""
        broadcaster.register_connection("conn1", Mock())

        playbook = {
            'playbook_id': 'pb_1',
            'status': 'EXECUTING',
            'executed_actions': 3,
            'total_actions': 5,
            'timestamp': datetime.utcnow().isoformat()
        }

        await broadcaster.on_playbook_status_changed(playbook)

        mock_apigateway.post_to_connection.assert_called_once()
        call_args = mock_apigateway.post_to_connection.call_args_list[0]
        message_data = json.loads(call_args.kwargs['Data'])
        assert message_data['type'] == 'playbook_status_changed'
        assert message_data['progress'] == 60.0  # 3/5 = 60%

    @pytest.mark.asyncio
    async def test_broadcast_metrics_updated(self, broadcaster, mock_apigateway):
        """메트릭 업데이트 → 브로드캐스트"""
        broadcaster.register_connection("conn1", Mock())

        metrics = {
            'threats_detected_1h': 10,
            'threats_mitigated_1h': 8,
            'avg_response_time_ms': 250.5,
            'total_cost_1h': 5.25,
            'top_threat_types': ['connection_spike', 'unknown_region'],
            'timestamp': datetime.utcnow().isoformat()
        }

        await broadcaster.on_metrics_updated(metrics)

        mock_apigateway.post_to_connection.assert_called_once()
        call_args = mock_apigateway.post_to_connection.call_args_list[0]
        message_data = json.loads(call_args.kwargs['Data'])
        assert message_data['type'] == 'metrics_updated'
        assert message_data['threats_detected_1h'] == 10
        assert message_data['total_cost_1h'] == 5.25

    @pytest.mark.asyncio
    async def test_websocket_message_ordering(self, broadcaster, mock_apigateway):
        """메시지 순서 유지"""
        broadcaster.register_connection("conn1", Mock())

        messages = []

        async def capture_message(**kwargs):
            messages.append(json.loads(kwargs['Data']))

        mock_apigateway.post_to_connection.side_effect = capture_message

        # 여러 위협 순서대로 전송
        for i in range(3):
            threat = {
                'threat_id': f'threat_{i}',
                'threat_type': 'connection_spike',
                'severity': 'HIGH',
                'rule_id': 'rule_1',
                'timestamp': datetime.utcnow().isoformat(),
                'evidence': [],
                'account_id': 'acc_123',
                'recommended_playbooks': []
            }
            await broadcaster.on_threat_detected(threat)

        # 순서 확인
        assert len(messages) == 3
        for i, msg in enumerate(messages):
            assert msg['threat_id'] == f'threat_{i}'

    @pytest.mark.asyncio
    async def test_connection_count_tracking(self, broadcaster):
        """연결 수 추적"""
        assert broadcaster.get_active_connection_count() == 0

        broadcaster.register_connection("conn1", Mock())
        assert broadcaster.get_active_connection_count() == 1

        broadcaster.register_connection("conn2", Mock())
        assert broadcaster.get_active_connection_count() == 2

        broadcaster.unregister_connection("conn1")
        assert broadcaster.get_active_connection_count() == 1

        assert "conn1" not in broadcaster.get_active_connections()
        assert "conn2" in broadcaster.get_active_connections()

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_connections(self, broadcaster, mock_apigateway):
        """연결이 없을 때 브로드캐스트 시도"""
        threat = {
            'threat_id': 'threat_1',
            'threat_type': 'connection_spike',
            'severity': 'HIGH',
            'rule_id': 'rule_1',
            'timestamp': datetime.utcnow().isoformat(),
            'evidence': [],
            'account_id': 'acc_123',
            'recommended_playbooks': []
        }

        # 예외 발생하지 않아야 함
        await broadcaster.on_threat_detected(threat)

        # 아무 메시지도 전송되지 않아야 함
        mock_apigateway.post_to_connection.assert_not_called()
