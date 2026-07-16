"""Cross-account role assumption using AWS STS."""

import logging
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

from guardian.config import Config

logger = logging.getLogger(__name__)


class RoleAssumptioner:
    """Assume IAM roles in member accounts."""

    def __init__(self, clients: Optional[Dict[str, Any]] = None):
        """Initialize role assumptioner.
        
        Args:
            clients: Dict of pre-configured boto3 clients (for testing)
        """
        self.clients = clients or {}
        self._sts_client = self.clients.get("sts")

    @property
    def sts_client(self):
        """Lazy STS client."""
        if self._sts_client is None:
            self._sts_client = boto3.client("sts", **Config.get_boto3_kwargs())
        return self._sts_client

    def assume_role(
        self,
        role_arn: str,
        session_name: str,
        duration_seconds: int = 3600,
    ) -> Optional[Dict[str, Any]]:
        """Assume a role in another account.
        
        Args:
            role_arn: ARN of role to assume
            session_name: Session name for the assumption
            duration_seconds: Duration for assumed session
            
        Returns:
            Credentials dict or None
        """
        try:
            assume_kwargs: Dict[str, Any] = {
                "RoleArn": role_arn,
                "RoleSessionName": session_name,
                "DurationSeconds": duration_seconds,
            }
            # Confused-deputy protection: include ExternalId when configured.
            external_id = Config.get_cross_account_external_id()
            if external_id:
                assume_kwargs["ExternalId"] = external_id
            response = self.sts_client.assume_role(**assume_kwargs)

            credentials = response['Credentials']
            return {
                'access_key': credentials['AccessKeyId'],
                'secret_key': credentials['SecretAccessKey'],
                'session_token': credentials['SessionToken'],
                'expiration': credentials['Expiration'].isoformat(),
            }
        except ClientError as e:
            logger.error(f"Failed to assume role {role_arn}: {e}")
            return None

    def get_caller_identity(self) -> Optional[Dict[str, Any]]:
        """Get current caller identity.
        
        Returns:
            Identity details or None
        """
        try:
            response = self.sts_client.get_caller_identity()
            return {
                'account_id': response['Account'],
                'user_id': response['UserId'],
                'arn': response['Arn'],
            }
        except ClientError as e:
            logger.error(f"Failed to get caller identity: {e}")
            return None

    def create_client_with_assumed_role(
        self,
        service: str,
        role_arn: str,
        session_name: str,
    ) -> Optional[Any]:
        """Create a boto3 client using assumed role credentials.
        
        Args:
            service: AWS service name (e.g., 'ec2', 'dynamodb')
            role_arn: ARN of role to assume
            session_name: Session name
            
        Returns:
            Configured boto3 client or None
        """
        credentials = self.assume_role(role_arn, session_name)
        if not credentials:
            return None
        
        try:
            session = boto3.Session(
                aws_access_key_id=credentials['access_key'],
                aws_secret_access_key=credentials['secret_key'],
                aws_session_token=credentials['session_token'],
            )
            return session.client(service, **Config.get_boto3_kwargs())
        except Exception as e:
            logger.error(f"Failed to create client: {e}")
            return None
