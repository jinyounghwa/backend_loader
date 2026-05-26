"""Dashboard Stream Manager for coordinating event streaming."""

from typing import Dict, List
from datetime import datetime


class DashboardStreamManager:
    """Manages event streaming to dashboard clients."""

    def __init__(self, broadcaster=None, dashboard_service=None):
        """Initialize stream manager."""
        self.broadcaster = broadcaster
        self.dashboard = dashboard_service
        self.event_history = []

    def handle_threat_detection(self, threat: Dict) -> Dict:
        """Handle threat detection event and broadcast."""
        event = {
            'event_id': str(id(threat)),
            'event_type': 'threat_detected',
            'timestamp': datetime.utcnow().isoformat(),
            'threat': threat
        }

        self.event_history.append(event)

        if self.broadcaster:
            self.broadcaster.broadcast_threat_detected(threat)

        return event

    def handle_remediation_update(self, execution_id: str, update: Dict) -> Dict:
        """Handle remediation progress update and broadcast."""
        event = {
            'event_id': str(id(update)),
            'event_type': 'remediation_update',
            'timestamp': datetime.utcnow().isoformat(),
            'execution_id': execution_id,
            'update': update
        }

        self.event_history.append(event)

        if self.broadcaster:
            self.broadcaster.broadcast_remediation_progress(
                execution_id,
                update.get('progress_percent', 0),
                update.get('resources_status', {})
            )

        return event

    def handle_resource_update(self, resource_id: str, status: str, action: str) -> Dict:
        """Handle individual resource update and broadcast."""
        event = {
            'event_id': str(id(resource_id)),
            'event_type': 'resource_update',
            'timestamp': datetime.utcnow().isoformat(),
            'resource_id': resource_id,
            'status': status,
            'action': action
        }

        self.event_history.append(event)

        return event

    def handle_playbook_event(self, event: Dict) -> Dict:
        """Handle playbook execution event and broadcast."""
        stream_event = {
            'event_id': str(id(event)),
            'event_type': 'playbook_execution',
            'timestamp': datetime.utcnow().isoformat(),
            'playbook_event': event
        }

        self.event_history.append(stream_event)

        if self.broadcaster:
            self.broadcaster.broadcast_playbook_execution(
                event.get('execution_id', ''),
                event.get('playbook_name', ''),
                event.get('status', '')
            )

        return stream_event

    def handle_compliance_update(self, framework: str, metrics: Dict) -> Dict:
        """Handle compliance metric update and broadcast."""
        event = {
            'event_id': str(id(metrics)),
            'event_type': 'compliance_update',
            'timestamp': datetime.utcnow().isoformat(),
            'framework': framework,
            'metrics': metrics
        }

        self.event_history.append(event)

        if self.broadcaster:
            self.broadcaster.broadcast_compliance_status_change(
                framework,
                metrics.get('status', 'COMPLIANT')
            )

        return event

    def handle_audit_event(self, event: Dict) -> Dict:
        """Handle audit trail event and broadcast."""
        stream_event = {
            'event_id': str(id(event)),
            'event_type': 'audit_event',
            'timestamp': datetime.utcnow().isoformat(),
            'audit_event': event
        }

        self.event_history.append(stream_event)

        return stream_event

    def batch_updates(self, events: List[Dict], batch_size: int = 10,
                     batch_timeout_ms: int = 100) -> List[Dict]:
        """Batch multiple events into single message."""
        batches = []
        current_batch = []

        for event in events:
            current_batch.append(event)

            if len(current_batch) >= batch_size:
                batches.append({
                    'batch_id': str(id(current_batch)),
                    'timestamp': datetime.utcnow().isoformat(),
                    'events': current_batch,
                    'event_count': len(current_batch)
                })
                current_batch = []

        # Add remaining events
        if current_batch:
            batches.append({
                'batch_id': str(id(current_batch)),
                'timestamp': datetime.utcnow().isoformat(),
                'events': current_batch,
                'event_count': len(current_batch)
            })

        return batches

    def get_event_history(self, limit: int = 100) -> List[Dict]:
        """Get recent event history."""
        return self.event_history[-limit:]

    def get_stream_stats(self) -> Dict:
        """Get stream statistics."""
        return {
            'total_events': len(self.event_history),
            'threat_events': sum(1 for e in self.event_history if e['event_type'] == 'threat_detected'),
            'remediation_events': sum(1 for e in self.event_history if e['event_type'] == 'remediation_update'),
            'playbook_events': sum(1 for e in self.event_history if e['event_type'] == 'playbook_execution')
        }

    def clear_history(self) -> int:
        """Clear event history."""
        count = len(self.event_history)
        self.event_history.clear()
        return count
