import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from guardian.orchestration.pipeline_orchestrator import PipelineOrchestrator
from guardian.orchestration.pipeline_metrics import PipelineMetrics


class TestPipelineOrchestrator:
    """PipelineOrchestrator 테스트"""

    @pytest.fixture
    def mock_stages(self):
        """모든 파이프라인 단계 Mock"""
        mock_anomaly_detector = AsyncMock()
        mock_anomaly_detector.detect = AsyncMock(return_value=[
            {
                'threat_id': 'threat_1',
                'threat_type': 'connection_spike',
                'severity': 'HIGH'
            }
        ])

        mock_predictor = AsyncMock()
        mock_predictor.predict_batch = AsyncMock(return_value=[
            {'threat_id': 'threat_1', 'risk_score': 0.85}
        ])

        mock_playbook_mapper = AsyncMock()
        mock_playbook_mapper.map_threats_to_playbooks = AsyncMock(return_value=[
            {'threat_id': 'threat_1', 'playbook_id': 'pb_1'}
        ])

        mock_action_executor = AsyncMock()
        mock_action_executor.execute_playbooks = AsyncMock(return_value=[
            {'action_id': 'action_1', 'status': 'SUCCESS'}
        ])

        mock_feedback_engine = AsyncMock()
        mock_feedback_engine.collect_feedback = AsyncMock(return_value=[
            {'feedback_id': 'fb_1', 'threat_id': 'threat_1'}
        ])

        mock_retrainer = AsyncMock()

        return {
            'anomaly_detector': mock_anomaly_detector,
            'predictor': mock_predictor,
            'playbook_mapper': mock_playbook_mapper,
            'action_executor': mock_action_executor,
            'feedback_engine': mock_feedback_engine,
            'retrainer': mock_retrainer
        }

    @pytest.fixture
    def mock_metrics_storage(self):
        return Mock()

    @pytest.fixture
    def orchestrator(self, mock_stages, mock_metrics_storage):
        return PipelineOrchestrator(
            anomaly_detector=mock_stages['anomaly_detector'],
            predictor=mock_stages['predictor'],
            playbook_mapper=mock_stages['playbook_mapper'],
            action_executor=mock_stages['action_executor'],
            feedback_engine=mock_stages['feedback_engine'],
            retrainer=mock_stages['retrainer'],
            metrics_storage=mock_metrics_storage
        )

    @pytest.mark.asyncio
    async def test_pipeline_orchestration_full_path(self, orchestrator, mock_stages):
        """모든 단계 정상 실행 → HEALTHY"""
        result = await orchestrator.orchestrate('acc_123')

        assert result['status'] == 'HEALTHY'
        assert result['pipeline_id'] is not None
        assert result['total_threats'] == 1
        assert len(result['stages']) > 0
        mock_stages['anomaly_detector'].detect.assert_called_once_with('acc_123')

    @pytest.mark.asyncio
    async def test_pipeline_one_stage_failure(self, orchestrator, mock_stages):
        """1개 단계 실패 → DEGRADED"""
        # prediction 단계 실패
        mock_stages['predictor'].predict_batch.side_effect = Exception("Prediction failed")

        result = await orchestrator.orchestrate('acc_123')

        assert result['status'] == 'DEGRADED'
        assert len(result['errors']) > 0
        assert any('Prediction failed' in e for e in result['errors'])

    @pytest.mark.asyncio
    async def test_pipeline_multiple_failures(self, orchestrator, mock_stages):
        """3개 이상 단계 실패 → FAILED"""
        # 여러 단계 실패
        mock_stages['predictor'].predict_batch.side_effect = Exception("Prediction failed")
        mock_stages['playbook_mapper'].map_threats_to_playbooks.side_effect = Exception("Mapping failed")
        mock_stages['action_executor'].execute_playbooks.side_effect = Exception("Execution failed")

        result = await orchestrator.orchestrate('acc_123')

        assert result['status'] == 'FAILED'
        assert len(result['errors']) >= 3

    @pytest.mark.asyncio
    async def test_pipeline_latency_tracking(self, orchestrator):
        """각 단계 지연 시간 기록"""
        result = await orchestrator.orchestrate('acc_123')

        # 모든 단계가 latency_ms 기록
        for stage_result in result['stages'].values():
            if stage_result.get('status') in ['SUCCESS', 'FAILED']:
                assert 'latency_ms' in stage_result
                assert stage_result['latency_ms'] >= 0

    @pytest.mark.asyncio
    async def test_pipeline_error_logging(self, orchestrator, mock_stages):
        """에러 메시지 정상 저장"""
        mock_stages['predictor'].predict_batch.side_effect = Exception("Test error message")

        result = await orchestrator.orchestrate('acc_123')

        assert any('Test error message' in e for e in result['errors'])

    @pytest.mark.asyncio
    async def test_pipeline_health_calculation(self, orchestrator, mock_metrics_storage):
        """성공률 계산 정확"""
        # PipelineMetrics의 health 계산 테스트는 별도로 수행
        result = await orchestrator.orchestrate('acc_123')

        assert 'total_threats' in result
        assert 'mitigated_threats' in result
        assert result['mitigated_threats'] <= result['total_threats']

    @pytest.mark.asyncio
    async def test_pipeline_no_threats_detected(self, orchestrator, mock_stages):
        """위협이 없을 때 후속 단계 스킵"""
        # 위협 없음
        mock_stages['anomaly_detector'].detect.return_value = []

        result = await orchestrator.orchestrate('acc_123')

        assert result['total_threats'] == 0
        assert result['stages']['prediction'].get('status') == 'SKIPPED'
        assert result['stages']['playbook_mapping'].get('status') == 'SKIPPED'


