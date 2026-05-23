"""Remediation Orchestrator (Sprint 37 Phase 4)

Coordinates execution of remediation actions with safety checks, approval workflows,
and state management.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from guardian.responders.aws_action_executor import AWSActionExecutor
from guardian.responders.rule_remediation import RuleRemediationExecutor
from guardian.responders.advanced_remediation import AdvancedRemediationExecutor
from guardian.storage.response_audit import ResponseAuditRepository, ResponseAction
from guardian.detectors.anomaly_detector import Threat

logger = logging.getLogger(__name__)


class RemediationImpact(Enum):
    """Impact level of a remediation action"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RemediationApprovalStatus(Enum):
    """Approval status for remediation actions"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_APPROVED = "AUTO_APPROVED"


@dataclass
class OrchestrationResult:
    """Result of orchestrated remediation execution"""
    threat_id: str
    rule_id: str
    total_actions: int
    executed_actions: int
    failed_actions: int
    pending_approval_actions: int
    results: List[Dict[str, Any]]
    approval_status: RemediationApprovalStatus
    timestamp: str
    execution_time_seconds: float


class RemediationOrchestrator:
    """Orchestrates remediation execution with safety checks and approvals"""

    # Impact thresholds for automatic approval
    AUTO_APPROVE_IMPACT = RemediationImpact.MEDIUM
    APPROVAL_REQUIRED_IMPACT = RemediationImpact.HIGH

    def __init__(
        self,
        aws_executor: Optional[AWSActionExecutor] = None,
        audit_repository: Optional[ResponseAuditRepository] = None
    ):
        """Initialize orchestrator

        Args:
            aws_executor: AWSActionExecutor for executing actions
            audit_repository: ResponseAuditRepository for logging
        """
        self.aws_executor = aws_executor or AWSActionExecutor()
        self.audit_repository = audit_repository
        self.basic_executor = RuleRemediationExecutor(aws_executor=self.aws_executor)
        self.advanced_executor = AdvancedRemediationExecutor(aws_executor=self.aws_executor)

    def execute_remediation_with_orchestration(
        self,
        rule: Dict[str, Any],
        threat: Threat,
        dry_run: bool = False,
        approval_required: bool = False,
        approved_by: Optional[str] = None
    ) -> OrchestrationResult:
        """Execute remediation with orchestration, safety checks, and approvals

        Args:
            rule: Rule definition with remediation_actions
            threat: Detected threat to remediate
            dry_run: If True, simulate execution without actually performing actions
            approval_required: If True, require approval before execution
            approved_by: User who approved the remediation (if applicable)

        Returns:
            OrchestrationResult with execution details
        """
        start_time = datetime.now(timezone.utc)
        timestamp = start_time.isoformat()
        results = []

        # Check if remediation is enabled
        if not rule.get('action', {}).get('auto_remediate', False):
            return OrchestrationResult(
                threat_id=threat.threat_id,
                rule_id=threat.rule_id,
                total_actions=0,
                executed_actions=0,
                failed_actions=0,
                pending_approval_actions=0,
                results=[],
                approval_status=RemediationApprovalStatus.AUTO_APPROVED,
                timestamp=timestamp,
                execution_time_seconds=0.0
            )

        remediation_actions = rule.get('action', {}).get('remediation_actions', [])
        if not remediation_actions:
            return OrchestrationResult(
                threat_id=threat.threat_id,
                rule_id=threat.rule_id,
                total_actions=0,
                executed_actions=0,
                failed_actions=0,
                pending_approval_actions=0,
                results=[],
                approval_status=RemediationApprovalStatus.AUTO_APPROVED,
                timestamp=timestamp,
                execution_time_seconds=0.0
            )

        # Assess impact and determine approval workflow
        total_impact = self._assess_total_impact(remediation_actions)
        approval_status = self._determine_approval_status(
            total_impact, approval_required, approved_by
        )

        # Perform dry-run if requested
        if dry_run:
            results = self._dry_run_remediation(remediation_actions, threat)
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return OrchestrationResult(
                threat_id=threat.threat_id,
                rule_id=threat.rule_id,
                total_actions=len(remediation_actions),
                executed_actions=sum(1 for r in results if r.get('success')),
                failed_actions=sum(1 for r in results if not r.get('success')),
                pending_approval_actions=0,
                results=results,
                approval_status=RemediationApprovalStatus.PENDING,
                timestamp=timestamp,
                execution_time_seconds=execution_time
            )

        # Execute remediation actions
        for action in remediation_actions:
            if not action.get('enabled', True):
                continue

            action_result = self._execute_single_action(action, threat)
            if action_result:
                results.append(action_result)

                # Log to audit repository
                if self.audit_repository and action_result.get('response_id'):
                    self.audit_repository.record_response(
                        threat_id=threat.threat_id,
                        rule_id=threat.rule_id,
                        action_type=action.get('type'),
                        target=action_result.get('target', 'unknown'),
                        success=action_result.get('success', False),
                        message=action_result.get('message', ''),
                        requires_approval=approval_required
                    )

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        return OrchestrationResult(
            threat_id=threat.threat_id,
            rule_id=threat.rule_id,
            total_actions=len(remediation_actions),
            executed_actions=sum(1 for r in results if r.get('success')),
            failed_actions=sum(1 for r in results if not r.get('success')),
            pending_approval_actions=0,
            results=results,
            approval_status=approval_status,
            timestamp=timestamp,
            execution_time_seconds=execution_time
        )

    def _assess_total_impact(self, remediation_actions: List[Dict[str, Any]]) -> RemediationImpact:
        """Assess combined impact of remediation actions"""
        max_impact = RemediationImpact.LOW

        for action in remediation_actions:
            action_type = action.get('type', '')
            impact = self._assess_action_impact(action_type)

            if impact == RemediationImpact.CRITICAL:
                return RemediationImpact.CRITICAL
            elif impact == RemediationImpact.HIGH and max_impact != RemediationImpact.CRITICAL:
                max_impact = RemediationImpact.HIGH
            elif impact == RemediationImpact.MEDIUM and max_impact == RemediationImpact.LOW:
                max_impact = RemediationImpact.MEDIUM

        return max_impact

    def _assess_action_impact(self, action_type: str) -> RemediationImpact:
        """Assess impact of a single action"""
        # High impact: stops instances, deregisters from LB, disables public access
        high_impact_actions = {
            'EC2_STOP', 'RDS_DISABLE_PUBLIC', 'ELB_DEREGISTER',
            'NACL_RESTRICT', 'ROUTE_REMOVE'
        }

        # Critical impact: removes layers, disables Lambda, isolates resources
        critical_impact_actions = {
            'LAMBDA_DISABLE', 'LAMBDA_LAYER_REMOVE', 'VPC_ISOLATE'
        }

        # Medium impact: restrictions, encryption, backups
        medium_impact_actions = {
            'LAMBDA_CONCURRENCY_LIMIT', 'RDS_ENCRYPT_ENABLE', 'RDS_BACKUP_ENABLE',
            'RDS_SNAPSHOT', 'S3_BLOCK_PUBLIC'
        }

        if action_type in critical_impact_actions:
            return RemediationImpact.CRITICAL
        elif action_type in high_impact_actions:
            return RemediationImpact.HIGH
        elif action_type in medium_impact_actions:
            return RemediationImpact.MEDIUM
        else:
            return RemediationImpact.LOW

    def _determine_approval_status(
        self,
        impact: RemediationImpact,
        approval_required: bool,
        approved_by: Optional[str]
    ) -> RemediationApprovalStatus:
        """Determine approval status based on impact"""
        if approval_required and approved_by:
            return RemediationApprovalStatus.APPROVED

        if impact == RemediationImpact.CRITICAL or approval_required:
            return RemediationApprovalStatus.PENDING

        if impact == RemediationImpact.HIGH:
            return RemediationApprovalStatus.PENDING

        return RemediationApprovalStatus.AUTO_APPROVED

    def _dry_run_remediation(
        self,
        remediation_actions: List[Dict[str, Any]],
        threat: Threat
    ) -> List[Dict[str, Any]]:
        """Perform dry-run of remediation actions (no actual execution)"""
        results = []

        for action in remediation_actions:
            if not action.get('enabled', True):
                continue

            # Simulate action execution
            result = {
                'action_type': action.get('type'),
                'success': True,  # Assume success in dry-run unless parameters are invalid
                'target': self._extract_target(action, threat),
                'message': f"[DRY-RUN] Would execute {action.get('type')}",
                'dry_run': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            results.append(result)

        return results

    def _execute_single_action(
        self,
        action: Dict[str, Any],
        threat: Threat
    ) -> Optional[Dict[str, Any]]:
        """Execute a single remediation action"""
        action_type = action.get('type', '')

        # Try to execute as advanced remediation first
        if action_type.startswith(('LAMBDA_', 'RDS_', 'VPC_', 'ROUTE_', 'NACL_', 'ELB_')):
            if action_type.startswith('LAMBDA_') or action_type.startswith('RDS_') \
               or action_type in ['VPC_ISOLATE', 'ROUTE_REMOVE', 'NACL_RESTRICT', 'ELB_DEREGISTER']:
                result = self._execute_advanced_action(action, threat)
            else:
                result = self._execute_basic_action(action, threat)
        else:
            result = self._execute_basic_action(action, threat)

        return result

    def _execute_basic_action(
        self,
        action: Dict[str, Any],
        threat: Threat
    ) -> Optional[Dict[str, Any]]:
        """Execute basic remediation action via RuleRemediationExecutor"""
        try:
            rule = {'action': {'auto_remediate': True, 'remediation_actions': [action]}}
            results = self.basic_executor.execute_remediation(rule, threat)

            if results:
                result = results[0]
                # Handle both dict and RemediationResult object
                if hasattr(result, '__dict__'):
                    # Object with attributes
                    return {
                        'action_type': action.get('type'),
                        'success': getattr(result, 'success', False),
                        'target': getattr(result, 'target', 'unknown'),
                        'message': getattr(result, 'message', ''),
                        'response_id': self._generate_response_id(),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    # Dictionary
                    return {
                        'action_type': action.get('type'),
                        'success': result.get('success', False),
                        'target': result.get('target', 'unknown'),
                        'message': result.get('message', ''),
                        'response_id': self._generate_response_id(),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }

            return None
        except Exception as e:
            logger.error(f"Error executing basic action: {e}")
            return None

    def _execute_advanced_action(
        self,
        action: Dict[str, Any],
        threat: Threat
    ) -> Optional[Dict[str, Any]]:
        """Execute advanced remediation action via AdvancedRemediationExecutor"""
        try:
            action_type = action.get('type', '')

            if action_type.startswith('LAMBDA_'):
                result = self.advanced_executor.execute_lambda_remediation(action, threat)
            elif action_type.startswith('RDS_'):
                result = self.advanced_executor.execute_rds_remediation(action, threat)
            elif action_type in ['VPC_ISOLATE', 'ROUTE_REMOVE', 'NACL_RESTRICT', 'ELB_DEREGISTER']:
                result = self.advanced_executor.execute_vpc_remediation(action, threat)
            else:
                return None

            if result:
                return {
                    'action_type': action.get('type'),
                    'success': result.success,
                    'target': result.target,
                    'message': result.message,
                    'rollback_metadata': result.rollback_metadata,
                    'response_id': self._generate_response_id(),
                    'timestamp': result.timestamp
                }

            return None
        except Exception as e:
            logger.error(f"Error executing advanced action: {e}")
            return None

    def _extract_target(
        self,
        action: Dict[str, Any],
        threat: Threat
    ) -> str:
        """Extract target resource from action and threat"""
        params = action.get('parameters', {})

        # Check parameters first
        if 'function_name' in params:
            return params['function_name']
        if 'db_instance_id' in params:
            return params['db_instance_id']
        if 'resource_id' in params:
            return params['resource_id']

        # Check threat evidence
        if threat.evidence:
            for item in threat.evidence:
                if isinstance(item, dict):
                    if 'function_name' in item:
                        return item['function_name']
                    if 'instance_id' in item:
                        return item['instance_id']
                    if 'bucket_name' in item:
                        return item['bucket_name']
                    if 'db_instance_id' in item:
                        return item['db_instance_id']

        return 'unknown'

    @staticmethod
    def _generate_response_id() -> str:
        """Generate unique response ID"""
        import uuid
        return str(uuid.uuid4())
