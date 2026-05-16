"""Singleton AWS Client Provider for managing boto3 and aioboto3 clients"""

import logging
from typing import Any, Dict, Optional

import boto3

try:
    import aioboto3
except ImportError:
    aioboto3 = None

from guardian.config import Config

logger = logging.getLogger(__name__)


class AWSClientProvider:
    _clients: Dict[str, Any] = {}
    _session: Optional[boto3.Session] = None
    _account_sessions: Dict[str, boto3.Session] = {}
    _aioboto3_session: Optional[Any] = None

    @classmethod
    def _get_clients_dict(cls) -> Dict[str, Any]:
        """Return the class-level client cache, ensuring a fresh dict after clear_cache()."""
        if cls._clients is None:
            cls._clients = {}
        return cls._clients

    @classmethod
    def get_session(cls) -> boto3.Session:
        if cls._session is None:
            boto3_kwargs = Config.get_boto3_kwargs()
            session_kwargs = {k: v for k, v in boto3_kwargs.items() if k != "endpoint_url"}
            cls._session = boto3.Session(**session_kwargs)
            logger.debug("Created new boto3 session")
        return cls._session

    @classmethod
    def create_session_from_credentials(cls, credentials: Dict[str, str]) -> boto3.Session:
        """Create a boto3 session from temporary credentials (for cross-account access)."""
        session = boto3.Session(
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            aws_session_token=credentials["aws_session_token"],
        )
        logger.debug("Created boto3 session from temporary credentials")
        return session

    @classmethod
    def get_client_for_account(
        cls,
        service_name: str,
        account_id: str,
        credentials: Dict[str, str],
        region: Optional[str] = None,
    ) -> Any:
        """Get a client using cross-account temporary credentials."""
        cache_key = f"{service_name}-account-{account_id}-{region or 'default'}"

        clients = cls._get_clients_dict()
        if cache_key not in clients:
            session = cls.create_session_from_credentials(credentials)
            client_kwargs = {}
            if region:
                client_kwargs["region_name"] = region

            boto3_kwargs = Config.get_boto3_kwargs()
            if "endpoint_url" in boto3_kwargs:
                client_kwargs["endpoint_url"] = boto3_kwargs["endpoint_url"]

            cls._clients[cache_key] = session.client(service_name, **client_kwargs)
            logger.debug(
                "Created cross-account boto3 client for %s (account=%s, region=%s)",
                service_name,
                account_id,
                region or "default",
            )

        return clients[cache_key]

    @classmethod
    def get_client(cls, service_name: str, region: Optional[str] = None) -> Any:
        cache_key = f"{service_name}-{region or 'default'}"

        clients = cls._get_clients_dict()
        if cache_key not in clients:
            session = cls.get_session()
            client_kwargs = {}
            if region:
                client_kwargs["region_name"] = region

            boto3_kwargs = Config.get_boto3_kwargs()
            if "endpoint_url" in boto3_kwargs:
                client_kwargs["endpoint_url"] = boto3_kwargs["endpoint_url"]

            clients[cache_key] = session.client(service_name, **client_kwargs)
            logger.debug(
                "Created new boto3 client for %s (region=%s)", service_name, region or "default"
            )

        return clients[cache_key]

    @classmethod
    def get_resource(cls, service_name: str, region: Optional[str] = None) -> Any:
        cache_key = f"resource-{service_name}-{region or 'default'}"

        clients = cls._get_clients_dict()
        if cache_key not in clients:
            session = cls.get_session()
            resource_kwargs = {}
            if region:
                resource_kwargs["region_name"] = region

            boto3_kwargs = Config.get_boto3_kwargs()
            if "endpoint_url" in boto3_kwargs:
                resource_kwargs["endpoint_url"] = boto3_kwargs["endpoint_url"]

            clients[cache_key] = session.resource(service_name, **resource_kwargs)
            logger.debug(
                "Created new boto3 resource for %s (region=%s)", service_name, region or "default"
            )

        return clients[cache_key]

    @classmethod
    def clear_cache(cls):
        cls._clients = {}
        cls._session = None
        cls._account_sessions = {}
        cls._aioboto3_session = None

    @classmethod
    def get_aioboto3_session(cls) -> Optional[Any]:
        """Get or create aioboto3 session for async operations."""
        if aioboto3 is None:
            logger.warning("aioboto3 not installed, async operations unavailable")
            return None

        if cls._aioboto3_session is None:
            boto3_kwargs = Config.get_boto3_kwargs()
            session_kwargs = {k: v for k, v in boto3_kwargs.items() if k != "endpoint_url"}
            cls._aioboto3_session = aioboto3.Session(**session_kwargs)
            logger.debug("Created new aioboto3 session")

        return cls._aioboto3_session

    @classmethod
    async def get_async_client(cls, service_name: str, region: Optional[str] = None) -> Any:
        """Get async client context manager for aioboto3.

        Usage:
            async with AWSClientProvider.get_async_client("ec2") as client:
                response = await client.describe_instances()
        """
        session = cls.get_aioboto3_session()
        if session is None:
            raise RuntimeError("aioboto3 not available")

        kwargs = {}
        if region:
            kwargs["region_name"] = region

        boto3_kwargs = Config.get_boto3_kwargs()
        if "endpoint_url" in boto3_kwargs:
            kwargs["endpoint_url"] = boto3_kwargs["endpoint_url"]

        return session.client(service_name, **kwargs)

    @classmethod
    async def assume_role_async(
        cls,
        account_id: str,
        role_name: str = "GuardianCrossAccountRole",
        session_duration: int = 3600,
    ) -> Dict[str, str]:
        """Assume role in target account and return temporary credentials.

        Args:
            account_id: Target AWS account ID
            role_name: IAM role name in target account
            session_duration: Duration of session in seconds

        Returns:
            Dictionary with temporary credentials (AccessKeyId, SecretAccessKey, SessionToken)
        """
        async with await cls.get_async_client("sts") as sts_client:
            role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
            response = await sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=f"guardian-{account_id}",
                DurationSeconds=session_duration,
            )

            credentials = response["Credentials"]
            logger.debug("Successfully assumed role in account %s", account_id)
            return {
                "aws_access_key_id": credentials["AccessKeyId"],
                "aws_secret_access_key": credentials["SecretAccessKey"],
                "aws_session_token": credentials["SessionToken"],
            }

    @classmethod
    async def get_async_client_for_account(
        cls,
        service_name: str,
        account_id: str,
        region: Optional[str] = None,
    ) -> Any:
        """Get async client for cross-account access.

        Args:
            service_name: AWS service name (ec2, s3, etc.)
            account_id: Target AWS account ID
            region: Optional region name

        Returns:
            Async client context manager
        """
        credentials = await cls.assume_role_async(account_id)

        if aioboto3 is None:
            raise RuntimeError("aioboto3 not available")

        session = aioboto3.Session(
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            aws_session_token=credentials["aws_session_token"],
        )

        kwargs = {}
        if region:
            kwargs["region_name"] = region

        boto3_kwargs = Config.get_boto3_kwargs()
        if "endpoint_url" in boto3_kwargs:
            kwargs["endpoint_url"] = boto3_kwargs["endpoint_url"]

        return session.client(service_name, **kwargs)
