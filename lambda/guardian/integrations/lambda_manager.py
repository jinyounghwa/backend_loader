"""Real AWS Lambda API client for function management."""

import logging
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError

from guardian.config import Config

logger = logging.getLogger(__name__)


class LambdaManager:
    """AWS Lambda manager for function operations."""

    def __init__(self, clients: Optional[Dict[str, Any]] = None):
        """Initialize Lambda manager.
        
        Args:
            clients: Dict of pre-configured boto3 clients (for testing)
        """
        self.clients = clients or {}
        self._lambda_client = self.clients.get("lambda")

    @property
    def lambda_client(self):
        """Lazy Lambda client."""
        if self._lambda_client is None:
            self._lambda_client = boto3.client("lambda", **Config.get_boto3_kwargs())
        return self._lambda_client

    def list_functions(self) -> List[Dict[str, Any]]:
        """List all Lambda functions.
        
        Returns:
            List of function details
        """
        try:
            response = self.lambda_client.list_functions()
            functions = []
            for func in response['Functions']:
                functions.append({
                    'name': func['FunctionName'],
                    'runtime': func['Runtime'],
                    'memory': func['MemorySize'],
                    'timeout': func['Timeout'],
                    'last_modified': func['LastModified'],
                })
            return functions
        except ClientError as e:
            logger.error(f"Failed to list Lambda functions: {e}")
            return []

    def get_function_config(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a Lambda function.
        
        Args:
            function_name: Function name or ARN
            
        Returns:
            Function config or None
        """
        try:
            response = self.lambda_client.get_function_configuration(
                FunctionName=function_name
            )
            return {
                'name': response['FunctionName'],
                'runtime': response['Runtime'],
                'memory': response['MemorySize'],
                'timeout': response['Timeout'],
                'handler': response['Handler'],
                'last_modified': response['LastModified'],
            }
        except ClientError as e:
            logger.error(f"Failed to get Lambda config: {e}")
            return None

    def update_memory(self, function_name: str, memory_mb: int) -> bool:
        """Update function memory.
        
        Args:
            function_name: Function name or ARN
            memory_mb: New memory size (128-10240)
            
        Returns:
            True if successful
        """
        try:
            if memory_mb < 128 or memory_mb > 10240:
                logger.error(f"Invalid memory size: {memory_mb}")
                return False
            
            self.lambda_client.update_function_configuration(
                FunctionName=function_name,
                MemorySize=memory_mb,
            )
            logger.info(f"Updated {function_name} memory to {memory_mb}MB")
            return True
        except ClientError as e:
            logger.error(f"Failed to update memory: {e}")
            return False

    def update_timeout(self, function_name: str, timeout_seconds: int) -> bool:
        """Update function timeout.
        
        Args:
            function_name: Function name or ARN
            timeout_seconds: New timeout (1-900)
            
        Returns:
            True if successful
        """
        try:
            if timeout_seconds < 1 or timeout_seconds > 900:
                logger.error(f"Invalid timeout: {timeout_seconds}")
                return False
            
            self.lambda_client.update_function_configuration(
                FunctionName=function_name,
                Timeout=timeout_seconds,
            )
            logger.info(f"Updated {function_name} timeout to {timeout_seconds}s")
            return True
        except ClientError as e:
            logger.error(f"Failed to update timeout: {e}")
            return False

    def get_metrics(self, function_name: str) -> Dict[str, Any]:
        """Get CloudWatch metrics for Lambda function.
        
        Args:
            function_name: Function name
            
        Returns:
            Dictionary of metrics
        """
        try:
            cloudwatch = boto3.client("cloudwatch", **Config.get_boto3_kwargs())
            
            invocations = cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[
                    {'Name': 'FunctionName', 'Value': function_name},
                ],
                StartTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ) - __import__('datetime').timedelta(hours=1),
                EndTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ),
                Period=300,
                Statistics=['Sum'],
            )
            
            duration = cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Duration',
                Dimensions=[
                    {'Name': 'FunctionName', 'Value': function_name},
                ],
                StartTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ) - __import__('datetime').timedelta(hours=1),
                EndTime=__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ),
                Period=300,
                Statistics=['Average'],
            )
            
            total_invocations = sum(
                dp['Sum'] for dp in invocations['Datapoints']
            )
            avg_duration = (
                duration['Datapoints'][-1]['Average']
                if duration['Datapoints']
                else 0
            )
            
            return {
                'total_invocations': total_invocations,
                'avg_duration_ms': avg_duration,
            }
        except Exception as e:
            logger.error(f"Failed to get Lambda metrics: {e}")
            return {}
