"""Pattern matching engine for CloudTrail anomaly detection."""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class PatternMatcher:
    """Detect suspicious patterns in CloudTrail events."""

    def __init__(self):
        """Initialize pattern matcher."""
        self.detections = []

    def detect_unauthorized_region(
        self, events: List[Dict[str, Any]], allowed_regions: List[str]
    ) -> List[Dict[str, Any]]:
        """Detect EC2 operations in unexpected regions.
        
        Args:
            events: List of CloudTrail events
            allowed_regions: List of allowed AWS regions
            
        Returns:
            List of suspicious events
        """
        suspicious = []
        ec2_events = [
            e for e in events
            if e.get('event_source') == 'ec2.amazonaws.com'
        ]
        
        for event in ec2_events:
            region = event.get('aws_region')
            if region and region not in allowed_regions:
                suspicious.append({
                    'pattern': 'unauthorized_region',
                    'event': event,
                    'detail': f"EC2 operation in unexpected region: {region}",
                })
        
        return suspicious

    def detect_mass_deletion(
        self, events: List[Dict[str, Any]], threshold: int = 5
    ) -> List[Dict[str, Any]]:
        """Detect bulk resource deletion attempts.
        
        Args:
            events: List of CloudTrail events
            threshold: Number of deletions to trigger alert
            
        Returns:
            List of suspicious patterns
        """
        suspicious = []
        deletion_events = [
            e for e in events
            if 'Delete' in e.get('event_name', '')
        ]
        
        user_deletions = {}
        for event in deletion_events:
            username = event.get('username')
            if not username:
                continue
            
            if username not in user_deletions:
                user_deletions[username] = []
            user_deletions[username].append(event)
        
        for username, deletions in user_deletions.items():
            if len(deletions) >= threshold:
                suspicious.append({
                    'pattern': 'mass_deletion',
                    'username': username,
                    'deletion_count': len(deletions),
                    'events': deletions,
                    'detail': f"{username} performed {len(deletions)} deletions",
                })
        
        return suspicious

    def detect_permission_escalation(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect IAM policy changes that could escalate permissions.
        
        Args:
            events: List of CloudTrail events
            
        Returns:
            List of suspicious events
        """
        suspicious = []
        iam_events = [
            e for e in events
            if e.get('event_source') == 'iam.amazonaws.com'
        ]
        
        escalation_indicators = [
            'PutUserPolicy',
            'AttachUserPolicy',
            'CreateAccessKey',
            'UpdateAssumeRolePolicy',
        ]
        
        for event in iam_events:
            event_name = event.get('event_name')
            if event_name in escalation_indicators:
                suspicious.append({
                    'pattern': 'permission_escalation',
                    'event': event,
                    'detail': f"Potential permission escalation: {event_name}",
                })
        
        return suspicious

    def detect_auth_anomaly(
        self, events: List[Dict[str, Any]], failed_threshold: int = 3
    ) -> List[Dict[str, Any]]:
        """Detect unusual authentication patterns.
        
        Args:
            events: List of CloudTrail events
            failed_threshold: Number of failures to trigger alert
            
        Returns:
            List of suspicious patterns
        """
        suspicious = []
        failed_auth = [
            e for e in events
            if e.get('error_code') and 'Unauthorized' in e.get('error_message', '')
        ]
        
        user_failures = {}
        for event in failed_auth:
            username = event.get('username')
            if not username:
                continue
            
            if username not in user_failures:
                user_failures[username] = []
            user_failures[username].append(event)
        
        for username, failures in user_failures.items():
            if len(failures) >= failed_threshold:
                suspicious.append({
                    'pattern': 'auth_anomaly',
                    'username': username,
                    'failure_count': len(failures),
                    'events': failures,
                    'detail': f"{username} has {len(failures)} failed auth attempts",
                })
        
        return suspicious

    def detect_cost_spike_trigger(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect resource provisioning spikes.
        
        Args:
            events: List of CloudTrail events
            
        Returns:
            List of suspicious provisioning events
        """
        suspicious = []
        provisioning_events = [
            'RunInstances',
            'CreateDBInstance',
            'CreateFunction',
            'PutObject',
        ]
        
        provisioning = [
            e for e in events
            if e.get('event_name') in provisioning_events
        ]
        
        if len(provisioning) > 10:
            suspicious.append({
                'pattern': 'cost_spike_trigger',
                'event_count': len(provisioning),
                'events': provisioning,
                'detail': f"High volume of provisioning events ({len(provisioning)})",
            })
        
        return suspicious

    def detect_suspicious_api_patterns(
        self, events: List[Dict[str, Any]], rate_threshold: int = 50
    ) -> List[Dict[str, Any]]:
        """Detect suspicious API call patterns.
        
        Args:
            events: List of CloudTrail events
            rate_threshold: Calls per minute to trigger alert
            
        Returns:
            List of suspicious patterns
        """
        suspicious = []
        
        if len(events) > rate_threshold:
            suspicious.append({
                'pattern': 'suspicious_api_pattern',
                'call_count': len(events),
                'detail': f"High API call volume: {len(events)} calls",
            })
        
        return suspicious
