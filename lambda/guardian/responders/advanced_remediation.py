"""Advanced Remediation System (Sprint 37)

Supports complex remediation scenarios with multiple AWS services.
Handles Lambda, RDS, VPC, and network-level remediations.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

from guardian.responders.aws_action_executor import AWSActionExecutor
from guardian.detectors.anomaly_detector import Threat

logger = logging.getLogger(__name__)


@dataclass
class AdvancedRemediationResult:
    """Result of an advanced remediation action"""
    action_type: str
    success: bool
    target: str
    message: str
    timestamp: str
    rollback_metadata: Optional[Dict[str, Any]] = None


class AdvancedRemediationExecutor:
    """Executes advanced remediation actions across multiple AWS services"""

    def __init__(self, aws_executor: Optional[AWSActionExecutor] = None):
        """
        Initialize advanced remediation executor
        Args:
            aws_executor: AWSActionExecutor instance
        """
        self.aws_executor = aws_executor or AWSActionExecutor()

    def execute_lambda_remediation(
        self,
        action: Dict[str, Any],
        threat: Threat
    ) -> Optional[AdvancedRemediationResult]:
        """
        Execute Lambda function remediation
        Supports: LAMBDA_DISABLE, LAMBDA_LAYER_REMOVE, LAMBDA_CONCURRENCY_LIMIT
        """
        action_type = action.get('type')
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            function_name = self._extract_lambda_function_name(threat, action)
            if not function_name:
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=False,
                    target='unknown',
                    message='Could not extract Lambda function name from threat',
                    timestamp=timestamp
                )

            region = action.get('parameters', {}).get('region', 'us-east-1')

            if action_type == 'LAMBDA_DISABLE':
                success = self.aws_executor.disable_lambda_function(function_name, region)
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=function_name,
                    message=f"{'Successfully disabled' if success else 'Failed to disable'} Lambda function {function_name}",
                    timestamp=timestamp,
                    rollback_metadata={"function_name": function_name, "region": region}
                )

            elif action_type == 'LAMBDA_LAYER_REMOVE':
                layer_arn = action.get('parameters', {}).get('layer_arn')
                if not layer_arn:
                    return AdvancedRemediationResult(
                        action_type=action_type,
                        success=False,
                        target=function_name,
                        message='Layer ARN not specified in action parameters',
                        timestamp=timestamp
                    )

                success = self.aws_executor.remove_lambda_layer(function_name, layer_arn, region)
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=f"{function_name}:{layer_arn}",
                    message=f"{'Successfully removed' if success else 'Failed to remove'} layer from {function_name}",
                    timestamp=timestamp,
                    rollback_metadata={"function_name": function_name, "layer_arn": layer_arn, "region": region}
                )

            elif action_type == 'LAMBDA_CONCURRENCY_LIMIT':
                max_concurrency = action.get('parameters', {}).get('max_concurrency', 1)
                success = self.aws_executor.restrict_lambda_concurrency(
                    function_name,
                    max_concurrency,
                    region
                )
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=function_name,
                    message=f"{'Successfully restricted' if success else 'Failed to restrict'} concurrency for {function_name}",
                    timestamp=timestamp,
                    rollback_metadata={
                        "function_name": function_name,
                        "max_concurrency": max_concurrency,
                        "region": region
                    }
                )

        except Exception as e:
            logger.error(f"Error executing Lambda remediation: {e}")
            return AdvancedRemediationResult(
                action_type=action_type,
                success=False,
                target='unknown',
                message=str(e),
                timestamp=timestamp
            )

        return None

    def execute_rds_remediation(
        self,
        action: Dict[str, Any],
        threat: Threat
    ) -> Optional[AdvancedRemediationResult]:
        """
        Execute RDS database remediation
        Supports: RDS_SNAPSHOT, RDS_DISABLE_PUBLIC, RDS_ENCRYPT_ENABLE, RDS_BACKUP_ENABLE
        """
        action_type = action.get('type')
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            db_instance_id = self._extract_rds_instance_id(threat, action)
            if not db_instance_id:
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=False,
                    target='unknown',
                    message='Could not extract RDS instance from threat',
                    timestamp=timestamp
                )

            region = action.get('parameters', {}).get('region', 'us-east-1')

            if action_type == 'RDS_SNAPSHOT':
                success = self.aws_executor.create_rds_snapshot(db_instance_id, region)
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=db_instance_id,
                    message=f"{'Successfully created' if success else 'Failed to create'} snapshot for {db_instance_id}",
                    timestamp=timestamp,
                    rollback_metadata={"db_instance_id": db_instance_id, "region": region}
                )

            elif action_type == 'RDS_DISABLE_PUBLIC':
                success = self.aws_executor.disable_rds_public_access(db_instance_id, region)
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=db_instance_id,
                    message=f"{'Successfully disabled' if success else 'Failed to disable'} public access for {db_instance_id}",
                    timestamp=timestamp,
                    rollback_metadata={"db_instance_id": db_instance_id, "region": region}
                )

            elif action_type == 'RDS_ENCRYPT_ENABLE':
                success = self.aws_executor.enable_rds_encryption(db_instance_id, region)
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=db_instance_id,
                    message=f"{'Successfully enabled' if success else 'Failed to enable'} encryption for {db_instance_id}",
                    timestamp=timestamp,
                    rollback_metadata={"db_instance_id": db_instance_id, "region": region}
                )

            elif action_type == 'RDS_BACKUP_ENABLE':
                backup_retention = action.get('parameters', {}).get('backup_retention_days', 7)
                success = self.aws_executor.enable_rds_backups(db_instance_id, backup_retention, region)
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=db_instance_id,
                    message=f"{'Successfully enabled' if success else 'Failed to enable'} backups for {db_instance_id}",
                    timestamp=timestamp,
                    rollback_metadata={
                        "db_instance_id": db_instance_id,
                        "backup_retention_days": backup_retention,
                        "region": region
                    }
                )

        except Exception as e:
            logger.error(f"Error executing RDS remediation: {e}")
            return AdvancedRemediationResult(
                action_type=action_type,
                success=False,
                target='unknown',
                message=str(e),
                timestamp=timestamp
            )

        return None

    def execute_vpc_remediation(
        self,
        action: Dict[str, Any],
        threat: Threat
    ) -> Optional[AdvancedRemediationResult]:
        """
        Execute VPC and network remediation
        Supports: VPC_ISOLATE, ROUTE_REMOVE, NACL_RESTRICT, ELB_DEREGISTER
        """
        action_type = action.get('type')
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            params = action.get('parameters', {})
            region = params.get('region', 'us-east-1')

            if action_type == 'VPC_ISOLATE':
                resource_id = params.get('resource_id')
                target_vpc = params.get('target_vpc')
                if not resource_id or not target_vpc:
                    return AdvancedRemediationResult(
                        action_type=action_type,
                        success=False,
                        target='unknown',
                        message='Resource ID and target VPC required',
                        timestamp=timestamp
                    )
                success = self.aws_executor.isolate_resource_in_vpc(resource_id, target_vpc, region)
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=f"{resource_id}→{target_vpc}",
                    message=f"{'Successfully isolated' if success else 'Failed to isolate'} {resource_id} to VPC {target_vpc}",
                    timestamp=timestamp,
                    rollback_metadata={"resource_id": resource_id, "target_vpc": target_vpc, "region": region}
                )

            elif action_type == 'ROUTE_REMOVE':
                route_table_id = params.get('route_table_id')
                destination_cidr = params.get('destination_cidr')
                if not route_table_id or not destination_cidr:
                    return AdvancedRemediationResult(
                        action_type=action_type,
                        success=False,
                        target='unknown',
                        message='Route table ID and destination CIDR required',
                        timestamp=timestamp
                    )
                success = self.aws_executor.remove_route_from_table(route_table_id, destination_cidr, region)
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=f"{route_table_id}/{destination_cidr}",
                    message=f"{'Successfully removed' if success else 'Failed to remove'} route {destination_cidr} from {route_table_id}",
                    timestamp=timestamp,
                    rollback_metadata={
                        "route_table_id": route_table_id,
                        "destination_cidr": destination_cidr,
                        "region": region
                    }
                )

            elif action_type == 'NACL_RESTRICT':
                nacl_id = params.get('nacl_id')
                if not nacl_id:
                    return AdvancedRemediationResult(
                        action_type=action_type,
                        success=False,
                        target='unknown',
                        message='NACL ID required',
                        timestamp=timestamp
                    )
                success = self.aws_executor.restrict_nacl_access(nacl_id, region)
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=nacl_id,
                    message=f"{'Successfully restricted' if success else 'Failed to restrict'} NACL {nacl_id}",
                    timestamp=timestamp,
                    rollback_metadata={"nacl_id": nacl_id, "region": region}
                )

            elif action_type == 'ELB_DEREGISTER':
                load_balancer_arn = params.get('load_balancer_arn')
                target_id = params.get('target_id')
                target_port = params.get('target_port', 80)
                if not load_balancer_arn or not target_id:
                    return AdvancedRemediationResult(
                        action_type=action_type,
                        success=False,
                        target='unknown',
                        message='Load balancer ARN and target ID required',
                        timestamp=timestamp
                    )
                success = self.aws_executor.deregister_target_from_load_balancer(
                    load_balancer_arn, target_id, target_port, region
                )
                return AdvancedRemediationResult(
                    action_type=action_type,
                    success=success,
                    target=f"{load_balancer_arn}/{target_id}",
                    message=f"{'Successfully deregistered' if success else 'Failed to deregister'} target {target_id} from load balancer",
                    timestamp=timestamp,
                    rollback_metadata={
                        "load_balancer_arn": load_balancer_arn,
                        "target_id": target_id,
                        "target_port": target_port,
                        "region": region
                    }
                )

        except Exception as e:
            logger.error(f"Error executing VPC remediation: {e}")
            return AdvancedRemediationResult(
                action_type=action_type,
                success=False,
                target='unknown',
                message=str(e),
                timestamp=timestamp
            )

        return None

    @staticmethod
    def _extract_lambda_function_name(threat: Threat, action: Dict[str, Any]) -> Optional[str]:
        """Extract Lambda function name from threat or action parameters"""
        # Check parameters first
        function_name = action.get('parameters', {}).get('function_name')
        if function_name:
            return function_name

        # Check threat evidence
        if threat.evidence:
            for item in threat.evidence:
                if isinstance(item, dict):
                    if 'function_name' in item:
                        return item['function_name']
                    if 'FunctionName' in item:
                        return item['FunctionName']
                    if 'function_arn' in item:
                        # Extract function name from ARN
                        arn = item['function_arn']
                        return arn.split(':')[-1] if ':' in arn else arn

        return None

    @staticmethod
    def _extract_rds_instance_id(threat: Threat, action: Dict[str, Any]) -> Optional[str]:
        """Extract RDS instance ID from threat or action parameters"""
        db_id = action.get('parameters', {}).get('db_instance_id')
        if db_id:
            return db_id

        if threat.evidence:
            for item in threat.evidence:
                if isinstance(item, dict):
                    if 'db_instance_id' in item:
                        return item['db_instance_id']
                    if 'DBInstanceIdentifier' in item:
                        return item['DBInstanceIdentifier']

        return None
