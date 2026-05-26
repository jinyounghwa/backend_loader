import logging
import uuid
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DashboardUI:
    """실시간 위협 대시보드 UI 백엔드"""

    def __init__(self):
        """대시보드 초기화"""
        self.threat_map = {}
        self.metrics = {}
        self.response_history = []
        self.widget_configs = {
            'threat_map': {'title': '실시간 위협 맵', 'refreshInterval': 5000},
            'metrics': {'title': '시스템 메트릭', 'refreshInterval': 10000},
            'response_history': {'title': '대응 이력', 'refreshInterval': 5000},
            'effectiveness': {'title': '효과성 분석', 'refreshInterval': 30000}
        }

    def register_threat(self, threat: Dict) -> Dict:
        """
        위협을 맵에 등록

        Args:
            threat: 위협 정보

        Returns:
            {
                'threat_id': str,
                'registered_at': str,
                'map_position': {'latitude': float, 'longitude': float}
            }
        """
        threat_id = str(uuid.uuid4())

        # 지역 기반 좌표 생성 (시뮬레이션)
        region = threat.get('region', 'us-east-1')
        latitude, longitude = self._region_to_coordinates(region)

        threat_entry = {
            'threat_id': threat_id,
            'threat_type': threat.get('threat_type', 'unknown'),
            'severity': threat.get('severity', 'LOW'),
            'region': region,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'ACTIVE'
        }

        self.threat_map[threat_id] = threat_entry

        logger.info(f"Threat registered on map: {threat_id} at ({latitude}, {longitude})")

        return {
            'threat_id': threat_id,
            'registered_at': threat_entry['timestamp'],
            'map_position': {'latitude': latitude, 'longitude': longitude}
        }

    def resolve_threat(self, threat_id: str) -> Dict:
        """
        위협 해결

        Args:
            threat_id: 위협 ID

        Returns:
            {
                'threat_id': str,
                'status': 'RESOLVED',
                'resolved_at': str
            }
        """
        if threat_id not in self.threat_map:
            return {'error': 'Threat not found'}

        self.threat_map[threat_id]['status'] = 'RESOLVED'
        self.threat_map[threat_id]['resolved_at'] = datetime.utcnow().isoformat()

        logger.info(f"Threat resolved: {threat_id}")

        return {
            'threat_id': threat_id,
            'status': 'RESOLVED',
            'resolved_at': self.threat_map[threat_id]['resolved_at']
        }

    def update_metrics(self, metrics: Dict) -> Dict:
        """
        대시보드 메트릭 업데이트

        Args:
            metrics: 메트릭 정보

        Returns:
            {
                'overall_status': str,
                'success_rate': float,
                'avg_latency_ms': float,
                'total_threats': int,
                'mitigated_threats': int
            }
        """
        self.metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': metrics.get('overall_status', 'HEALTHY'),
            'success_rate': metrics.get('success_rate', 0.9),
            'avg_latency_ms': metrics.get('avg_latency_ms', 0),
            'total_threats': metrics.get('total_threats', 0),
            'mitigated_threats': metrics.get('mitigated_threats', 0),
            'active_threats': len([t for t in self.threat_map.values() if t['status'] == 'ACTIVE'])
        }

        logger.info(f"Metrics updated: {self.metrics['overall_status']}")

        return self.metrics

    def record_response(self, response: Dict) -> Dict:
        """
        대응 이력 기록

        Args:
            response: 대응 정보

        Returns:
            {
                'response_id': str,
                'recorded_at': str,
                'action': str
            }
        """
        response_id = str(uuid.uuid4())

        response_entry = {
            'response_id': response_id,
            'threat_id': response.get('threat_id'),
            'action': response.get('action'),
            'status': response.get('status', 'COMPLETED'),
            'timestamp': datetime.utcnow().isoformat(),
            'effectiveness': response.get('effectiveness', 0.7)
        }

        self.response_history.append(response_entry)

        # 최근 100개만 유지
        if len(self.response_history) > 100:
            self.response_history = self.response_history[-100:]

        logger.info(f"Response recorded: {response_id} - {response.get('action')}")

        return {
            'response_id': response_id,
            'recorded_at': response_entry['timestamp'],
            'action': response_entry['action']
        }

    def get_dashboard_data(self) -> Dict:
        """
        대시보드용 전체 데이터 조회

        Returns:
            {
                'threats': [...],
                'metrics': {...},
                'recent_responses': [...],
                'widget_configs': {...}
            }
        """
        # 활성 위협만 반환
        active_threats = [
            t for t in self.threat_map.values()
            if t['status'] == 'ACTIVE'
        ]

        # 최근 응답 (최대 20개)
        recent_responses = sorted(
            self.response_history,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:20]

        return {
            'threats': active_threats,
            'metrics': self.metrics,
            'recent_responses': recent_responses,
            'widget_configs': self.widget_configs,
            'data_timestamp': datetime.utcnow().isoformat()
        }

    def get_threat_timeline(self, hours: int = 24) -> List[Dict]:
        """
        위협 타임라인 조회

        Args:
            hours: 조회 기간 (시간)

        Returns:
            위협 타임라인 목록
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        timeline = []
        for threat_id, threat in self.threat_map.items():
            threat_time = datetime.fromisoformat(threat['timestamp'])
            if threat_time > cutoff_time:
                timeline.append({
                    'threat_id': threat_id,
                    'threat_type': threat['threat_type'],
                    'severity': threat['severity'],
                    'timestamp': threat['timestamp'],
                    'status': threat['status']
                })

        return sorted(timeline, key=lambda x: x['timestamp'], reverse=True)

    def get_effectiveness_metrics(self) -> Dict:
        """
        대응 효과성 메트릭

        Returns:
            {
                'total_responses': int,
                'avg_effectiveness': float,
                'effectiveness_by_action': {...}
            }
        """
        if not self.response_history:
            return {
                'total_responses': 0,
                'avg_effectiveness': 0.0,
                'effectiveness_by_action': {}
            }

        total = len(self.response_history)
        avg_effectiveness = sum(r['effectiveness'] for r in self.response_history) / total

        # 액션별 효과성
        action_effectiveness = {}
        for response in self.response_history:
            action = response['action']
            if action not in action_effectiveness:
                action_effectiveness[action] = []
            action_effectiveness[action].append(response['effectiveness'])

        effectiveness_by_action = {
            action: sum(scores) / len(scores)
            for action, scores in action_effectiveness.items()
        }

        return {
            'total_responses': total,
            'avg_effectiveness': round(avg_effectiveness, 3),
            'effectiveness_by_action': {
                action: round(score, 3)
                for action, score in effectiveness_by_action.items()
            }
        }

    def _region_to_coordinates(self, region: str) -> tuple:
        """
        AWS 리전을 지리적 좌표로 변환

        Returns: (latitude, longitude)
        """
        coordinates = {
            'us-east-1': (38.8951, -77.0369),
            'us-west-2': (45.8951, -119.2808),
            'eu-west-1': (53.3498, -6.2603),
            'ap-southeast-1': (1.3521, 103.8198),
            'ap-northeast-1': (35.6762, 139.6503),
            'us-east-2': (40.3888, -82.7649),
            'eu-central-1': (50.1109, 8.6821),
            'ap-south-1': (19.0760, 72.8777),
        }

        if region in coordinates:
            return coordinates[region]

        # 기본값: 미국 중부
        return (39.8283, -98.5795)

    def export_dashboard_config(self) -> str:
        """
        대시보드 설정을 JSON으로 내보내기

        Returns:
            JSON 문자열
        """
        config = {
            'widgets': self.widget_configs,
            'threat_map_settings': {
                'zoom_level': 3,
                'center': {'latitude': 39.8283, 'longitude': -98.5795}
            },
            'refresh_intervals': {
                'threat_map': 5000,
                'metrics': 10000,
                'response_history': 5000
            },
            'export_time': datetime.utcnow().isoformat()
        }

        return json.dumps(config, indent=2)

    def import_dashboard_config(self, config_json: str) -> Dict:
        """
        JSON 설정을 대시보드에 적용

        Args:
            config_json: JSON 설정 문자열

        Returns:
            {'status': 'success', 'widgets_updated': int}
        """
        try:
            config = json.loads(config_json)
            if 'widgets' in config:
                self.widget_configs.update(config['widgets'])
                return {
                    'status': 'success',
                    'widgets_updated': len(config['widgets'])
                }
            return {'status': 'error', 'message': 'Invalid config'}
        except json.JSONDecodeError:
            return {'status': 'error', 'message': 'Invalid JSON'}
