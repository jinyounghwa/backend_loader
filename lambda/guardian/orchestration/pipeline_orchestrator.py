import logging
import uuid
import time
from typing import Dict, List, Any
from datetime import datetime
from guardian.orchestration.pipeline_metrics import PipelineMetrics

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """위협 탐지부터 피드백 수집까지 전체 파이프라인 오케스트레이션"""

    # 파이프라인 단계
    STAGES = [
        'anomaly_detection',
        'prediction',
        'playbook_mapping',
        'action_execution',
        'feedback_collection',
        'model_retraining'
    ]

    def __init__(
        self,
        anomaly_detector,
        predictor,
        playbook_mapper,
        action_executor,
        feedback_engine,
        retrainer,
        metrics_storage
    ):
        """
        Args:
            anomaly_detector: AnomalyDetector 인스턴스
            predictor: ThreatPredictor 인스턴스
            playbook_mapper: PlaybookMapper 인스턴스
            action_executor: ActionExecutor 인스턴스
            feedback_engine: FeedbackEngine 인스턴스
            retrainer: ModelRetrainer 인스턴스
            metrics_storage: 메트릭 저장소
        """
        self.stages = {
            'anomaly_detection': anomaly_detector,
            'prediction': predictor,
            'playbook_mapping': playbook_mapper,
            'action_execution': action_executor,
            'feedback_collection': feedback_engine,
            'model_retraining': retrainer
        }
        self.metrics = PipelineMetrics(metrics_storage)

    async def orchestrate(self, account_id: str) -> Dict[str, Any]:
        """
        전체 파이프라인 실행 (각 단계 모니터링)

        Args:
            account_id: AWS 계정 ID

        Returns:
            {
                'pipeline_id': str,
                'status': 'HEALTHY' | 'DEGRADED' | 'FAILED',
                'stages': {
                    'anomaly_detection': {...},
                    'prediction': {...},
                    ...
                },
                'end_to_end_latency_ms': float,
                'errors': [str],
                'total_threats': int,
                'mitigated_threats': int
            }
        """
        pipeline_id = str(uuid.uuid4())
        stage_results = {}
        errors = []
        threats = []
        start_time = time.time()

        logger.info(f"Pipeline orchestration started: {pipeline_id} for account {account_id}")

        try:
            # Stage 1: 이상 탐지
            stage_start = time.time()
            try:
                threats = await self.stages['anomaly_detection'].detect(account_id)
                stage_results['anomaly_detection'] = {
                    'status': 'SUCCESS',
                    'threats_detected': len(threats),
                    'latency_ms': (time.time() - stage_start) * 1000
                }
                logger.info(f"Anomaly detection: {len(threats)} threats detected")
            except Exception as e:
                logger.error(f"Anomaly detection failed: {e}")
                errors.append(f"Anomaly detection failed: {e}")
                stage_results['anomaly_detection'] = {
                    'status': 'FAILED',
                    'error': str(e),
                    'latency_ms': (time.time() - stage_start) * 1000
                }

            # Stage 2: ML 예측 (위협이 있을 경우)
            if threats:
                stage_start = time.time()
                try:
                    predictions = await self.stages['prediction'].predict_batch(threats)
                    stage_results['prediction'] = {
                        'status': 'SUCCESS',
                        'predictions_made': len(predictions),
                        'latency_ms': (time.time() - stage_start) * 1000
                    }
                    logger.info(f"Prediction: {len(predictions)} predictions made")
                except Exception as e:
                    logger.error(f"Prediction failed: {e}")
                    errors.append(f"Prediction failed: {e}")
                    stage_results['prediction'] = {
                        'status': 'FAILED',
                        'error': str(e),
                        'latency_ms': (time.time() - stage_start) * 1000
                    }

                # Stage 3: 플레이북 매핑
                stage_start = time.time()
                try:
                    playbooks = await self.stages['playbook_mapping'].map_threats_to_playbooks(threats)
                    stage_results['playbook_mapping'] = {
                        'status': 'SUCCESS',
                        'playbooks_mapped': len(playbooks),
                        'latency_ms': (time.time() - stage_start) * 1000
                    }
                    logger.info(f"Playbook mapping: {len(playbooks)} playbooks mapped")
                except Exception as e:
                    logger.error(f"Playbook mapping failed: {e}")
                    errors.append(f"Playbook mapping failed: {e}")
                    stage_results['playbook_mapping'] = {
                        'status': 'FAILED',
                        'error': str(e),
                        'latency_ms': (time.time() - stage_start) * 1000
                    }

                # Stage 4: 작업 실행
                stage_start = time.time()
                try:
                    execution_results = await self.stages['action_execution'].execute_playbooks(playbooks)
                    stage_results['action_execution'] = {
                        'status': 'SUCCESS',
                        'actions_executed': len(execution_results),
                        'successful_actions': sum(1 for r in execution_results if r.get('status') == 'SUCCESS'),
                        'latency_ms': (time.time() - stage_start) * 1000
                    }
                    logger.info(f"Action execution: {len(execution_results)} actions executed")
                except Exception as e:
                    logger.error(f"Action execution failed: {e}")
                    errors.append(f"Action execution failed: {e}")
                    stage_results['action_execution'] = {
                        'status': 'FAILED',
                        'error': str(e),
                        'latency_ms': (time.time() - stage_start) * 1000
                    }

                # Stage 5: 피드백 수집
                stage_start = time.time()
                try:
                    feedback = await self.stages['feedback_collection'].collect_feedback(threats)
                    stage_results['feedback_collection'] = {
                        'status': 'SUCCESS',
                        'feedback_collected': len(feedback),
                        'latency_ms': (time.time() - stage_start) * 1000
                    }
                    logger.info(f"Feedback collection: {len(feedback)} feedback items collected")
                except Exception as e:
                    logger.error(f"Feedback collection failed: {e}")
                    errors.append(f"Feedback collection failed: {e}")
                    stage_results['feedback_collection'] = {
                        'status': 'FAILED',
                        'error': str(e),
                        'latency_ms': (time.time() - stage_start) * 1000
                    }

            else:
                # 위협이 없으면 이후 단계 스킵
                stage_results['prediction'] = {'status': 'SKIPPED'}
                stage_results['playbook_mapping'] = {'status': 'SKIPPED'}
                stage_results['action_execution'] = {'status': 'SKIPPED'}
                stage_results['feedback_collection'] = {'status': 'SKIPPED'}

            # Stage 6: 모델 재학습 (매주 실행, 여기서는 스킵)
            stage_results['model_retraining'] = {'status': 'SCHEDULED'}

        except Exception as e:
            logger.error(f"Pipeline orchestration error: {e}", exc_info=True)
            errors.append(f"Pipeline orchestration error: {e}")

        # 파이프라인 상태 결정
        status = self._determine_pipeline_status(stage_results)
        end_time = time.time()

        result = {
            'pipeline_id': pipeline_id,
            'status': status,
            'stages': stage_results,
            'errors': errors,
            'total_threats': len(threats),
            'mitigated_threats': sum(1 for t in threats if t.get('mitigated', False)),
            'end_to_end_latency_ms': (end_time - start_time) * 1000,
            'timestamp': datetime.utcnow().isoformat()
        }

        # 메트릭 저장
        await self.metrics.record_pipeline_execution(result)

        logger.info(f"Pipeline orchestration completed: {pipeline_id} with status {status}")

        return result

    def _determine_pipeline_status(self, stage_results: Dict[str, Dict]) -> str:
        """
        파이프라인 상태 결정

        Rules:
        - 실패한 단계 0개: HEALTHY
        - 실패한 단계 1-2개: DEGRADED
        - 실패한 단계 3개 이상: FAILED
        """
        failed_stages = sum(
            1 for result in stage_results.values()
            if result.get('status') == 'FAILED'
        )

        if failed_stages == 0:
            return 'HEALTHY'
        elif failed_stages <= 2:
            return 'DEGRADED'
        else:
            return 'FAILED'

    async def get_pipeline_health(self, lookback_minutes: int = 60) -> Dict[str, Any]:
        """
        파이프라인 전체 상태 조회

        Returns:
            {
                'overall_status': 'HEALTHY' | 'DEGRADED' | 'FAILED',
                'total_executions': int,
                'successful_executions': int,
                'success_rate': float,
                'avg_latency_ms': float,
                'stage_success_rates': {...},
                'recent_errors': [str]
            }
        """
        return await self.metrics.get_pipeline_health(lookback_minutes)

    async def get_stage_metrics(self, stage_name: str) -> Dict[str, Any]:
        """특정 단계의 메트릭"""
        return await self.metrics.get_stage_metrics(stage_name)
