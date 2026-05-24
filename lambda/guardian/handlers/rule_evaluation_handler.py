import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

from storage.security_rules import SecurityRuleRepository
from detectors.anomaly_detector import AnomalyDetector
from responders.remediation_orchestrator import RemediationOrchestrator
from storage.response_audit import ResponseAuditRepository

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """규칙 평가 실행 메트릭"""
    evaluation_id: str
    timestamp: str
    active_rules_count: int
    detected_threats_count: int
    executed_responses_count: int
    failed_responses_count: int
    total_execution_time_seconds: float


@dataclass
class EvaluationResult:
    """규칙 평가 실행 결과"""
    success: bool
    metrics: EvaluationMetrics
    threats: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    errors: List[str]


class RuleEvaluationHandler:
    """
    EventBridge 트리거로 활성화된 규칙을 평가하고 대응을 실행합니다.

    흐름:
    1. 활성화(ACTIVE) 규칙 로드
    2. 이상 탐지 (최근 로그 분석)
    3. 각 위협에 대해 자동 대응 실행
    4. 감사 로그 기록
    5. 메트릭 반환
    """

    def __init__(
        self,
        rules_repo: SecurityRuleRepository,
        detector: AnomalyDetector,
        responder: RemediationOrchestrator,
        audit_repo: ResponseAuditRepository
    ):
        self.rules = rules_repo
        self.detector = detector
        self.responder = responder
        self.audit = audit_repo

    def handle_evaluation(self, event: Dict[str, Any]) -> EvaluationResult:
        """
        EventBridge 트리거 이벤트 처리

        Args:
            event: EventBridge 이벤트 (schedule-expression 포함)

        Returns:
            EvaluationResult: 평가 실행 결과
        """
        start_time = datetime.utcnow()
        evaluation_id = self._generate_evaluation_id()
        errors = []
        threats_list = []
        responses_list = []

        try:
            # 1. ACTIVE 규칙 로드
            logger.info(f"[{evaluation_id}] Loading active rules...")
            active_rules = self.rules.list_active_rules()
            logger.info(f"[{evaluation_id}] Loaded {len(active_rules)} active rules")

            if not active_rules:
                logger.warning(f"[{evaluation_id}] No active rules found")
                return self._build_result(
                    evaluation_id, start_time, active_rules,
                    threats_list, responses_list, errors, success=True
                )

            # 2. 이상 탐지 (배포된 규칙만)
            logger.info(f"[{evaluation_id}] Detecting anomalies...")
            threats = self.detector.detect_anomalies(
                lookback_minutes=5,
                rules=active_rules
            )
            threats_list = [self._threat_to_dict(t) for t in threats]
            logger.info(f"[{evaluation_id}] Detected {len(threats)} threats")

            # 3. 각 위협에 대해 자동 대응 실행
            for threat in threats:
                try:
                    rule = self.rules.get_rule(threat.rule_id)
                    if not rule:
                        error_msg = f"Rule {threat.rule_id} not found"
                        logger.warning(f"[{evaluation_id}] {error_msg}")
                        errors.append(error_msg)
                        continue

                    # 자동 대응 실행 (dry_run=False, 자동 승인)
                    logger.info(f"[{evaluation_id}] Executing response for threat {threat.threat_id}")
                    response = self.responder.execute_remediation_with_orchestration(
                        rule=rule,
                        threat=threat,
                        dry_run=False,
                        approval_required=False,
                        approved_by="auto-evaluation"
                    )

                    # 응답 결과 기록
                    response_dict = self._orchestration_result_to_dict(response)
                    responses_list.append(response_dict)
                    logger.info(f"[{evaluation_id}] Response executed: {response.total_actions} actions")

                    # 감사 로그 기록
                    try:
                        self.audit.record_evaluation(threat, response)
                    except Exception as e:
                        logger.warning(f"[{evaluation_id}] Failed to record audit: {str(e)}")
                        errors.append(f"Audit recording failed: {str(e)}")

                except Exception as e:
                    error_msg = f"Response execution failed for threat {threat.threat_id}: {str(e)}"
                    logger.error(f"[{evaluation_id}] {error_msg}")
                    errors.append(error_msg)

            return self._build_result(
                evaluation_id, start_time, active_rules,
                threats_list, responses_list, errors, success=True
            )

        except Exception as e:
            error_msg = f"Evaluation failed: {str(e)}"
            logger.error(f"[{evaluation_id}] {error_msg}")
            errors.append(error_msg)

            return self._build_result(
                evaluation_id, start_time, [],
                threats_list, responses_list, errors, success=False
            )

    def _build_result(
        self,
        evaluation_id: str,
        start_time: datetime,
        active_rules: List,
        threats: List[Dict],
        responses: List[Dict],
        errors: List[str],
        success: bool
    ) -> EvaluationResult:
        """평가 결과 구성"""
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        # 실패한 응답 수 계산
        failed_count = sum(1 for r in responses if not r.get('success', False))

        metrics = EvaluationMetrics(
            evaluation_id=evaluation_id,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            active_rules_count=len(active_rules),
            detected_threats_count=len(threats),
            executed_responses_count=len(responses),
            failed_responses_count=failed_count,
            total_execution_time_seconds=elapsed
        )

        return EvaluationResult(
            success=success,
            metrics=asdict(metrics),
            threats=threats,
            responses=responses,
            errors=errors
        )

    @staticmethod
    def _threat_to_dict(threat) -> Dict[str, Any]:
        """Threat 객체를 딕셔너리로 변환"""
        return {
            'threat_id': threat.threat_id,
            'rule_id': threat.rule_id,
            'severity': threat.severity,
            'account_id': threat.account_id,
            'timestamp': threat.timestamp.isoformat() + 'Z' if hasattr(threat.timestamp, 'isoformat') else threat.timestamp,
            'message': threat.message,
            'evidence': threat.evidence if hasattr(threat, 'evidence') else []
        }

    @staticmethod
    def _orchestration_result_to_dict(result) -> Dict[str, Any]:
        """OrchestrationResult를 딕셔너리로 변환"""
        result_dict = {
            'threat_id': result.threat_id,
            'rule_id': result.rule_id,
            'total_actions': result.total_actions,
            'executed_actions': result.executed_actions,
            'failed_actions': result.failed_actions,
            'pending_approval_actions': result.pending_approval_actions,
            'approval_status': result.approval_status,
            'timestamp': result.timestamp,
            'execution_time_seconds': result.execution_time_seconds,
            'success': result.executed_actions > 0 or result.total_actions == 0
        }

        # 액션 결과 추가 (있는 경우)
        if hasattr(result, 'results') and result.results:
            result_dict['action_results'] = [
                self._action_result_to_dict(r) for r in result.results
            ]

        return result_dict

    @staticmethod
    def _action_result_to_dict(action_result) -> Dict[str, Any]:
        """액션 결과를 딕셔너리로 변환"""
        if isinstance(action_result, dict):
            return action_result

        return {
            'action_type': getattr(action_result, 'action_type', 'unknown'),
            'success': getattr(action_result, 'success', False),
            'target': getattr(action_result, 'target', ''),
            'message': getattr(action_result, 'message', '')
        }

    @staticmethod
    def _generate_evaluation_id() -> str:
        """평가 ID 생성 (타임스탬프 기반)"""
        import uuid
        return f"eval-{uuid.uuid4().hex[:8]}"


def lambda_handler(event, context):
    """
    AWS Lambda 핸들러 진입점

    EventBridge 규칙으로부터 1분/5분/1시간마다 호출됨

    이벤트 구조:
    {
        "version": "0",
        "id": "...",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789",
        "time": "2026-05-24T12:00:00Z",
        "region": "us-east-1",
        "resources": [],
        "detail": {
            "schedule": "rate(1 minute)"
        }
    }
    """
    try:
        # 의존성 주입 (실제 구현에서는 DI 컨테이너 사용)
        rules_repo = SecurityRuleRepository()
        detector = AnomalyDetector()
        responder = RemediationOrchestrator()
        audit_repo = ResponseAuditRepository()

        handler = RuleEvaluationHandler(rules_repo, detector, responder, audit_repo)
        result = handler.handle_evaluation(event)

        return {
            'statusCode': 200,
            'body': json.dumps(asdict(result)),
            'headers': {'Content-Type': 'application/json'}
        }

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'success': False
            }),
            'headers': {'Content-Type': 'application/json'}
        }
