"""Singleton AWS Client Provider for managing boto3 clients"""
import boto3
from typing import Dict, Optional
from config import Config


class AWSClientProvider:
    """
    Manages and caches AWS service clients to optimize cold start performance.
    Ensures a single boto3 client is created per service type and region.
    """

    _clients: Dict[str, any] = {}
    _session: Optional[boto3.Session] = None

    @classmethod
    def get_session(cls) -> boto3.Session:
        """Get or create the boto3 session (reused across all clients)."""
        if cls._session is None:
            boto3_kwargs = Config.get_boto3_kwargs()
            cls._session = boto3.Session(**boto3_kwargs)
        return cls._session

    @classmethod
    def get_client(cls, service_name: str, region: Optional[str] = None) -> any:
        """
        Get or create a boto3 client for the specified service.

        Args:
            service_name: AWS service name (e.g., 'ec2', 's3', 'dynamodb')
            region: AWS region (optional, uses default if not specified)

        Returns:
            Cached boto3 client instance
        """
        cache_key = f"{service_name}-{region or 'default'}"

        if cache_key not in cls._clients:
            session = cls.get_session()
            client_kwargs = {}
            if region:
                client_kwargs['region_name'] = region
            cls._clients[cache_key] = session.client(service_name, **client_kwargs)

        return cls._clients[cache_key]

    @classmethod
    def clear_cache(cls):
        """Clear cached clients (useful for testing)."""
        cls._clients = {}
        cls._session = None
