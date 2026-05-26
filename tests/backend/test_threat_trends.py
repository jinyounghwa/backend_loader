import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda'))
from guardian.ml.threat_trend_analyzer import ThreatTrendAnalyzer


@pytest.fixture
def threat_trend_analyzer():
    mock_db = Mock()
    return ThreatTrendAnalyzer(dynamodb_resource=mock_db)


@pytest.fixture
def time_series_threats():
    threats = []
    base_time = datetime.utcnow()

    for day in range(10):
        for hour in range(24):
            threat_time = (base_time - timedelta(days=day, hours=hour)).isoformat()
            for i in range(max(1, 5 - (hour % 6))):  # 시간대별로 위협 수 변동
                threats.append({
                    'threat_id': f'threat-{day}-{hour}-{i}',
                    'account_id': 'test-account',
                    'threat_type': 'Connection Spike' if hour < 12 else 'Unknown Region',
                    'severity': 5 + (hour % 3),
                    'timestamp': threat_time,
                    'affected_resource_type': 'EC2'
                })

    return threats


def test_analyze_trends(threat_trend_analyzer, time_series_threats):
    """시간대별 추세 분석"""
    mock_table = threat_trend_analyzer.threats_table
    mock_table.query.return_value = {'Items': time_series_threats}

    result = threat_trend_analyzer.analyze_trends('test-account', time_range='24h')

    assert 'hourly_breakdown' in result
    assert 'daily_breakdown' in result
    assert 'peak_hours' in result
    assert 'safe_hours' in result
    assert 'anomaly_hours' in result
    assert 'trend' in result

    # peak_hours와 safe_hours가 겹치지 않아야 함
    peak_set = set(result['peak_hours'])
    safe_set = set(result['safe_hours'])
    assert len(peak_set & safe_set) == 0


def test_get_threat_velocity(threat_trend_analyzer, time_series_threats):
    """위협 속도 계산"""
    mock_table = threat_trend_analyzer.threats_table
    mock_table.query.return_value = {'Items': time_series_threats}

    result = threat_trend_analyzer.get_threat_velocity('test-account', time_window='1h')

    assert 'threat_velocity' in result
    assert 'threats_per_hour' in result
    assert 'total_threats' in result
    assert 'trend' in result
    assert result['threat_velocity'] >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
