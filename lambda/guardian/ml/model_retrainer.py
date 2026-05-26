import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import pickle
import logging

logger = logging.getLogger(__name__)


class ModelRetrainer:
    """피드백 기반 머신러닝 모델 재학습"""

    def __init__(self, model_storage, feedback_repo, feature_engineer):
        """
        Args:
            model_storage: 모델 저장소 (저장/로드)
            feedback_repo: 피드백 저장소 (쿼리)
            feature_engineer: 특성 공학 엔진
        """
        self.model_storage = model_storage
        self.feedback = feedback_repo
        self.engineer = feature_engineer
        self.scaler = StandardScaler()
        self.current_model = None
        self.model_version = None

    def retrain_from_feedback(self, lookback_days: int = 30) -> Dict[str, Any]:
        """
        지난 N일간의 피드백으로 모델 재학습

        Args:
            lookback_days: 몇 일 간의 피드백을 사용할지 (기본: 30일)

        Returns:
            {
                'model_version': str,
                'training_samples': int,
                'metrics': {...},
                'improvements': {...},
                'timestamp': str
            }
        """
        logger.info(f"Starting model retraining with {lookback_days}-day lookback")

        # 1. 피드백 수집
        feedback_logs = self.feedback.query_recent(days=lookback_days)
        if not feedback_logs:
            logger.warning("No feedback logs available for retraining")
            return {
                'model_version': None,
                'training_samples': 0,
                'metrics': {},
                'improvements': {},
                'timestamp': datetime.utcnow().isoformat()
            }

        # 2. 특성 추출
        X, y = self.engineer.extract_features(feedback_logs)
        if len(X) == 0:
            logger.warning("Failed to extract features from feedback logs")
            return {
                'model_version': None,
                'training_samples': 0,
                'metrics': {},
                'improvements': {},
                'timestamp': datetime.utcnow().isoformat()
            }

        # 3. 데이터 정규화
        X_scaled = self.scaler.fit_transform(X)

        # 4. 모델 재학습 (증분 또는 신규)
        new_model = self._train_model(X_scaled, y)

        # 5. 모델 평가
        metrics = self._evaluate_model(new_model, X_scaled, y)

        # 6. 이전 모델과 비교
        improvements = self._compare_with_previous(metrics)

        # 7. 모델 저장 (버전 관리)
        model_version = self.model_storage.save_version(
            model=new_model,
            scaler=self.scaler,
            metrics=metrics,
            training_samples=len(feedback_logs)
        )

        self.current_model = new_model
        self.model_version = model_version

        logger.info(f"Model retraining completed. Version: {model_version}, Accuracy: {metrics['accuracy']:.4f}")

        return {
            'model_version': model_version,
            'training_samples': len(feedback_logs),
            'metrics': metrics,
            'improvements': improvements,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _train_model(self, X_scaled: np.ndarray, y: np.ndarray):
        """
        RandomForest 모델 학습

        Args:
            X_scaled: 정규화된 특성 배열
            y: 레이블 배열 (0 = 오탐, 1 = 정탐)

        Returns:
            학습된 모델
        """
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'  # 불균형 데이터 처리
        )

        model.fit(X_scaled, y)
        return model

    def _evaluate_model(self, model, X_scaled: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        모델 성능 평가

        Args:
            model: 학습된 모델
            X_scaled: 정규화된 특성
            y: 레이블

        Returns:
            {
                'accuracy': float,
                'precision': float,
                'recall': float,
                'f1_score': float,
                'confusion_matrix': List[List[int]]
            }
        """
        predictions = model.predict(X_scaled)

        metrics = {
            'accuracy': accuracy_score(y, predictions),
            'precision': precision_score(y, predictions, zero_division=0, average='binary'),
            'recall': recall_score(y, predictions, zero_division=0, average='binary'),
            'f1_score': f1_score(y, predictions, zero_division=0, average='binary'),
            'confusion_matrix': confusion_matrix(y, predictions).tolist()
        }

        return metrics

    def _compare_with_previous(self, new_metrics: Dict[str, Any]) -> Dict[str, float]:
        """
        이전 모델 대비 개선도 계산

        Returns:
            {
                'accuracy_improvement': float,
                'precision_improvement': float,
                'recall_improvement': float,
                'f1_improvement': float
            }
        """
        try:
            prev_metrics = self.model_storage.get_previous_version_metrics()
            if not prev_metrics:
                return {
                    'accuracy_improvement': 0.0,
                    'precision_improvement': 0.0,
                    'recall_improvement': 0.0,
                    'f1_improvement': 0.0
                }

            return {
                'accuracy_improvement': new_metrics['accuracy'] - prev_metrics.get('accuracy', 0),
                'precision_improvement': new_metrics['precision'] - prev_metrics.get('precision', 0),
                'recall_improvement': new_metrics['recall'] - prev_metrics.get('recall', 0),
                'f1_improvement': new_metrics['f1_score'] - prev_metrics.get('f1_score', 0)
            }
        except Exception as e:
            logger.warning(f"Failed to compare with previous model: {e}")
            return {
                'accuracy_improvement': 0.0,
                'precision_improvement': 0.0,
                'recall_improvement': 0.0,
                'f1_improvement': 0.0
            }

    def should_deploy_new_model(self, improvements: Dict[str, float], threshold: float = 0.02) -> bool:
        """
        신규 모델 자동 배포 여부 결정

        Args:
            improvements: 개선도 딕셔너리
            threshold: 배포 임계값 (기본: 2% 개선도)

        Returns:
            bool: True면 배포, False면 유지
        """
        f1_improvement = improvements.get('f1_improvement', 0)
        accuracy_improvement = improvements.get('accuracy_improvement', 0)

        # F1 점수 2% 이상 개선 또는 정확도 1% 이상 개선
        return f1_improvement >= threshold or accuracy_improvement >= 0.01

    def deploy_new_model(self, model_version: str) -> Dict[str, Any]:
        """
        신규 모델을 활성 모델로 배포

        Args:
            model_version: 배포할 모델 버전

        Returns:
            {
                'status': 'success' | 'failed',
                'deployed_version': str,
                'timestamp': str
            }
        """
        try:
            self.model_storage.set_active_version(model_version)
            logger.info(f"Model {model_version} deployed successfully")

            return {
                'status': 'success',
                'deployed_version': model_version,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to deploy model {model_version}: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def get_model_feature_importance(self) -> Dict[str, float]:
        """
        현재 모델의 특성 중요도 반환

        Returns:
            {
                'feature_name': importance_score,
                ...
            }
        """
        if self.current_model is None or not hasattr(self.current_model, 'feature_importances_'):
            return {}

        # 특성 이름 (feature_engineer와 동일한 순서)
        feature_names = [
            'threat_type_id', 'severity_numeric', 'evidence_count',
            'detection_latency_sec', 'action_success_rate', 'hour_of_day',
            'day_of_week', 'is_night_time', 'account_id_hash', 'source_ip_anomaly'
        ]

        importances = self.current_model.feature_importances_
        return {
            name: float(importance)
            for name, importance in zip(feature_names, importances)
        }
