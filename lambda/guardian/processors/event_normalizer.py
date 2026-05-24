"""CloudTrail Event Normalization for Analysis"""

import logging
from typing import Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EventNormalizer:
    """Normalize CloudTrail events for threat analysis"""

    def __init__(self):
        """Initialize event normalizer"""
        pass

    def normalize_cloudtrail_event(self, raw_event: Dict) -> Dict:
        """
        Normalize CloudTrail event for analysis

        Args:
            raw_event: Raw CloudTrail event

        Returns:
            Normalized event with standardized fields
        """
        try:
            normalized = {
                'eventId': raw_event.get('eventID'),
                'eventName': raw_event.get('eventName'),
                'eventSource': raw_event.get('eventSource'),
                'eventTime': raw_event.get('eventTime'),
                'awsRegion': raw_event.get('awsRegion'),
                'sourceIP': raw_event.get('sourceIPAddress'),
                'userAgent': raw_event.get('userAgent'),
                'principal': self.extract_principal(raw_event),
                'resourceType': self._extract_resource_type(raw_event),
                'resourceName': self._extract_resource_name(raw_event),
                'apiParameters': self.get_api_parameters(raw_event),
                'riskScore': self.calculate_event_risk_score(raw_event),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.debug(f"Normalized event: {normalized['eventId']}")
            return normalized

        except Exception as e:
            logger.error(f"Failed to normalize event: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def extract_principal(self, event: Dict) -> Dict:
        """
        Extract principal (user/role) from event

        Args:
            event: CloudTrail event

        Returns:
            Principal information
        """
        try:
            user_identity = event.get('userIdentity', {})

            principal = {
                'principalId': user_identity.get('principalId'),
                'type': user_identity.get('type'),  # IAMUser, AssumedRole, Root, etc.
                'arn': user_identity.get('arn'),
                'accountId': user_identity.get('accountId'),
                'userName': user_identity.get('userName'),
                'invokedBy': user_identity.get('invokedBy')
            }

            logger.debug(f"Extracted principal: {principal['principalId']}")
            return principal

        except Exception as e:
            logger.error(f"Failed to extract principal: {str(e)}")
            return {}

    def get_api_parameters(self, event: Dict) -> Dict:
        """
        Get API parameters from event

        Args:
            event: CloudTrail event

        Returns:
            API request parameters
        """
        try:
            params = event.get('requestParameters', {})

            normalized_params = {
                'action': event.get('eventName'),
                'parameters': params,
                'parameterCount': len(params) if params else 0
            }

            logger.debug(f"Extracted parameters: {normalized_params['parameterCount']} fields")
            return normalized_params

        except Exception as e:
            logger.error(f"Failed to get API parameters: {str(e)}")
            return {}

    def calculate_event_risk_score(self, event: Dict) -> int:
        """
        Calculate risk score for event (0-10)

        Args:
            event: CloudTrail event

        Returns:
            Risk score
        """
        try:
            score = 0
            event_name = event.get('eventName', '')

            # Check event type risk
            dangerous_events = {
                'DeleteBucket': 9,
                'DeleteUser': 9,
                'DeleteRole': 9,
                'PutUserPolicy': 8,
                'PutRolePolicy': 8,
                'AttachUserPolicy': 7,
                'AttachRolePolicy': 7,
                'CreateAccessKey': 6,
                'ModifyDBInstance': 6,
                'CreateUser': 5,
                'CreateRole': 5,
                'PutBucketPolicy': 8,
                'DeleteObject': 8
            }

            if event_name in dangerous_events:
                score = dangerous_events[event_name]

            # Check source IP risk (external IP = higher risk)
            source_ip = event.get('sourceIPAddress', '')
            if source_ip and not source_ip.startswith(('10.', '172.', '192.168.')):
                score += 2

            # Check principal type risk
            user_identity = event.get('userIdentity', {})
            if user_identity.get('type') == 'Root':
                score += 2

            # Normalize to 0-10 range
            score = min(10, score)

            logger.debug(f"Calculated risk score: {score}/10 for {event_name}")
            return score

        except Exception as e:
            logger.error(f"Failed to calculate risk score: {str(e)}")
            return 0

    def _extract_resource_type(self, event: Dict) -> str:
        """Helper: Extract resource type from event"""
        event_source = event.get('eventSource', '')

        if 's3' in event_source:
            return 's3'
        elif 'ec2' in event_source:
            return 'ec2'
        elif 'iam' in event_source:
            return 'iam'
        elif 'lambda' in event_source:
            return 'lambda'
        elif 'rds' in event_source:
            return 'rds'

        return 'unknown'

    def _extract_resource_name(self, event: Dict) -> str:
        """Helper: Extract resource name from event"""
        response_elements = event.get('responseElements', {})

        # Try to find resource name from response
        if isinstance(response_elements, dict):
            if 'instancesSet' in response_elements:
                items = response_elements['instancesSet'].get('items', [])
                if items and isinstance(items, list) and 'instanceId' in items[0]:
                    return items[0]['instanceId']

        # Try request parameters
        request_params = event.get('requestParameters', {})
        if isinstance(request_params, dict):
            if 'bucketName' in request_params:
                return request_params['bucketName']
            if 'userName' in request_params:
                return request_params['userName']
            if 'roleName' in request_params:
                return request_params['roleName']

        return 'unknown'