class TestPipelineMetrics:
    """PipelineMetrics 테스트"""

    @pytest.fixture
    def mock_table(self):
        return Mock()

    @pytest.fixture
    def metrics(self, mock_table):
        return PipelineMetrics(mock_table)

    @pytest.mark.asyncio
    async def test_record_pipeline_execution(self, metrics, mock_table):
        """파이프라인 실행 기록 저장"""
        execution = {
            'pipeline_id': 'pipe_1',
            'status': 'HEALTHY',
            'stages': {},
            'errors': [],
            'total_threats': 5,
            'mitigated_threats': 4,
            'end_to_end_latency_ms': 1500.0
        }

        await metrics.record_pipeline_execution(execution)

        mock_table.put_item.assert_called_once_with(Item=execution)

    @pytest.mark.asyncio
    async def test_pipeline_health_empty(self, metrics):
        """빈 상태에서 health 조회"""
        health = await metrics.get_pipeline_health()

        assert health['overall_status'] == 'UNKNOWN'
        assert health['total_executions'] == 0
        assert health['success_rate'] == 0.0

    @pytest.mark.asyncio
    async def test_determine_overall_status(self, metrics):
        """전체 상태 결정"""
        # 성공률 95% 이상 → HEALTHY
        assert metrics._determine_overall_status(19, 1, 0, 20) == 'HEALTHY'

        # 성공률 75-95% → DEGRADED
        assert metrics._determine_overall_status(16, 4, 0, 20) == 'DEGRADED'

        # 성공률 75% 미만 → FAILED
        assert metrics._determine_overall_status(14, 6, 0, 20) == 'FAILED'

    @pytest.mark.asyncio
    async def test_stage_success_rates(self, metrics):
        """단계별 성공률 계산"""
        executions = [
            {
                'pipeline_id': 'pipe_1',
                'stages': {
                    'anomaly_detection': {'status': 'SUCCESS', 'latency_ms': 100},
                    'prediction': {'status': 'SUCCESS', 'latency_ms': 200}
                }
            },
            {
                'pipeline_id': 'pipe_2',
                'stages': {
                    'anomaly_detection': {'status': 'SUCCESS', 'latency_ms': 110},
                    'prediction': {'status': 'FAILED', 'latency_ms': 50}
                }
            }
        ]

        rates = metrics._calculate_stage_success_rates(executions)

        assert rates['anomaly_detection'] == 1.0  # 2/2
        assert rates['prediction'] == 0.5  # 1/2

    @pytest.mark.asyncio
    async def test_error_summarization(self, metrics):
        """에러 요약"""
        executions = [
            {'errors': ['Error A', 'Error B']},
            {'errors': ['Error A', 'Error C']},
            {'errors': []}
        ]

        summary = metrics._summarize_errors(executions)

        assert summary['Error A'] == 2
        assert summary['Error B'] == 1
        assert summary['Error C'] == 1
