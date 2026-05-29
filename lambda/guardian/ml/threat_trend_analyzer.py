import json
import boto3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

try:
    import numpy as np
except ImportError:
    np = None


class ThreatTrendAnalyzer:
    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.threats_table = self.dynamodb.Table('guardian-threats')

    def analyze_trends(self, account_id: str, time_range: str = '24h') -> Dict:
        """
        시간대별 위협 분포 분석

        Args:
            account_id: AWS account ID
            time_range: '24h', '7d', '30d'

        Returns:
            {
                'hourly_breakdown': [...],
                'daily_breakdown': [...],
                'peak_hours': [...],
                'safe_hours': [...],
                'anomaly_hours': [...],
                'trend': 'increasing|stable|decreasing'
            }
        """
        lookback_hours = self._parse_time_range(time_range)
        threats = self._get_threats_by_time_range(account_id, lookback_hours)

        hourly_breakdown = self._aggregate_threats_by_hour(threats, lookback_hours)
        daily_breakdown = self._aggregate_threats_by_day(threats, lookback_hours)

        peak_hours = self._find_peak_hours(hourly_breakdown)
        safe_hours = self._find_safe_hours(hourly_breakdown)
        anomaly_hours = self._find_anomaly_hours(hourly_breakdown)

        trend = self._calculate_trend(daily_breakdown)

        return {
            'account_id': account_id,
            'time_range': time_range,
            'hourly_breakdown': hourly_breakdown,
            'daily_breakdown': daily_breakdown,
            'peak_hours': peak_hours,
            'safe_hours': safe_hours,
            'anomaly_hours': anomaly_hours,
            'trend': trend,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def get_threat_velocity(self, account_id: str, time_window: str = '1h') -> Dict:
        """위협 발생 속도 (위협/시간)"""
        window_hours = self._parse_time_window(time_window)
        threats = self._get_threats_by_time_range(account_id, window_hours)

        if not threats or window_hours == 0:
            return {
                'account_id': account_id,
                'time_window': time_window,
                'threat_velocity': 0.0,
                'threats_per_hour': 0.0,
                'trend': 'stable'
            }

        threat_count = len(threats)
        threat_velocity = threat_count / window_hours if window_hours > 0 else 0.0

        # 최근 절반과 이전 절반 비교
        mid_point = len(threats) // 2
        if mid_point > 0:
            recent_count = len(threats[mid_point:])
            previous_count = len(threats[:mid_point])
            trend = 'increasing' if recent_count > previous_count else ('decreasing' if recent_count < previous_count else 'stable')
        else:
            trend = 'stable'

        return {
            'account_id': account_id,
            'time_window': time_window,
            'threat_velocity': float(threat_velocity),
            'threats_per_hour': float(threat_velocity),
            'total_threats': threat_count,
            'trend': trend,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def get_threat_density(self, account_id: str, time_window: str = '1h') -> Dict:
        """시간 윈도우 내 위협 밀도"""
        window_hours = self._parse_time_window(time_window)
        threats = self._get_threats_by_time_range(account_id, window_hours)

        if not threats or window_hours == 0:
            return {
                'account_id': account_id,
                'time_window': time_window,
                'threat_density': 0.0,
                'severity_distribution': {},
                'resource_distribution': {}
            }

        threat_count = len(threats)
        density = threat_count / window_hours if window_hours > 0 else 0.0

        # 심각도 분포
        severity_dist = {}
        for threat in threats:
            severity = threat.get('severity', 0)
            severity_dist[severity] = severity_dist.get(severity, 0) + 1

        # 리소스 분포
        resource_dist = {}
        for threat in threats:
            resource_type = threat.get('affected_resource_type', 'unknown')
            resource_dist[resource_type] = resource_dist.get(resource_type, 0) + 1

        return {
            'account_id': account_id,
            'time_window': time_window,
            'threat_density': float(density),
            'total_threats': threat_count,
            'severity_distribution': severity_dist,
            'resource_distribution': resource_dist,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def _parse_time_range(self, time_range: str) -> int:
        """시간 범위 파싱"""
        if time_range == '24h':
            return 24
        elif time_range == '7d':
            return 168
        elif time_range == '30d':
            return 720
        else:
            return 24

    def _parse_time_window(self, time_window: str) -> int:
        """시간 윈도우 파싱"""
        if time_window == '1h':
            return 1
        elif time_window == '1d':
            return 24
        elif time_window == '1w':
            return 168
        else:
            return 1

    def _get_threats_by_time_range(self, account_id: str, lookback_hours: int) -> List[Dict]:
        """시간 범위에 해당하는 위협 조회"""
        start_time = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=lookback_hours)).isoformat()

        try:
            response = self.threats_table.query(
                KeyConditionExpression='account_id = :aid AND #ts > :start',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':aid': account_id,
                    ':start': start_time
                },
                Limit=1000
            )
            return sorted(response.get('Items', []), key=lambda t: t.get('timestamp', ''))
        except Exception:
            return []

    def _aggregate_threats_by_hour(self, threats: List[Dict], lookback_hours: int) -> List[Dict]:
        """시간별로 위협 집계"""
        hourly_counts = {}

        for threat in threats:
            threat_time = threat.get('timestamp', '')
            if threat_time:
                hour = threat_time[:13]  # YYYY-MM-DDTHH
                hourly_counts[hour] = hourly_counts.get(hour, {
                    'count': 0,
                    'total_severity': 0,
                    'threat_types': {}
                })

                hourly_counts[hour]['count'] += 1
                hourly_counts[hour]['total_severity'] += threat.get('severity', 0)

                threat_type = threat.get('threat_type', 'unknown')
                hourly_counts[hour]['threat_types'][threat_type] = hourly_counts[hour]['threat_types'].get(threat_type, 0) + 1

        result = []
        for hour in sorted(hourly_counts.keys()):
            data = hourly_counts[hour]
            avg_severity = data['total_severity'] / data['count'] if data['count'] > 0 else 0

            result.append({
                'hour': hour,
                'threats': data['count'],
                'avg_severity': float(avg_severity),
                'threat_types': data['threat_types']
            })

        return result

    def _aggregate_threats_by_day(self, threats: List[Dict], lookback_hours: int) -> List[Dict]:
        """일별로 위협 집계"""
        daily_counts = {}

        for threat in threats:
            threat_time = threat.get('timestamp', '')
            if threat_time:
                day = threat_time[:10]  # YYYY-MM-DD
                daily_counts[day] = daily_counts.get(day, {
                    'count': 0,
                    'total_severity': 0
                })

                daily_counts[day]['count'] += 1
                daily_counts[day]['total_severity'] += threat.get('severity', 0)

        result = []
        for day in sorted(daily_counts.keys()):
            data = daily_counts[day]
            avg_severity = data['total_severity'] / data['count'] if data['count'] > 0 else 0

            result.append({
                'day': day,
                'threats': data['count'],
                'avg_severity': float(avg_severity)
            })

        return result

    def _find_peak_hours(self, hourly_breakdown: List[Dict]) -> List[str]:
        """위협이 가장 많은 시간 찾기"""
        if not hourly_breakdown:
            return []

        sorted_hours = sorted(hourly_breakdown, key=lambda h: h['threats'], reverse=True)
        peak_threshold = max(1, len(hourly_breakdown) // 5)

        return [h['hour'] for h in sorted_hours[:peak_threshold]]

    def _find_safe_hours(self, hourly_breakdown: List[Dict]) -> List[str]:
        """위협이 가장 적은 시간 찾기"""
        if not hourly_breakdown:
            return []

        sorted_hours = sorted(hourly_breakdown, key=lambda h: h['threats'])
        safe_threshold = max(1, len(hourly_breakdown) // 5)

        return [h['hour'] for h in sorted_hours[:safe_threshold]]

    def _find_anomaly_hours(self, hourly_breakdown: List[Dict]) -> List[str]:
        """비정상적인 위협이 많은 시간 찾기"""
        if len(hourly_breakdown) < 2:
            return []

        threat_counts = [h['threats'] for h in hourly_breakdown]

        if np is not None:
            threat_counts = np.array(threat_counts)
            mean = np.mean(threat_counts)
            std = np.std(threat_counts)
        else:
            # Pure Python calculation
            mean = sum(threat_counts) / len(threat_counts)
            variance = sum((x - mean) ** 2 for x in threat_counts) / len(threat_counts)
            std = variance ** 0.5

        anomaly_hours = []
        for hour_data in hourly_breakdown:
            count = hour_data['threats']
            # 평균 + 1.5*std 초과하면 이상
            if count > mean + 1.5 * std:
                anomaly_hours.append(hour_data['hour'])

        return anomaly_hours

    def _calculate_trend(self, daily_breakdown: List[Dict]) -> str:
        """일별 추세 계산"""
        if len(daily_breakdown) < 2:
            return 'stable'

        threat_counts = [d['threats'] for d in daily_breakdown]

        if np is not None:
            first_half = np.mean(threat_counts[:len(threat_counts)//2])
            second_half = np.mean(threat_counts[len(threat_counts)//2:])
        else:
            mid = len(threat_counts) // 2
            first_half = sum(threat_counts[:mid]) / len(threat_counts[:mid]) if threat_counts[:mid] else 0
            second_half = sum(threat_counts[mid:]) / len(threat_counts[mid:]) if threat_counts[mid:] else 0

        if first_half == 0:
            return 'stable'

        if second_half > first_half * 1.2:
            return 'increasing'
        elif second_half < first_half * 0.8:
            return 'decreasing'
        else:
            return 'stable'
