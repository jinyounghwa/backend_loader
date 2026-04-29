"""CloudTrail checker for suspicious API activity detection."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import logging

from guardian.checkers.base import BaseChecker, CheckResult

logger = logging.getLogger(__name__)


class CloudTrailChecker(BaseChecker):
    """Detect suspicious API calls from CloudTrail."""

    # API events that modify resources (ReadOnly=False)
    SUSPICIOUS_EVENTS = {
        'CreateAccessKey',
        'CreateUser',
        'AttachUserPolicy',
        'PutUserPolicy',
        'CreatePolicy',
        'CreateRole',
        'CreateSecurityGroup',
        'DeleteBucket',
        'DeleteTable',
        'TerminateInstances',
        'StopInstances',
        'ModifyDBInstance',
        'DeleteDBInstance'
    }

    # Authorized regions (customize as needed)
    def __init__(self, clients: Dict[str, Any], config: Dict[str, Any]):
        super().__init__(clients, config)
        self.cloudtrail = clients.get('cloudtrail')
        self.sts = clients.get('sts')
        self.hours_lookback = config.get('cloudtrail_hours', 1)
        self.authorized_regions = set(config.get('authorized_regions', ['us-east-1', 'us-west-2', 'eu-west-1']))

    def check(self) -> CheckResult:
        """Check for suspicious CloudTrail events."""
        self._log_check_start('CloudTrail')

        try:
            # Get events from last N hours
            events = self._get_recent_events()

            if not events:
                self._log_check_end('CloudTrail', 'INFO')
                return CheckResult.info(
                    'CloudTrail Check',
                    'No suspicious API calls detected'
                )

            # Analyze events for anomalies
            anomalies = self._analyze_events(events)

            if anomalies:
                severity = self._determine_severity(anomalies)
                self._log_check_end('CloudTrail', severity)

                return CheckResult(
                    severity=severity,
                    title='Suspicious API Calls Detected',
                    message=f'Found {len(anomalies)} suspicious API events in CloudTrail',
                    details={'anomalies': anomalies},
                    suggested_action='Review user activity and verify legitimate changes'
                )
            else:
                self._log_check_end('CloudTrail', 'INFO')
                return CheckResult.info(
                    'CloudTrail Check',
                    f'Analyzed {len(events)} API events - all appear normal'
                )

        except Exception as e:
            self._log_error('CloudTrail', e)
            return CheckResult.error(
                'CloudTrail Check Failed',
                f'Failed to check CloudTrail: {str(e)}'
            )

    def _get_recent_events(self) -> List[Dict[str, Any]]:
        """Get CloudTrail events from last N hours."""
        if not self.cloudtrail:
            return []

        start_time = datetime.now(timezone.utc) - timedelta(hours=self.hours_lookback)
        all_events = []

        try:
            paginator = self.cloudtrail.get_paginator('lookup_events')
            page_iterator = paginator.paginate(
                LookupAttributes=[
                    {
                        'AttributeKey': 'EventSource',
                        'AttributeValue': 'iam.amazonaws.com'
                    }
                ],
                StartTime=start_time,
                MaxResults=50
            )

            for page in page_iterator:
                for event in page.get('Events', []):
                    all_events.append({
                        'EventName': event.get('EventName'),
                        'Username': event.get('Username'),
                        'EventTime': event.get('EventTime'),
                        'SourceIPAddress': event.get('SourceIPAddress'),
                        'CloudTrailEvent': event.get('CloudTrailEvent')
                    })

        except Exception as e:
            logger.warning(f"Error fetching CloudTrail events: {str(e)}")

        return all_events

    def _analyze_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze events for suspicious activity."""
        anomalies = []

        for event in events:
            severity = self._analyze_event(event)
            if severity:
                event_time = event.get('EventTime')
                # Handle both datetime objects and strings
                if event_time and hasattr(event_time, 'isoformat'):
                    timestamp = event_time.isoformat()
                else:
                    timestamp = event_time

                anomalies.append({
                    'event_name': event.get('EventName'),
                    'username': event.get('Username'),
                    'source_ip': event.get('SourceIPAddress'),
                    'timestamp': timestamp,
                    'severity': severity
                })

        return anomalies

    def _analyze_event(self, event: Dict[str, Any]) -> Optional[str]:
        """Determine severity of a single event."""
        username = event.get('Username', '')
        event_name = event.get('EventName', '')

        # Root account activity
        if username == 'root' or username.endswith(':root'):
            return 'CRITICAL'

        # Suspicious API events
        if event_name in self.SUSPICIOUS_EVENTS:
            return 'HIGH'

        return None

    def _determine_severity(self, anomalies: List[Dict[str, Any]]) -> str:
        """Determine overall severity based on anomalies."""
        if any(a['severity'] == 'CRITICAL' for a in anomalies):
            return 'CRITICAL'
        elif any(a['severity'] == 'HIGH' for a in anomalies):
            return 'HIGH'
        elif len(anomalies) >= 3:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _get_remediation_suggestion(self, anomalies: List[Dict[str, Any]]) -> str:
        """Generate remediation suggestion based on anomalies."""
        if not anomalies:
            return 'Review CloudTrail logs for suspicious activity'

        event_names = {a.get('event_name') for a in anomalies}

        if 'CreateAccessKey' in event_names or 'CreateUser' in event_names:
            return 'Review and rotate access keys. Enable MFA for affected users.'
        elif 'AttachUserPolicy' in event_names or 'PutUserPolicy' in event_names:
            return 'Review IAM permission changes. Check for unauthorized policy modifications.'
        elif 'TerminateInstances' in event_names or 'StopInstances' in event_names:
            return 'Verify EC2 instance changes. Review if changes were authorized.'
        elif 'DeleteBucket' in event_names or 'DeleteTable' in event_names:
            return 'Alert: Critical resource deletion detected. Review deletion logs immediately.'
        else:
            return 'Review CloudTrail findings and take appropriate action'
