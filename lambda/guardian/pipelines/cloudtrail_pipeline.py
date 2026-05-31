"""CloudTrail event processing pipeline."""

from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from guardian.integrations.cloudtrail_analyzer import (
    CloudTrailEventParser,
    AnomalousActivityDetector,
    PermissionChangeTracker,
    ResourceDeleteMonitor
)


class CloudTrailPipeline:
    """End-to-end CloudTrail event processing pipeline."""

    ANOMALY_THRESHOLD = 70  # Score above this triggers alerts
    CRITICAL_THRESHOLD = 80  # Score above this is critical

    def __init__(self):
        self.parser = CloudTrailEventParser()
        self.detector = AnomalousActivityDetector()
        self.tracker = PermissionChangeTracker()
        self.monitor = ResourceDeleteMonitor()
        self.event_history = defaultdict(list)
        self.authorized_regions = ['us-east-1', 'us-west-2', 'eu-west-1']

    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process CloudTrail event through full pipeline."""
        # Parse event
        normalized = self.parser.parse(event)

        # Store in history for pattern detection. Retention is keyed off the
        # ingestion time (when we observed the event), not the event's own
        # eventTime — otherwise a burst of events whose eventTime is older than
        # the window (replayed, delayed, or back-dated by an attacker) would be
        # purged before frequency analysis could flag it.
        now = datetime.now(timezone.utc)
        event_key = f"{normalized['principal']}:{normalized['event_name']}"
        normalized['_ingested_at'] = now
        self.event_history[event_key].append(normalized)

        # Keep only recently-ingested history (1 hour)
        cutoff_time = now - timedelta(hours=1)
        self.event_history[event_key] = [
            e for e in self.event_history[event_key]
            if e.get('_ingested_at', now) > cutoff_time
        ]

        # Calculate anomaly score
        anomaly_score = self._calculate_anomaly_score(normalized, event)

        # Generate alerts
        alerts = self._generate_alerts(normalized, anomaly_score, event)

        # Track permission changes
        permission_change = None
        if any(keyword in normalized['event_type'] for keyword in ['IAM', 'ASSUME']):
            permission_change = self.tracker.track_change(event)

        # Check for deletions
        deletion = None
        if 'DELETION' in normalized['event_type'] or 'DELETE' in event.get('eventName', ''):
            deletion = self.monitor.detect_deletion(event)

        return {
            'processed': True,
            'event_type': normalized['event_type'],
            'anomaly_score': anomaly_score,
            'alerts': alerts,
            'severity': self._get_severity(anomaly_score),
            'permission_change': permission_change,
            'deletion': deletion,
            'timestamp': normalized['timestamp'],
            'normalized_event': normalized
        }

    def _calculate_anomaly_score(self, normalized: Dict[str, Any], raw_event: Dict[str, Any]) -> float:
        """Calculate composite anomaly score (0-100)."""
        scores = []

        # Score 1: Frequency analysis
        event_key = f"{normalized['principal']}:{normalized['event_name']}"
        recent_events = self.event_history[event_key]
        if len(recent_events) > 1:
            freq_result = self.detector.detect_frequency_anomaly(recent_events)
            scores.append(freq_result['anomaly_score'])

        # Score 2: Region anomaly
        if normalized['aws_region']:
            region_result = self.detector.detect_region_anomaly(
                raw_event,
                self.authorized_regions
            )
            scores.append(region_result['anomaly_score'])

        # Score 3: Event type risk
        if 'DELETION' in normalized['event_type']:
            scores.append(80)
        elif 'IAM_POLICY' in normalized['event_type']:
            scores.append(60)
        elif normalized['error_code']:
            scores.append(45)

        # Score 4: Escalation patterns
        if len(recent_events) >= 2:
            escalation_result = self.detector.detect_escalation_pattern(recent_events)
            if escalation_result['is_anomalous']:
                scores.append(85)

        # Return average score
        return sum(scores) / len(scores) if scores else 0

    def _generate_alerts(self, normalized: Dict[str, Any], anomaly_score: float, event: Dict[str, Any]) -> List[str]:
        """Generate alerts based on anomaly score and event type."""
        alerts = []

        if anomaly_score >= self.CRITICAL_THRESHOLD:
            alerts.append(f"CRITICAL: Anomalous activity detected (score: {anomaly_score:.0f})")

        if 'DELETION' in normalized['event_type']:
            resource = normalized.get('resource') or normalized.get('instance_id')
            alerts.append(f"Resource deletion detected: {resource}")

        if 'IAM_POLICY' in normalized['event_type']:
            change = self.tracker.track_change(event)
            if change.get('policy'):
                alerts.append(f"IAM policy modified: {change['policy']} on {change.get('principal')}")

        if normalized['error_code']:
            alerts.append(f"API call failed: {normalized['error_code']}")

        if 'ASSUME_ROLE' in normalized['event_type']:
            alerts.append(f"Role assumption detected: {normalized.get('resource')}")

        if anomaly_score >= self.ANOMALY_THRESHOLD and not alerts:
            alerts.append(f"Anomalous activity detected (score: {anomaly_score:.0f})")

        return alerts

    def _get_severity(self, anomaly_score: float) -> str:
        """Map anomaly score to severity level."""
        if anomaly_score >= 90:
            return 'CRITICAL'
        elif anomaly_score >= 80:
            return 'HIGH'
        elif anomaly_score >= 70:
            return 'MEDIUM'
        elif anomaly_score >= 50:
            return 'LOW'
        else:
            return 'INFO'


class EventNormalizer:
    """Normalize various CloudTrail event formats."""

    def __init__(self):
        self.parser = CloudTrailEventParser()

    def normalize_batch(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize batch of events."""
        return [self.parser.parse(event) for event in events]

    def normalize_from_eventbridge(self, eventbridge_event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize EventBridge-wrapped CloudTrail event."""
        # EventBridge typically wraps the actual event in 'detail'
        cloudtrail_event = eventbridge_event.get('detail', eventbridge_event)
        return self.parser.parse(cloudtrail_event)

    def deduplicate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate events (same event_name, resource, within 1 second)."""
        seen = {}
        deduplicated = []

        for event in events:
            key = (
                event.get('eventName'),
                event.get('requestParameters', {}).get('bucketName') or
                event.get('requestParameters', {}).get('userName') or
                event.get('responseElements', {}).get('instanceId'),
                event.get('eventTime')
            )

            if key not in seen:
                seen[key] = True
                deduplicated.append(event)

        return deduplicated
