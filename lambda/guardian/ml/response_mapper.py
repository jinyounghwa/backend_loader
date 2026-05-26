import json
from typing import Dict, Any, List, Optional


class ResponseMapper:
    """ML 예측 결과를 Playbook으로 매핑"""

    def __init__(self, playbooks_repo=None):
        """
        초기화
        Args:
            playbooks_repo: Playbook 저장소 (DynamoDB)
        """
        self.playbooks_repo = playbooks_repo
        self.threat_playbook_mapping = self._init_threat_mapping()

    def _init_threat_mapping(self) -> Dict[str, List[Dict[str, Any]]]:
        """위협 타입별 기본 Playbook 매핑"""
        return {
            'Unknown Region': [
                {
                    'playbook_id': 'pb-unknown-region-block',
                    'name': 'Block Unknown Region EC2',
                    'type': 'ec2_stop',
                    'severity_threshold': 7,
                    'confidence_threshold': 0.85,
                    'auto_execute': True,
                    'priority': 1,
                    'expected_resolution_time': 300
                }
            ],
            'Unauthorized SSH': [
                {
                    'playbook_id': 'pb-ssh-block',
                    'name': 'Block Unauthorized SSH',
                    'type': 'security_group_update',
                    'severity_threshold': 6,
                    'confidence_threshold': 0.80,
                    'auto_execute': True,
                    'priority': 1,
                    'expected_resolution_time': 120
                },
                {
                    'playbook_id': 'pb-ssh-isolate',
                    'name': 'Isolate Instance',
                    'type': 'ec2_isolate',
                    'severity_threshold': 8,
                    'confidence_threshold': 0.90,
                    'auto_execute': False,
                    'priority': 2,
                    'expected_resolution_time': 180
                }
            ],
            'Data Exfiltration': [
                {
                    'playbook_id': 'pb-exfil-stop',
                    'name': 'Stop Instance Immediately',
                    'type': 'ec2_stop',
                    'severity_threshold': 9,
                    'confidence_threshold': 0.95,
                    'auto_execute': True,
                    'priority': 1,
                    'expected_resolution_time': 60
                },
                {
                    'playbook_id': 'pb-exfil-investigate',
                    'name': 'Enable Detailed Logging',
                    'type': 'cloudtrail_enable',
                    'severity_threshold': 7,
                    'confidence_threshold': 0.85,
                    'auto_execute': True,
                    'priority': 2,
                    'expected_resolution_time': 90
                }
            ],
            'Public S3 Bucket': [
                {
                    'playbook_id': 'pb-s3-block-public',
                    'name': 'Block Public Access',
                    'type': 's3_block_public',
                    'severity_threshold': 8,
                    'confidence_threshold': 0.90,
                    'auto_execute': True,
                    'priority': 1,
                    'expected_resolution_time': 150
                }
            ],
            'Permission Escalation': [
                {
                    'playbook_id': 'pb-iam-revoke',
                    'name': 'Revoke Recent Permissions',
                    'type': 'iam_revoke_recent',
                    'severity_threshold': 8,
                    'confidence_threshold': 0.90,
                    'auto_execute': False,
                    'priority': 1,
                    'expected_resolution_time': 120
                }
            ]
        }

    def map_prediction_to_playbook(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        위협 예측 결과 → 권장 Playbook 매핑

        Args:
            prediction: {
                'threat_type': 'Unknown Region',
                'confidence': 0.95,
                'severity': 8,
                'account_id': 'test-account',
                'timestamp': '2026-05-26T...'
            }

        Returns:
            {
                'threat_type': 'Unknown Region',
                'prediction_confidence': 0.95,
                'threat_severity': 8,
                'recommended_playbooks': [
                    {
                        'playbook_id': 'pb-001',
                        'name': 'Block Unknown Region',
                        'priority': 1,
                        'match_score': 0.98,
                        'auto_execute': True,
                        'expected_resolution_time': 300
                    }
                ],
                'primary_playbook': 'pb-001'
            }
        """
        threat_type = prediction.get('threat_type', 'Unknown')
        confidence = prediction.get('confidence', 0.0)
        severity = prediction.get('severity', 0)

        playbooks = self.threat_playbook_mapping.get(threat_type, [])

        # 조건에 맞는 Playbook 필터링
        recommended = []
        for pb in playbooks:
            # 신뢰도 및 심각도 임계값 확인
            if confidence >= pb['confidence_threshold'] and severity >= pb['severity_threshold']:
                match_score = self._calculate_match_score(confidence, severity, pb)
                recommended.append({
                    'playbook_id': pb['playbook_id'],
                    'name': pb['name'],
                    'type': pb['type'],
                    'priority': pb['priority'],
                    'match_score': match_score,
                    'auto_execute': pb['auto_execute'],
                    'expected_resolution_time': pb['expected_resolution_time'],
                    'severity_threshold': pb['severity_threshold'],
                    'confidence_threshold': pb['confidence_threshold']
                })

        # 우선순위 + 매칭 점수로 정렬 (우선순위 1이 가장 높음)
        recommended.sort(key=lambda x: (x['priority'], -x['match_score']))

        primary_playbook = recommended[0]['playbook_id'] if recommended else None

        return {
            'threat_type': threat_type,
            'prediction_confidence': confidence,
            'threat_severity': severity,
            'recommended_playbooks': recommended,
            'primary_playbook': primary_playbook,
            'total_recommendations': len(recommended)
        }

    def map_cluster_to_playbook(self, cluster: Dict[str, Any]) -> Dict[str, Any]:
        """
        유사 위협 클러스터 → 공통 대응 규칙

        Args:
            cluster: {
                'id': 'C1',
                'threats': ['t1', 't2'],
                'avg_severity': 7.5,
                'representative_threat_type': 'Unknown Region'
            }

        Returns:
            {
                'cluster_id': 'C1',
                'representative_threat': 'Unknown Region',
                'threat_count': 2,
                'avg_severity': 7.5,
                'recommended_playbook': 'pb-001',
                'bulk_remediation': True
            }
        """
        threat_type = cluster.get('representative_threat_type', 'Unknown')
        avg_severity = cluster.get('avg_severity', 0)

        playbooks = self.threat_playbook_mapping.get(threat_type, [])
        recommended = next(
            (pb for pb in playbooks if avg_severity >= pb['severity_threshold']),
            None
        )

        return {
            'cluster_id': cluster.get('id'),
            'representative_threat': threat_type,
            'threat_count': len(cluster.get('threats', [])),
            'avg_severity': avg_severity,
            'recommended_playbook': recommended['playbook_id'] if recommended else None,
            'bulk_remediation': True if recommended else False,
            'playbook_details': recommended
        }

    def map_pattern_to_playbook(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        반복 공격 패턴 → 예방 조치

        Args:
            pattern: {
                'id': 'P1',
                'sequence': ['Unknown Region', 'Unauthorized SSH'],
                'confidence': 0.85,
                'occurrences': 10
            }

        Returns:
            {
                'pattern_id': 'P1',
                'pattern_sequence': ['Unknown Region', 'Unauthorized SSH'],
                'pattern_confidence': 0.85,
                'occurrences': 10,
                'preventive_playbooks': ['pb-001', 'pb-002'],
                'early_intervention': True
            }
        """
        sequence = pattern.get('sequence', [])
        confidence = pattern.get('confidence', 0.0)
        occurrences = pattern.get('occurrences', 0)

        # 패턴의 첫 단계에서 미리 차단하는 Playbook 선택
        first_threat = sequence[0] if sequence else None
        preventive_playbooks = []

        if first_threat:
            playbooks = self.threat_playbook_mapping.get(first_threat, [])
            preventive_playbooks = [pb['playbook_id'] for pb in playbooks if pb['auto_execute']]

        return {
            'pattern_id': pattern.get('id'),
            'pattern_sequence': sequence,
            'pattern_confidence': confidence,
            'occurrences': occurrences,
            'preventive_playbooks': preventive_playbooks,
            'early_intervention': True if preventive_playbooks else False,
            'intervention_point': first_threat
        }

    def _calculate_match_score(self, confidence: float, severity: int, playbook: Dict) -> float:
        """
        매칭 점수 계산 (0-1)

        Args:
            confidence: 예측 신뢰도 (0-1)
            severity: 위협 심각도 (0-10)
            playbook: Playbook 설정

        Returns:
            float: 매칭 점수 (0-1)
        """
        # 신뢰도: 0.5점
        confidence_score = (confidence - playbook['confidence_threshold']) / (1.0 - playbook['confidence_threshold'])
        confidence_score = max(0, min(1, confidence_score)) * 0.5

        # 심각도: 0.3점
        severity_score = (severity - playbook['severity_threshold']) / (10 - playbook['severity_threshold'])
        severity_score = max(0, min(1, severity_score)) * 0.3

        # 기본점: 0.2점
        base_score = 0.2

        return confidence_score + severity_score + base_score

    def get_playbook_details(self, playbook_id: str) -> Optional[Dict[str, Any]]:
        """
        Playbook 상세 정보 조회

        Args:
            playbook_id: Playbook ID

        Returns:
            Playbook 정보 또는 None
        """
        for threat_type, playbooks in self.threat_playbook_mapping.items():
            for pb in playbooks:
                if pb['playbook_id'] == playbook_id:
                    return pb
        return None
