import pytest
from guardian.detectors.statistical_anomaly import StatisticalAnomalyDetector


class TestStatisticalAnomalyDetector:
    """StatisticalAnomalyDetector 테스트"""

    @pytest.fixture
    def detector(self):
        """StatisticalAnomalyDetector 인스턴스"""
        return StatisticalAnomalyDetector()

    @pytest.fixture
    def historical_data(self):
        """과거 정상 데이터"""
        return [
            {'event_count': 100, 'latency_ms': 50, 'error_rate': 0.01},
            {'event_count': 105, 'latency_ms': 52, 'error_rate': 0.01},
            {'event_count': 98, 'latency_ms': 48, 'error_rate': 0.02},
            {'event_count': 102, 'latency_ms': 51, 'error_rate': 0.01},
            {'event_count': 110, 'latency_ms': 55, 'error_rate': 0.02},
            {'event_count': 95, 'latency_ms': 47, 'error_rate': 0.01},
            {'event_count': 108, 'latency_ms': 53, 'error_rate': 0.02},
        ]

    def test_train_baseline(self, detector, historical_data):
        """기준선 학습"""
        result = detector.train_baseline(historical_data, window_days=7)

        assert result['baseline_id'] is not None
        assert 'metrics' in result
        assert 'trained_at' in result
        assert 'event_count' in result['metrics']
        assert 'mean' in result['metrics']['event_count']
        assert 'std_dev' in result['metrics']['event_count']
        assert 'percentile_95' in result['metrics']['event_count']
        assert 'percentile_99' in result['metrics']['event_count']

    def test_detect_normal_event(self, detector, historical_data):
        """정상 이벤트 탐지"""
        baseline_result = detector.train_baseline(historical_data)
        baseline = detector.baselines[baseline_result['baseline_id']]

        # 정상 범위 이벤트
        normal_event = {
            'event_count': 103,
            'latency_ms': 51,
            'error_rate': 0.01
        }

        result = detector.detect_anomaly(normal_event, baseline)

        assert result['is_anomaly'] is False
        assert result['z_score'] <= 1.5
        assert result['severity'] in ['LOW', 'MEDIUM']

    def test_detect_volumetric_anomaly(self, detector, historical_data):
        """볼륨 이상 탐지 (비정상적으로 많은 이벤트)"""
        baseline_result = detector.train_baseline(historical_data)
        baseline = detector.baselines[baseline_result['baseline_id']]

        # 비정상적으로 많은 이벤트
        volumetric_event = {
            'event_count': 500,
            'latency_ms': 51,
            'error_rate': 0.01
        }

        result = detector.detect_anomaly(volumetric_event, baseline)

        assert result['is_anomaly'] is True
        assert result['anomaly_type'] == 'volumetric'
        assert result['z_score'] > 1.5
        assert result['severity'] in ['HIGH', 'CRITICAL']

    def test_detect_behavioral_anomaly(self, detector, historical_data):
        """행동 이상 탐지 (평소와 다른 지연시간)"""
        baseline_result = detector.train_baseline(historical_data)
        baseline = detector.baselines[baseline_result['baseline_id']]

        # 비정상적으로 높은 지연
        behavioral_event = {
            'event_count': 100,
            'latency_ms': 200,
            'error_rate': 0.01
        }

        result = detector.detect_anomaly(behavioral_event, baseline)

        assert result['is_anomaly'] is True
        assert result['anomaly_type'] == 'behavioral'
        assert result['z_score'] > 1.5

    def test_detect_pattern_anomaly(self, detector, historical_data):
        """패턴 이상 탐지 (비정상적인 에러율)"""
        baseline_result = detector.train_baseline(historical_data)
        baseline = detector.baselines[baseline_result['baseline_id']]

        # 비정상적으로 높은 에러율
        pattern_event = {
            'event_count': 100,
            'latency_ms': 50,
            'error_rate': 0.5
        }

        result = detector.detect_anomaly(pattern_event, baseline)

        assert result['is_anomaly'] is True
        assert result['anomaly_type'] == 'pattern'

    def test_get_anomaly_insights(self, detector, historical_data):
        """이상에 대한 인사이트"""
        baseline_result = detector.train_baseline(historical_data)
        baseline = detector.baselines[baseline_result['baseline_id']]

        event = {
            'event_count': 200,
            'latency_ms': 100,
            'error_rate': 0.1
        }

        insights = detector.get_anomaly_insights(event, baseline)

        assert 'event_count' in insights or 'latency' in insights
        if 'event_count' in insights:
            assert 'expected_value' in insights['event_count']
            assert 'actual_value' in insights['event_count']
            assert 'deviation_percent' in insights['event_count']
            assert 'recommendation' in insights['event_count']

    def test_update_baseline_incremental(self, detector, historical_data):
        """점진적 기준선 업데이트"""
        baseline_result = detector.train_baseline(historical_data)
        baseline_id = baseline_result['baseline_id']
        original_mean = baseline_result['metrics']['event_count']['mean']

        # 새 데이터로 기준선 업데이트
        new_data = [
            {'event_count': 150, 'latency_ms': 60, 'error_rate': 0.03},
            {'event_count': 155, 'latency_ms': 62, 'error_rate': 0.03}
        ]
        detector.update_baseline(new_data)

        # 기준선이 업데이트됨
        updated_baseline = detector.baselines[baseline_id]
        updated_mean = updated_baseline['metrics']['event_count']['mean']

        # 새 데이터 쪽으로 이동하지만 완전히 변경되지 않음 (가중 평균)
        assert updated_mean != original_mean
        assert original_mean < updated_mean < 150

    def test_multi_feature_anomaly(self, detector, historical_data):
        """다중 특성 이상 탐지"""
        baseline_result = detector.train_baseline(historical_data)
        baseline = detector.baselines[baseline_result['baseline_id']]

        # 여러 특성이 동시에 이상
        multi_feature_event = {
            'event_count': 500,
            'latency_ms': 300,
            'error_rate': 0.5
        }

        result = detector.detect_anomaly(multi_feature_event, baseline)

        assert result['is_anomaly'] is True
        assert result['z_score'] > 2.0
        assert result['severity'] in ['HIGH', 'CRITICAL']

    def test_anomaly_scoring(self, detector, historical_data):
        """이상 점수 계산"""
        baseline_result = detector.train_baseline(historical_data)
        baseline = detector.baselines[baseline_result['baseline_id']]

        # 다양한 이상 정도의 이벤트들
        events = [
            {'event_count': 101, 'latency_ms': 50, 'error_rate': 0.01},  # 거의 정상
            {'event_count': 200, 'latency_ms': 100, 'error_rate': 0.05},  # 중간 이상
            {'event_count': 500, 'latency_ms': 300, 'error_rate': 0.5}   # 심각한 이상
        ]

        results = []
        for event in events:
            result = detector.detect_anomaly(event, baseline)
            results.append(result)

        # Z-score와 신뢰도가 일관성 있게 증가
        z_scores = [r['z_score'] for r in results]
        confidences = [r['confidence'] for r in results]

        # 첫 번째는 정상, 나머지는 이상
        assert results[0]['is_anomaly'] is False
        assert results[1]['is_anomaly'] is True
        assert results[2]['is_anomaly'] is True

        # Z-score가 증가 (절댓값 기준)
        assert abs(z_scores[0]) < abs(z_scores[1]) < abs(z_scores[2])

        # 신뢰도는 비감소 (큰 Z-score는 1.0으로 캡됨)
        assert confidences[0] <= confidences[1]
        assert confidences[1] <= confidences[2]

    def test_empty_data_handling(self, detector):
        """빈 데이터 처리"""
        result = detector.train_baseline([], window_days=7)

        assert result['baseline_id'] is None
        assert 'error' in result
