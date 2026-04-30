"""Singleton AWS Client Provider for managing boto3 clients"""
import boto3
import logging
from typing import Dict, Optional

from guardian.config import Config

logger = logging.getLogger(__name__)


class AWSClientProvider:
    _clients: Dict[str, object] = {}
    _session: Optional[boto3.Session] = None

    @classmethod
    def get_session(cls) -> boto3.Session:
        if cls._session is None:
            boto3_kwargs = Config.get_boto3_kwargs()
            session_kwargs = {k: v for k, v in boto3_kwargs.items() if k != 'endpoint_url'}
            cls._session = boto3.Session(**session_kwargs)
            logger.debug("Created new boto3 session")
        return cls._session

    @classmethod
    def get_client(cls, service_name: str, region: Optional[str] = None) -> object:
        cache_key = f"{service_name}-{region or 'default'}"

        if cache_key not in cls._clients:
            session = cls.get_session()
            client_kwargs = {}
            if region:
                client_kwargs['region_name'] = region

            boto3_kwargs = Config.get_boto3_kwargs()
            if 'endpoint_url' in boto3_kwargs:
                client_kwargs['endpoint_url'] = boto3_kwargs['endpoint_url']

            cls._clients[cache_key] = session.client(service_name, **client_kwargs)
            logger.debug("Created new boto3 client for %s (region=%s)", service_name, region or 'default')

        return cls._clients[cache_key]

    @classmethod
    def get_resource(cls, service_name: str, region: Optional[str] = None) -> object:
        cache_key = f"resource-{service_name}-{region or 'default'}"

        if cache_key not in cls._clients:
            session = cls.get_session()
            resource_kwargs = {}
            if region:
                resource_kwargs['region_name'] = region

            boto3_kwargs = Config.get_boto3_kwargs()
            if 'endpoint_url' in boto3_kwargs:
                resource_kwargs['endpoint_url'] = boto3_kwargs['endpoint_url']

            cls._clients[cache_key] = session.resource(service_name, **resource_kwargs)
            logger.debug("Created new boto3 resource for %s (region=%s)", service_name, region or 'default')

        return cls._clients[cache_key]

    @classmethod
    def clear_cache(cls):
        cls._clients = {}
        cls._session = None
