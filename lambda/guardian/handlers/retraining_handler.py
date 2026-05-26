import json
import logging
from datetime import datetime
from typing import Dict, Any

from guardian.ml.feature_engineer import FeatureEngineer
from guardian.ml.model_retrainer import ModelRetrainer
from guardian.storage.feedback_repository import FeedbackRepository
from guardian.storage.model_storage import ModelStorage
from guardian.responders.notification_responder import NotificationResponder

logger = logging.getLogger(__name__)


class RetrainingHandler:
    """모델 재학습 Lambda 핸들러"""

    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.feedback_repo = FeedbackRepository()
        self.model_storage = ModelStorage()
        self.notifier = NotificationResponder()
        self.retrainer = ModelRetrainer(
            model_storage=self.model_storage,
            feedback_repo=self.feedback_repo,
            feature_engineer=self.feature_engineer
        )

    def handle_retraining_event(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """
        EventBridge 트리거 이벤트 처리 (매주 일요일 00:00 UTC)

        Args:
            event: EventBridge 이벤트
            context: Lambda 컨텍스트

        Returns:
            {
                'statusCode': 200 | 500,
                'body': {...}
            }
        """
        logger.info("Starting model retraining job")

        try:
            # 1. 모델 재학습 (지난 30일 피드백)
            result = self.retrainer.retrain_from_feedback(lookback_days=30)

            if result['model_version'] is None:
                logger.warning("Model retraining skipped: no feedback data")
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'skipped',
                        'reason': 'no_feedback_data',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                }

            # 2. 개선도 확인
            improvements = result['improvements']
            metrics = result['metrics']

            logger.info(f"Retraining complete. F1 improvement: {improvements['f1_improvement']:.4f}")

            # 3. 임계값 초과 시 자동 배포
            should_deploy = self.retrainer.should_deploy_new_model(improvements, threshold=0.02)

            if should_deploy:
                logger.info(f"Deploying new model: {result['model_version']}")
                deployment_result = self.retrainer.deploy_new_model(result['model_version'])

                # 배포 알림
                await self._notify_deployment(result, deployment_result)

                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'success',
                        'action': 'deployed',
                        'model_version': result['model_version'],
                        'metrics': metrics,
                        'improvements': improvements,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                }
            else:
                logger.info(f"Model improvement ({improvements['f1_improvement']:.4f}) below threshold (0.02)")

                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'success',
                        'action': 'trained_not_deployed',
                        'model_version': result['model_version'],
                        'metrics': metrics,
                        'improvements': improvements,
                        'reason': 'improvement_below_threshold',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                }

        except Exception as e:
            logger.error(f"Model retraining failed: {e}", exc_info=True)
            await self._notify_failure(str(e))

            return {
                'statusCode': 500,
                'body': json.dumps({
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
            }

    async def _notify_deployment(self, result: Dict[str, Any], deployment_result: Dict[str, Any]):
        """모델 배포 알림"""
        message = (
            f"🚀 **모델 배포 완료**\n\n"
            f"📊 **성능 지표**\n"
            f"• 정확도: {result['metrics']['accuracy']:.2%}\n"
            f"• 정밀도: {result['metrics']['precision']:.2%}\n"
            f"• 재현율: {result['metrics']['recall']:.2%}\n"
            f"• F1 점수: {result['metrics']['f1_score']:.2%}\n\n"
            f"📈 **개선도**\n"
            f"• 정확도: +{result['improvements']['accuracy_improvement']:.2%}\n"
            f"• F1 점수: +{result['improvements']['f1_improvement']:.2%}\n\n"
            f"📚 **학습 데이터**\n"
            f"• 샘플 수: {result['training_samples']:,}\n"
            f"• 모델 버전: {result['model_version']}"
        )

        await self.notifier.send_telegram(message)

    async def _notify_failure(self, error_message: str):
        """재학습 실패 알림"""
        message = (
            f"❌ **모델 재학습 실패**\n\n"
            f"오류: {error_message}"
        )

        await self.notifier.send_telegram(message)


def lambda_handler(event, context):
    """AWS Lambda 진입점"""
    handler = RetrainingHandler()
    response = handler.handle_retraining_event(event, context)

    # JSON 직렬화 처리 (NoneType 등)
    return json.loads(json.dumps(response, default=str))
