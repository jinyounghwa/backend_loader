"""Real-Time Event Processor - CloudTrail, SNS, and WebSocket threat response."""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import heapq
import hashlib


class EventPriority(Enum):
    """Request priority levels (lower number = higher priority)."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class RealTimeEventProcessor:
    """Process real-time threat events with priority queue and deduplication."""

    def __init__(self, orchestrator, audit_logger):
        """Initialize real-time event processor."""
        self.orchestrator = orchestrator
        self.audit = audit_logger
        self.priority_queue = []
        self.processed_events = set()  # For deduplication
        self.throttle_window = {}  # Track recent events by source

    def process_cloudtrail_event(self, event: Dict) -> Dict:
        """
        Process CloudTrail event and trigger immediate remediation if needed.

        Args:
            event: CloudTrail event from EventBridge

        Returns:
            {
                'status': 'queued|skipped|processing',
                'event_id': str,
                'threat_id': str,
                'priority': int,
                'reason': str
            }
        """
        result = {
            'event_id': event.get('detail-id', 'unknown'),
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            # Extract threat indicators from CloudTrail event
            threat = self._extract_threat_from_cloudtrail(event)
            if not threat:
                result['status'] = 'skipped'
                result['reason'] = 'No threat indicators detected'
                return result

            # Check for deduplication
            event_hash = self._hash_event(event)
            if event_hash in self.processed_events:
                result['status'] = 'skipped'
                result['reason'] = 'Duplicate event'
                return result

            # Determine priority based on severity
            priority = self._determine_priority(threat)

            # Add to priority queue
            queue_entry = (priority, datetime.utcnow().timestamp(), threat)
            heapq.heappush(self.priority_queue, queue_entry)

            # Track processed event
            self.processed_events.add(event_hash)

            result['status'] = 'queued'
            result['threat_id'] = threat.get('threat_id')
            result['priority'] = priority

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def process_sns_notification(self, notification: Dict) -> Dict:
        """
        Process SNS notification (e.g., S3:PublicBucketCreated).

        Args:
            notification: SNS notification message

        Returns:
            {
                'status': 'queued|skipped',
                'notification_id': str,
                'threat_id': str
            }
        """
        result = {
            'notification_id': notification.get('MessageId', 'unknown'),
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            # Parse SNS message
            message = notification.get('Message', {})
            if isinstance(message, str):
                import json
                message = json.loads(message)

            # Extract threat from SNS message
            threat = self._extract_threat_from_sns(message)
            if not threat:
                result['status'] = 'skipped'
                return result

            # Add to priority queue
            priority = self._determine_priority(threat)
            queue_entry = (priority, datetime.utcnow().timestamp(), threat)
            heapq.heappush(self.priority_queue, queue_entry)

            result['status'] = 'queued'
            result['threat_id'] = threat.get('threat_id')

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def process_webhook_trigger(self, webhook_payload: Dict) -> Dict:
        """
        Process webhook trigger for immediate threat detection.

        Args:
            webhook_payload: Webhook POST body

        Returns:
            {
                'status': 'queued|invalid',
                'threat_id': str,
                'estimated_remediation_time_seconds': int
            }
        """
        result = {
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            threat = webhook_payload.get('threat', {})
            if not threat.get('threat_id'):
                result['status'] = 'invalid'
                result['error'] = 'Missing threat_id'
                return result

            # Validate webhook signature (would be verified by caller)
            priority = self._determine_priority(threat)
            queue_entry = (priority, datetime.utcnow().timestamp(), threat)
            heapq.heappush(self.priority_queue, queue_entry)

            result['status'] = 'queued'
            result['threat_id'] = threat.get('threat_id')
            result['estimated_remediation_time_seconds'] = 60

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def dequeue_and_remediate(self) -> Dict:
        """
        Dequeue highest-priority threat and execute remediation.

        Returns:
            {
                'status': 'remediated|empty',
                'threat_id': str,
                'orchestration_id': str,
                'remediation_time_seconds': float
            }
        """
        result = {
            'timestamp': datetime.utcnow().isoformat()
        }

        if not self.priority_queue:
            result['status'] = 'empty'
            return result

        try:
            # Pop highest priority threat
            priority, timestamp, threat = heapq.heappop(self.priority_queue)

            # Execute remediation
            start_time = datetime.utcnow()
            remediation_result = self.orchestrator.execute_multi_resource_remediation(threat)
            end_time = datetime.utcnow()

            result['status'] = 'remediated'
            result['threat_id'] = threat.get('threat_id')
            result['orchestration_id'] = remediation_result.get('orchestration_id')
            result['remediation_time_seconds'] = (end_time - start_time).total_seconds()
            result['priority'] = priority

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def check_throttle(self, threat_source: str) -> bool:
        """Check if threat source is being throttled (too many events)."""
        current_time = datetime.utcnow().timestamp()
        window_start = current_time - 300  # 5-minute window

        # Clean old entries
        if threat_source in self.throttle_window:
            self.throttle_window[threat_source] = [
                ts for ts in self.throttle_window[threat_source]
                if ts > window_start
            ]

            # Throttle if more than 10 events per 5 minutes
            if len(self.throttle_window[threat_source]) > 10:
                return True

            self.throttle_window[threat_source].append(current_time)
        else:
            self.throttle_window[threat_source] = [current_time]

        return False

    def _extract_threat_from_cloudtrail(self, event: Dict) -> Optional[Dict]:
        """Extract threat indicators from CloudTrail event."""
        detail = event.get('detail', {})
        event_name = detail.get('eventName', '')

        threat = {
            'threat_id': f'THREAT-CT-{event.get("detail-id", "")[:16]}',
            'source': 'cloudtrail',
            'event_type': event_name,
            'severity': 5  # Base severity
        }

        # Detect suspicious CloudTrail events
        suspicious_events = [
            'CreateAccessKey',
            'AttachUserPolicy',
            'PutUserPolicy',
            'AuthorizeSecurityGroupIngress',
            'PutBucketPolicy'
        ]

        if event_name in suspicious_events:
            threat['severity'] = 7
            return threat

        return None

    def _extract_threat_from_sns(self, message: Dict) -> Optional[Dict]:
        """Extract threat indicators from SNS notification."""
        event_type = message.get('detail-type', '')

        threat = {
            'threat_id': f'THREAT-SNS-{datetime.utcnow().timestamp():.0f}',
            'source': 'sns',
            'event_type': event_type,
            'severity': 5
        }

        # Detect S3 public bucket creation
        if 'PublicBucket' in event_type:
            threat['severity'] = 8
            threat['bucket_name'] = message.get('bucket', {}).get('name')
            return threat

        return None

    def _determine_priority(self, threat: Dict) -> int:
        """Determine event priority based on threat severity."""
        severity = threat.get('severity', 5)

        if severity >= 9:
            return EventPriority.CRITICAL.value
        elif severity >= 7:
            return EventPriority.HIGH.value
        elif severity >= 5:
            return EventPriority.MEDIUM.value
        else:
            return EventPriority.LOW.value

    def _hash_event(self, event: Dict) -> str:
        """Generate hash for event deduplication."""
        event_id = event.get('detail-id', '')
        source = event.get('source', '')
        detail_type = event.get('detail-type', '')

        unique_str = f"{source}:{detail_type}:{event_id}"
        return hashlib.sha256(unique_str.encode()).hexdigest()

    def get_queue_status(self) -> Dict:
        """Get current priority queue status."""
        return {
            'queue_size': len(self.priority_queue),
            'processed_events': len(self.processed_events),
            'throttled_sources': len(self.throttle_window),
            'timestamp': datetime.utcnow().isoformat()
        }
