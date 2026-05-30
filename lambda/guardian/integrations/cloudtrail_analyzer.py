"""CloudTrail event analysis and anomaly detection."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
import json


class CloudTrailEventParser:
    """Parse and normalize CloudTrail events."""

    EVENT_TYPE_MAPPING = {
        'RunInstances': 'EC2_LAUNCH',
        'TerminateInstances': 'EC2_TERMINATION',
        'StartInstances': 'EC2_START',
        'StopInstances': 'EC2_STOP',
        'PutUserPolicy': 'IAM_POLICY_UPDATE',
        'AttachUserPolicy': 'IAM_POLICY_ATTACH',
        'DetachUserPolicy': 'IAM_POLICY_DETACH',
        'DeleteBucket': 'S3_DELETION',
        'PutBucketPolicy': 'S3_POLICY_CHANGE',
        'DeleteDBInstance': 'RDS_DELETION',
        'ConsoleLogin': 'CONSOLE_LOGIN',
        'AssumeRole': 'ASSUME_ROLE',
    }

    def parse(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse CloudTrail event and normalize."""
        event_name = event.get('eventName', 'Unknown')
        event_type = self.EVENT_TYPE_MAPPING.get(event_name, f'OTHER_{event_name}')

        normalized = {
            'event_type': event_type,
            'event_name': event_name,
            'timestamp': self._parse_timestamp(event.get('eventTime')),
            'source_ip': event.get('sourceIPAddress'),
            'user_agent': event.get('userAgent'),
            'principal': event.get('userIdentity', {}).get('principalId'),
            'aws_region': event.get('awsRegion'),
            'request_parameters': event.get('requestParameters', {}),
            'response_elements': event.get('responseElements', {}),
            'error_code': event.get('errorCode'),
        }

        # Extract resource-specific IDs
        if event_type == 'EC2_LAUNCH' or event_type == 'EC2_TERMINATION':
            instances = event.get('responseElements', {}).get('instancesSet', {}).get('items', [])
            if instances:
                normalized['instance_id'] = instances[0].get('instanceId')

        elif event_type in ['IAM_POLICY_UPDATE', 'IAM_POLICY_ATTACH', 'IAM_POLICY_DETACH']:
            params = event.get('requestParameters', {})
            normalized['resource'] = params.get('userName') or params.get('groupName') or params.get('roleName')
            normalized['policy_name'] = params.get('policyName')
            normalized['policy_arn'] = params.get('policyArn')

        elif event_type == 'S3_DELETION':
            normalized['resource'] = event.get('requestParameters', {}).get('bucketName')

        elif event_type == 'RDS_DELETION':
            normalized['resource'] = event.get('requestParameters', {}).get('dBInstanceIdentifier')

        elif event_type == 'ASSUME_ROLE':
            normalized['resource'] = event.get('requestParameters', {}).get('roleArn')

        return normalized

    def _parse_timestamp(self, ts_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 timestamp."""
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            return None


class AnomalousActivityDetector:
    """Detect anomalous API activity patterns."""

    FREQUENCY_THRESHOLD = 10  # events per minute
    AUTH_FAILURE_THRESHOLD = 3  # failures in 5 minutes
    ANOMALY_BASELINE = 100  # baseline for anomaly scoring

    def detect_frequency_anomaly(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect unusually high API call frequency."""
        if not events:
            return {'is_anomalous': False, 'anomaly_score': 0}

        # Count events in windows
        event_counts = Counter()
        for event in events:
            ts = event.get('timestamp', datetime.now())
            if isinstance(ts, datetime):
                minute = ts.replace(second=0, microsecond=0)
                event_counts[minute] += 1

        max_count = max(event_counts.values()) if event_counts else 0
        is_anomalous = max_count > self.FREQUENCY_THRESHOLD

        anomaly_score = min(100, (max_count / self.FREQUENCY_THRESHOLD) * 80) if is_anomalous else 0

        return {
            'is_anomalous': is_anomalous,
            'anomaly_score': anomaly_score,
            'max_events_per_minute': max_count,
            'threshold': self.FREQUENCY_THRESHOLD
        }

    def detect_auth_anomaly(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect brute force or auth anomalies."""
        failed_attempts = [e for e in events if e.get('errorCode') == 'UnauthorizedOperation']

        if len(failed_attempts) < self.AUTH_FAILURE_THRESHOLD:
            return {'is_anomalous': False, 'anomaly_score': 0, 'anomaly_type': None}

        # Check if from same IP
        source_ips = set(e.get('sourceIPAddress') for e in failed_attempts)
        is_anomalous = len(failed_attempts) >= self.AUTH_FAILURE_THRESHOLD

        anomaly_score = min(100, (len(failed_attempts) / self.AUTH_FAILURE_THRESHOLD) * 85)

        return {
            'is_anomalous': is_anomalous,
            'anomaly_score': anomaly_score,
            'anomaly_type': 'brute_force_attempt',
            'failed_count': len(failed_attempts),
            'source_ips': list(source_ips)
        }

    def detect_region_anomaly(self, event: Dict[str, Any], authorized_regions: List[str]) -> Dict[str, Any]:
        """Detect API calls from unauthorized regions."""
        region = event.get('awsRegion')
        is_anomalous = region not in authorized_regions if authorized_regions else False

        anomaly_score = 75 if is_anomalous else 0

        return {
            'is_anomalous': is_anomalous,
            'anomaly_score': anomaly_score,
            'region': region,
            'authorized_regions': authorized_regions
        }

    def detect_escalation_pattern(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect permission escalation patterns."""
        escalation_indicators = [
            'AttachUserPolicy',
            'AttachRolePolicy',
            'PutUserPolicy',
            'CreateAccessKey',
            'CreateLoginProfile'
        ]

        matching_events = [
            e for e in events
            if e.get('eventName') in escalation_indicators
        ]

        is_anomalous = len(matching_events) >= 2

        return {
            'is_anomalous': is_anomalous,
            'anomaly_score': 85 if is_anomalous else 0,
            'pattern_type': 'privilege_escalation',
            'indicator_count': len(matching_events),
            'indicators': [e.get('eventName') for e in matching_events]
        }


class PermissionChangeTracker:
    """Track IAM permission changes."""

    CHANGE_TYPE_MAPPING = {
        'AttachUserPolicy': 'policy_attached',
        'DetachUserPolicy': 'policy_detached',
        'PutUserPolicy': 'policy_updated',
        'AttachRolePolicy': 'policy_attached',
        'DetachRolePolicy': 'policy_detached',
        'AssumeRole': 'assume_role',
        'CreateAccessKey': 'access_key_created',
        'DeleteAccessKey': 'access_key_deleted',
    }

    def track_change(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Track permission change."""
        event_name = event.get('eventName')
        change_type = self.CHANGE_TYPE_MAPPING.get(event_name, 'policy_changed')
        params = event.get('requestParameters', {})

        change = {
            'change_type': change_type,
            'event_name': event_name,
            'timestamp': event.get('eventTime'),
            'principal': event.get('userIdentity', {}).get('principalId'),
        }

        # Extract specific details
        if 'User' in event_name:
            change['principal'] = params.get('userName')
        elif 'Role' in event_name:
            change['role'] = params.get('roleArn') or params.get('roleName')
        elif 'Group' in event_name:
            change['group'] = params.get('groupName')

        if 'Policy' in event_name:
            change['policy'] = params.get('policyArn') or params.get('policyName')
            if params.get('policyArn'):
                # Extract policy name from ARN
                arn_parts = params.get('policyArn', '').split('/')
                change['policy'] = arn_parts[-1] if arn_parts else change['policy']

        return change


class ResourceDeleteMonitor:
    """Monitor resource deletion events."""

    DELETION_EVENTS = {
        'TerminateInstances': ('EC2_INSTANCE', 'instancesSet'),
        'DeleteBucket': ('S3_BUCKET', 'bucketName'),
        'DeleteDBInstance': ('RDS_DATABASE', 'dBInstanceIdentifier'),
        'DeleteSecurityGroup': ('SECURITY_GROUP', 'groupId'),
        'DeleteNetworkInterface': ('NETWORK_INTERFACE', 'networkInterfaceId'),
    }

    RISK_SCORES = {
        'S3_BUCKET': 90,
        'RDS_DATABASE': 85,
        'EC2_INSTANCE': 70,
        'SECURITY_GROUP': 65,
        'NETWORK_INTERFACE': 60,
    }

    def detect_deletion(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Detect resource deletion events."""
        event_name = event.get('eventName')

        if event_name not in self.DELETION_EVENTS:
            return {'is_deletion': False}

        resource_type, param_key = self.DELETION_EVENTS[event_name]
        params = event.get('requestParameters', {})

        # Extract resource ID
        resource_id = None
        if isinstance(params.get(param_key), dict):
            # Handle nested structures (e.g., instancesSet)
            items = params[param_key].get('items', [])
            if items and isinstance(items[0], dict):
                first_item_key = list(items[0].keys())[0]
                resource_id = items[0].get(first_item_key)
        else:
            resource_id = params.get(param_key)

        if not resource_id:
            resource_id = params.get('bucketName') or params.get('dBInstanceIdentifier')

        return {
            'is_deletion': True,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'timestamp': event.get('eventTime'),
            'principal': event.get('userIdentity', {}).get('principalId'),
            'risk_score': self.RISK_SCORES.get(resource_type, 50),
            'event_name': event_name
        }
