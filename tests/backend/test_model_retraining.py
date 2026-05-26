import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from guardian.ml.feature_engineer import FeatureEngineer
from guardian.ml.model_retrainer import ModelRetrainer


class TestFeatureEngineer:
    """FeatureEngineer 테스트"""

    @pytest.fixture
    def feature_engineer(self):
        return FeatureEngineer()

    @pytest.fixture
    def sample_feedback_logs(self):
        """샘플 피드백 로그"""
        return [
            {
                'threat_id': 'threat_1',
                'threat_type': 'connection_spike',
                'severity': 'HIGH',
                'is_correct': True,
                'timestamp': datetime.utcnow().isoformat(),
                'evidence': ['log1', 'log2', 'log3'],
                'detection_latency_sec': 30,
                'action_success_rate': 0.95,
                'account_id': 'acc_123',
                'source_ip_anomaly': False
            },
            {
                'threat_id': 'threat_2',
                'threat_type': 'unknown_region',
                'severity': 'MEDIUM',
                'is_correct': False,
                'timestamp': (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                'evidence': ['log4'],
                'detection_latency_sec': 45,
                'action_success_rate': 0.5,
                'account_id': 'acc_456',
                'source_ip_anomaly': True
            }
        ]

    def test_extract_features_basic(self, feature_engineer, sample_feedback_logs):
        """피드백 로그 → 특성 벡터 정상 추출"""
        X, y = feature_engineer.extract_features(sample_feedback_logs)

        assert len(X) == 2
        assert len(y) == 2
        assert y[0] == 1  # is_correct=True
        assert y[1] == 0  # is_correct=False
        assert X.shape[1] > 0  # 특성 벡터 차원

    def test_extract_features_empty(self, feature_engineer):
        """피드백 없음 → 빈 벡터 반환"""
        X, y = feature_engineer.extract_features([])

        assert len(X) == 0
        assert len(y) == 0

    def test_engineer_single_feedback(self, feature_engineer, sample_feedback_logs):
        """단일 피드백 → 특성 딕셔너리"""
        feedback = sample_feedback_logs[0]
        features = feature_engineer.engineer_single_feedback(feedback)

        assert 'threat_type_id' in features
        assert 'severity_numeric' in features
        assert 'evidence_count' in features
        assert 'detection_latency_sec' in features
        assert features['evidence_count'] == 3
        assert features['severity_numeric'] == 2  # HIGH = 2

    def test_engineer_batch_features(self, feature_engineer, sample_feedback_logs):
        """배치 데이터 → 집계 특성"""
        threats = sample_feedback_logs
        batch_features = feature_engineer.engineer_batch_features(threats)

        assert batch_features['num_threats_detected'] == 2
        assert 'threat_type_distribution' in batch_features
        assert 'severity_distribution' in batch_features
        assert batch_features['affected_account_ids'] == 2

    def test_extract_threat_patterns(self, feature_engineer):
        """위협-대응-결과 패턴 추출"""
        detections = [
            {'threat_id': 't1', 'threat_type': 'connection_spike', 'account_id': 'acc_1', 'timestamp': datetime.utcnow().isoformat()}
        ]
        actions = [
            {'action_id': 'a1', 'threat_id': 't1', 'action_type': 'stop_instance'}
        ]
        outcomes = [
            {'action_id': 'a1', 'success': True}
        ]

        patterns = feature_engineer.extract_threat_patterns(detections, actions, outcomes)

        assert 'threat_to_action_mapping' in patterns
        assert 'action_success_patterns' in patterns
        assert 'temporal_patterns' in patterns
        assert 'account_vulnerability_profile' in patterns


class TestModelRetrainer:
    """ModelRetrainer 테스트"""

    @pytest.fixture
    def mock_dependencies(self):
        """의존성 Mock"""
        model_storage = Mock()
        feedback_repo = Mock()
        feature_engineer = FeatureEngineer()

        return {
            'model_storage': model_storage,
            'feedback_repo': feedback_repo,
            'feature_engineer': feature_engineer
        }

    @pytest.fixture
    def retrainer(self, mock_dependencies):
        return ModelRetrainer(
            model_storage=mock_dependencies['model_storage'],
            feedback_repo=mock_dependencies['feedback_repo'],
            feature_engineer=mock_dependencies['feature_engineer']
        )

    @pytest.fixture
    def sample_feedback_with_features(self):
        """특성 벡터를 포함한 샘플 피드백"""
        logs = []
        for i in range(20):
            logs.append({
                'threat_id': f'threat_{i}',
                'threat_type': 'connection_spike' if i % 2 == 0 else 'unknown_region',
                'severity': ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'][i % 4],
                'is_correct': i % 3 != 0,  # 2/3가 정탐
                'timestamp': (datetime.utcnow() - timedelta(days=i)).isoformat(),
                'evidence': [f'log_{i}_{j}' for j in range(i % 5 + 1)],
                'detection_latency_sec': 20 + i,
                'action_success_rate': 0.7 + (i % 3) * 0.1,
                'account_id': f'acc_{i % 5}',
                'source_ip_anomaly': i % 5 == 0
            })
        return logs

    def test_retrain_with_feedback(self, retrainer, mock_dependencies, sample_feedback_with_features):
        """피드백으로 모델 재학습 → 메트릭 반환"""
        mock_dependencies['feedback_repo'].query_recent.return_value = sample_feedback_with_features
        mock_dependencies['model_storage'].get_previous_version_metrics.return_value = {
            'accuracy': 0.75,
            'precision': 0.70,
            'recall': 0.80,
            'f1_score': 0.75
        }
        mock_dependencies['model_storage'].save_version.return_value = 'v1.0.1'

        result = retrainer.retrain_from_feedback(lookback_days=30)

        assert result['model_version'] == 'v1.0.1'
        assert result['training_samples'] == len(sample_feedback_with_features)
        assert 'metrics' in result
        assert 'accuracy' in result['metrics']
        assert 'precision' in result['metrics']
        assert 'recall' in result['metrics']
        assert 'f1_score' in result['metrics']

    def test_retrain_incremental(self, retrainer, mock_dependencies, sample_feedback_with_features):
        """증분 학습 → 메모리 효율성"""
        mock_dependencies['feedback_repo'].query_recent.return_value = sample_feedback_with_features
        mock_dependencies['model_storage'].get_previous_version_metrics.return_value = {}
        mock_dependencies['model_storage'].save_version.return_value = 'v1.0.0'

        result1 = retrainer.retrain_from_feedback(lookback_days=30)
        result2 = retrainer.retrain_from_feedback(lookback_days=30)

        # 두 번 재학습해도 성공
        assert result1['model_version'] is not None
        assert result2['model_version'] is not None

    def test_model_version_management(self, retrainer, mock_dependencies, sample_feedback_with_features):
        """모델 버전 저장/로드 정상"""
        mock_dependencies['feedback_repo'].query_recent.return_value = sample_feedback_with_features
        mock_dependencies['model_storage'].get_previous_version_metrics.return_value = {}
        mock_dependencies['model_storage'].save_version.return_value = 'v1.0.0'

        result = retrainer.retrain_from_feedback()

        # 저장된 모델 버전 확인
        mock_dependencies['model_storage'].save_version.assert_called_once()
        call_args = mock_dependencies['model_storage'].save_version.call_args
        assert 'model' in call_args.kwargs or len(call_args.args) > 0

    def test_compare_metrics_improvement(self, retrainer, mock_dependencies):
        """이전 모델 대비 개선도 계산 정확"""
        new_metrics = {
            'accuracy': 0.82,
            'precision': 0.75,
            'recall': 0.85,
            'f1_score': 0.80
        }

        mock_dependencies['model_storage'].get_previous_version_metrics.return_value = {
            'accuracy': 0.75,
            'precision': 0.70,
            'recall': 0.80,
            'f1_score': 0.75
        }

        improvements = retrainer._compare_with_previous(new_metrics)

        assert improvements['accuracy_improvement'] == pytest.approx(0.07)
        assert improvements['precision_improvement'] == pytest.approx(0.05)
        assert improvements['recall_improvement'] == pytest.approx(0.05)
        assert improvements['f1_improvement'] == pytest.approx(0.05)

    def test_should_deploy_threshold(self, retrainer):
        """배포 임계값 확인"""
        improvements = {
            'f1_improvement': 0.03,  # 3% > 2% 임계값
            'accuracy_improvement': 0.02,
            'precision_improvement': 0.01,
            'recall_improvement': 0.02
        }

        should_deploy = retrainer.should_deploy_new_model(improvements, threshold=0.02)
        assert should_deploy is True

    def test_deploy_new_model(self, retrainer, mock_dependencies):
        """신규 모델 배포 실행"""
        mock_dependencies['model_storage'].set_active_version.return_value = None

        result = retrainer.deploy_new_model('v1.0.1')

        assert result['status'] == 'success'
        assert result['deployed_version'] == 'v1.0.1'
        mock_dependencies['model_storage'].set_active_version.assert_called_once_with('v1.0.1')

    def test_evaluate_model(self, retrainer):
        """모델 평가"""
        from sklearn.ensemble import RandomForestClassifier

        X = np.random.rand(50, 10)
        y = np.random.randint(0, 2, 50)

        model = RandomForestClassifier(random_state=42)
        model.fit(X, y)

        metrics = retrainer._evaluate_model(model, X, y)

        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'confusion_matrix' in metrics
        assert 0 <= metrics['accuracy'] <= 1
        assert 0 <= metrics['f1_score'] <= 1
