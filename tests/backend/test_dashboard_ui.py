import pytest
import json
from guardian.ui.dashboard_ui import DashboardUI


class TestDashboardUI:
    """DashboardUI 테스트"""

    @pytest.fixture
    def dashboard(self):
        """DashboardUI 인스턴스"""
        return DashboardUI()

    @pytest.fixture
    def sample_threat(self):
        """샘플 위협"""
        return {
            'threat_type': 'volumetric_anomaly',
            'severity': 'HIGH',
            'region': 'us-east-1'
        }

    @pytest.fixture
    def sample_response(self):
        """샘플 대응"""
        return {
            'threat_id': 'threat_1',
            'action': 'isolate_resource',
            'status': 'COMPLETED',
            'effectiveness': 0.85
        }

    def test_register_threat(self, dashboard, sample_threat):
        """위협 맵 등록"""
        result = dashboard.register_threat(sample_threat)

        assert result['threat_id'] is not None
        assert result['registered_at'] is not None
        assert 'map_position' in result
        assert 'latitude' in result['map_position']
        assert 'longitude' in result['map_position']

    def test_resolve_threat(self, dashboard, sample_threat):
        """위협 해결"""
        # 위협 등록
        threat_result = dashboard.register_threat(sample_threat)
        threat_id = threat_result['threat_id']

        # 위협 해결
        resolve_result = dashboard.resolve_threat(threat_id)

        assert resolve_result['threat_id'] == threat_id
        assert resolve_result['status'] == 'RESOLVED'
        assert resolve_result['resolved_at'] is not None

    def test_update_metrics(self, dashboard):
        """메트릭 업데이트"""
        metrics = {
            'overall_status': 'HEALTHY',
            'success_rate': 0.95,
            'avg_latency_ms': 120.5,
            'total_threats': 5,
            'mitigated_threats': 5
        }

        result = dashboard.update_metrics(metrics)

        assert result['overall_status'] == 'HEALTHY'
        assert result['success_rate'] == 0.95
        assert result['avg_latency_ms'] == 120.5
        assert result['total_threats'] == 5
        assert result['mitigated_threats'] == 5
        assert result['active_threats'] == 0

    def test_record_response(self, dashboard, sample_response):
        """대응 이력 기록"""
        result = dashboard.record_response(sample_response)

        assert result['response_id'] is not None
        assert result['recorded_at'] is not None
        assert result['action'] == 'isolate_resource'

        # 이력에 기록됨 확인
        assert len(dashboard.response_history) == 1

    def test_get_dashboard_data(self, dashboard, sample_threat, sample_response):
        """대시보드 전체 데이터 조회"""
        # 위협 등록 및 대응 기록
        threat_result = dashboard.register_threat(sample_threat)
        sample_response['threat_id'] = threat_result['threat_id']

        dashboard.update_metrics({
            'overall_status': 'HEALTHY',
            'success_rate': 0.9,
            'avg_latency_ms': 150
        })

        dashboard.record_response(sample_response)

        data = dashboard.get_dashboard_data()

        assert 'threats' in data
        assert 'metrics' in data
        assert 'recent_responses' in data
        assert 'widget_configs' in data
        assert 'data_timestamp' in data

        assert len(data['threats']) == 1
        assert len(data['recent_responses']) == 1
        assert data['metrics']['overall_status'] == 'HEALTHY'

    def test_get_threat_timeline(self, dashboard, sample_threat):
        """위협 타임라인 조회"""
        # 여러 위협 등록
        for i in range(3):
            dashboard.register_threat(sample_threat)

        timeline = dashboard.get_threat_timeline(hours=24)

        assert len(timeline) == 3
        assert all('threat_id' in t for t in timeline)
        assert all('timestamp' in t for t in timeline)

    def test_get_effectiveness_metrics(self, dashboard, sample_response):
        """효과성 메트릭"""
        # 대응 이력 기록
        for i in range(3):
            response = sample_response.copy()
            response['response_id'] = f'response_{i}'
            response['effectiveness'] = 0.7 + (i * 0.1)
            dashboard.record_response(response)

        metrics = dashboard.get_effectiveness_metrics()

        assert metrics['total_responses'] == 3
        assert metrics['avg_effectiveness'] > 0.7
        assert 'effectiveness_by_action' in metrics
        assert 'isolate_resource' in metrics['effectiveness_by_action']

    def test_export_import_dashboard_config(self, dashboard):
        """대시보드 설정 내보내기/가져오기"""
        # 설정 내보내기
        config_json = dashboard.export_dashboard_config()

        assert isinstance(config_json, str)
        config = json.loads(config_json)
        assert 'widgets' in config
        assert 'refresh_intervals' in config

        # 설정 변경 및 가져오기
        updated_config = {
            'widgets': {
                'threat_map': {
                    'title': '실시간 위협 맵',
                    'refreshInterval': 3000  # 변경됨
                }
            }
        }

        result = dashboard.import_dashboard_config(json.dumps(updated_config))

        assert result['status'] == 'success'
        assert result['widgets_updated'] == 1
        assert dashboard.widget_configs['threat_map']['refreshInterval'] == 3000

    @pytest.mark.parametrize('region,expected_latitude', [
        ('us-east-1', 38.8951),
        ('us-west-2', 45.8951),
        ('eu-west-1', 53.3498),
        ('ap-southeast-1', 1.3521),
        ('unknown-region', 39.8283)  # 기본값
    ])
    def test_region_to_coordinates(self, dashboard, region, expected_latitude):
        """지역을 좌표로 변환"""
        threat = {
            'threat_type': 'test',
            'severity': 'LOW',
            'region': region
        }

        result = dashboard.register_threat(threat)
        latitude = result['map_position']['latitude']

        assert abs(latitude - expected_latitude) < 0.0001
