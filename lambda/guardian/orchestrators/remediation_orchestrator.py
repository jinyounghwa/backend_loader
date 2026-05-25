"""Remediation Orchestrator - Coordinate multi-step remediation across EC2, S3, IAM, Network."""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid


class RemediationStatus(Enum):
    """Remediation execution statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RemediationOrchestrator:
    """Orchestrate multi-resource remediation with dependency management and rollback."""

    # Remediation dependency order: EC2 → Network → IAM → S3
    REMEDIATION_ORDER = ['ec2', 'network', 'iam', 's3']

    def __init__(self, ec2_remediator, network_remediator, iam_remediator, s3_remediator, audit_logger):
        """Initialize orchestrator with all remediators."""
        self.ec2 = ec2_remediator
        self.network = network_remediator
        self.iam = iam_remediator
        self.s3 = s3_remediator
        self.audit = audit_logger
        self.execution_history = {}

    def execute_multi_resource_remediation(self, threat: Dict) -> Dict:
        """
        Execute multi-step remediation across multiple resources in dependency order.

        Remediation order:
        1. EC2: Stop compromised instances
        2. Network: Isolate instances via Security Groups
        3. IAM: Revoke excessive permissions
        4. S3: Block public access

        Args:
            threat: Threat detection details with resource IDs

        Returns:
            {
                'status': 'success|failed|rolled_back',
                'orchestration_id': uuid,
                'threat_id': threat_id,
                'execution_order': [steps],
                'results': {remediator_type: result},
                'rollback_info': optional,
                'timestamp': iso_timestamp
            }
        """
        orchestration_id = str(uuid.uuid4())
        result = {
            'orchestration_id': orchestration_id,
            'threat_id': threat.get('threat_id', 'unknown'),
            'timestamp': datetime.utcnow().isoformat(),
            'execution_order': [],
            'results': {},
            'status': RemediationStatus.IN_PROGRESS.value
        }

        executed_steps = []
        try:
            # Step 1: EC2 remediation
            if threat.get('instance_id'):
                ec2_result = self.ec2.remediate_unauthorized_instance(
                    threat['instance_id'], threat
                )
                result['results']['ec2'] = ec2_result
                result['execution_order'].append('ec2')
                executed_steps.append(('ec2', ec2_result))

                if ec2_result.get('status') != 'success':
                    raise Exception('EC2 remediation failed')

            # Step 2: Network remediation (depends on EC2)
            if threat.get('instance_id'):
                network_result = self.network.isolate_instance(
                    threat['instance_id'], threat
                )
                result['results']['network'] = network_result
                result['execution_order'].append('network')
                executed_steps.append(('network', network_result))

                if network_result.get('status') != 'success':
                    raise Exception('Network remediation failed')

            # Step 3: IAM remediation (depends on principal)
            if threat.get('principal'):
                iam_result = self.iam.remediate_excessive_permissions(
                    threat['principal'], threat
                )
                result['results']['iam'] = iam_result
                result['execution_order'].append('iam')
                executed_steps.append(('iam', iam_result))

                if iam_result.get('status') != 'success':
                    raise Exception('IAM remediation failed')

            # Step 4: S3 remediation (depends on bucket)
            if threat.get('bucket_name'):
                s3_result = self.s3.remediate_public_access(
                    threat['bucket_name'], threat
                )
                result['results']['s3'] = s3_result
                result['execution_order'].append('s3')
                executed_steps.append(('s3', s3_result))

                if s3_result.get('status') != 'success':
                    raise Exception('S3 remediation failed')

            result['status'] = RemediationStatus.SUCCESS.value

            # Store execution history with resources
            history_entry = {
                'threat_id': threat.get('threat_id'),
                'executed_steps': executed_steps,
                'timestamp': result['timestamp'],
                'resources': {
                    'instance_id': threat.get('instance_id'),
                    'principal': threat.get('principal'),
                    'bucket_name': threat.get('bucket_name')
                }
            }
            self.execution_history[orchestration_id] = history_entry

            # Audit log
            self.audit.log_orchestration(orchestration_id, result)

        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['error'] = str(e)
            result['failed_step'] = len(executed_steps)

            # Attempt rollback cascade
            rollback_info = self._rollback_cascade(threat, executed_steps)
            if rollback_info:
                result['rollback_info'] = rollback_info
                result['status'] = RemediationStatus.ROLLED_BACK.value

            self.audit.log_orchestration(orchestration_id, result)

        return result

    def _rollback_cascade(self, threat: Dict, executed_steps: List) -> Optional[Dict]:
        """Rollback all executed steps in reverse order."""
        rollback_info = {
            'steps': [],
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            # Rollback in reverse order
            for step_type, step_result in reversed(executed_steps):
                if step_type == 'network' and threat.get('instance_id'):
                    rollback_result = self.network.restore_connectivity(
                        threat['instance_id']
                    )
                    rollback_info['steps'].append({
                        'step': 'network',
                        'status': rollback_result.get('status')
                    })
                elif step_type == 'ec2' and threat.get('instance_id'):
                    # For EC2, we can try to start the instance again
                    rollback_result = self.ec2.resume_instance(
                        threat['instance_id']
                    )
                    rollback_info['steps'].append({
                        'step': 'ec2',
                        'status': rollback_result.get('status')
                    })

            return rollback_info

        except Exception as e:
            rollback_info['error'] = str(e)
            return rollback_info

    def correlate_resources_by_threat(self, threat_id: str) -> Dict:
        """Find all resources affected by same threat ID."""
        correlation = {
            'threat_id': threat_id,
            'resources': {
                'instances': [],
                'principals': [],
                'buckets': []
            },
            'timestamp': datetime.utcnow().isoformat()
        }

        # Search execution history for related resources
        for orch_id, history in self.execution_history.items():
            if history.get('threat_id') == threat_id:
                resources = history.get('resources', {})
                if resources.get('instance_id'):
                    correlation['resources']['instances'].append(resources['instance_id'])
                if resources.get('principal'):
                    correlation['resources']['principals'].append(resources['principal'])
                if resources.get('bucket_name'):
                    correlation['resources']['buckets'].append(resources['bucket_name'])

        return correlation

    def get_orchestration_status(self, orchestration_id: str) -> Dict:
        """Get status of a specific orchestration execution."""
        if orchestration_id not in self.execution_history:
            return {
                'status': 'not_found',
                'orchestration_id': orchestration_id
            }

        history = self.execution_history[orchestration_id]
        return {
            'orchestration_id': orchestration_id,
            'threat_id': history.get('threat_id'),
            'executed_steps': len(history.get('executed_steps', [])),
            'timestamp': history.get('timestamp')
        }
