"""Audit Trail Service for comprehensive compliance and forensic audit logging."""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid


class AuditTrailService:
    """Manages comprehensive audit trail for all security operations."""

    def __init__(self, audit_logger=None):
        """Initialize audit trail service."""
        self.audit = audit_logger
        self.events = []

    def log_threat_detection(self, threat: Dict, detector_id: str, evidence: List[str]) -> str:
        """Log threat detection event with detector info and evidence."""
        event_id = str(uuid.uuid4())
        event = {
            'event_id': event_id,
            'event_type': 'THREAT_DETECTION',
            'timestamp': datetime.utcnow().isoformat(),
            'threat_id': threat.get('threat_id'),
            'threat_type': threat.get('threat_type'),
            'severity': threat.get('severity'),
            'account_id': threat.get('account_id'),
            'detector_id': detector_id,
            'evidence': evidence,
            'status': 'LOGGED'
        }
        self.events.append(event)
        return event_id

    def log_remediation_action(self, threat_id: str, action: str, status: str, resources: List[str]) -> str:
        """Log remediation execution with action details and affected resources."""
        event_id = str(uuid.uuid4())
        event = {
            'event_id': event_id,
            'event_type': 'REMEDIATION_ACTION',
            'timestamp': datetime.utcnow().isoformat(),
            'threat_id': threat_id,
            'action': action,
            'status': status,
            'resources_affected': resources,
            'resource_count': len(resources)
        }
        self.events.append(event)
        return event_id

    def log_policy_enforcement(self, account_id: str, policy_name: str, decision: str) -> str:
        """Log policy enforcement decision."""
        event_id = str(uuid.uuid4())
        event = {
            'event_id': event_id,
            'event_type': 'POLICY_ENFORCEMENT',
            'timestamp': datetime.utcnow().isoformat(),
            'account_id': account_id,
            'policy_name': policy_name,
            'decision': decision
        }
        self.events.append(event)
        return event_id

    def log_user_action(self, user_id: str, action: str, target: str, details: Dict) -> str:
        """Log manual user actions (approvals, deployments, etc)."""
        event_id = str(uuid.uuid4())
        event = {
            'event_id': event_id,
            'event_type': 'USER_ACTION',
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'target': target,
            'details': details
        }
        self.events.append(event)
        return event_id

    def get_audit_trail(self, start_time: str, end_time: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Retrieve audit trail events with optional filtering."""
        if isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            start_dt = start_time

        if isinstance(end_time, str):
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end_dt = end_time

        filtered_events = []
        for event in self.events:
            event_dt = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            if start_dt <= event_dt <= end_dt:
                if filters is None or self._matches_filters(event, filters):
                    filtered_events.append(event)

        return sorted(filtered_events, key=lambda e: e['timestamp'], reverse=True)

    def get_threat_audit_chain(self, threat_id: str) -> List[Dict]:
        """Get complete audit chain for a threat from detection to resolution."""
        threat_events = [e for e in self.events if e.get('threat_id') == threat_id]
        return sorted(threat_events, key=lambda e: e['timestamp'])

    def get_user_action_history(self, user_id: str) -> List[Dict]:
        """Get all actions by specific user."""
        user_events = [e for e in self.events if e.get('user_id') == user_id]
        return sorted(user_events, key=lambda e: e['timestamp'], reverse=True)

    def export_audit_log(self, start_time: str, end_time: str, format_type: str = 'json') -> Dict:
        """Export audit log in standardized format."""
        events = self.get_audit_trail(start_time, end_time)

        if format_type == 'json':
            return {
                'format': 'json',
                'export_timestamp': datetime.utcnow().isoformat(),
                'event_count': len(events),
                'start_time': start_time,
                'end_time': end_time,
                'events': events
            }
        elif format_type == 'csv':
            return {
                'format': 'csv',
                'export_timestamp': datetime.utcnow().isoformat(),
                'event_count': len(events),
                'headers': ['timestamp', 'event_type', 'threat_id', 'action', 'status', 'user_id'],
                'events': events
            }
        else:
            return {'error': f'Unsupported format: {format_type}'}

    def get_threat_timeline(self, threat_id: str) -> Dict:
        """Get chronological timeline of threat lifecycle."""
        threat_events = self.get_threat_audit_chain(threat_id)

        timeline = {
            'threat_id': threat_id,
            'detection_time': threat_events[0]['timestamp'] if threat_events else None,
            'total_events': len(threat_events),
            'event_types': list(set(e['event_type'] for e in threat_events)),
            'events': threat_events
        }
        return timeline

    def get_event_count_by_type(self, start_time: str, end_time: str) -> Dict:
        """Get event count by type for a period."""
        events = self.get_audit_trail(start_time, end_time)
        counts = {}
        for event in events:
            event_type = event.get('event_type')
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts

    def _matches_filters(self, event: Dict, filters: Dict) -> bool:
        """Check if event matches all filter criteria."""
        for key, value in filters.items():
            if event.get(key) != value:
                return False
        return True
