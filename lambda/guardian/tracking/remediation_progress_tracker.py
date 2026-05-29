from typing import Dict, List
from datetime import datetime, timezone
import uuid


class RemediationProgressTracker:
    def __init__(self, dynamodb_table=None, audit_logger=None):
        self.table = dynamodb_table
        self.audit = audit_logger
        self.active_remediations = {}
        self.completed_remediations = []

    def track_remediation_start(self, threat_id: str, execution_id: str, strategy: str) -> None:
        remediation_record = {
            'execution_id': execution_id,
            'threat_id': threat_id,
            'strategy': strategy,
            'started_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'status': 'in_progress',
            'resources_processed': 0,
            'resources_successful': 0,
            'resources_failed': 0,
            'resource_updates': [],
        }

        self.active_remediations[execution_id] = remediation_record

    def track_resource_remediation(self, execution_id: str, resource_id: str, status: str, result: Dict) -> None:
        if execution_id not in self.active_remediations:
            return

        remediation = self.active_remediations[execution_id]
        remediation['resources_processed'] += 1

        if status == 'success':
            remediation['resources_successful'] += 1
        elif status == 'failed':
            remediation['resources_failed'] += 1

        remediation['resource_updates'].append({
            'resource_id': resource_id,
            'status': status,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'result': result,
        })

    def track_remediation_complete(self, execution_id: str, outcome: Dict) -> None:
        if execution_id not in self.active_remediations:
            return

        remediation = self.active_remediations[execution_id]
        remediation['completed_at'] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        remediation['status'] = outcome.get('status', 'completed')
        remediation['final_outcome'] = outcome

        self.completed_remediations.append(remediation)
        del self.active_remediations[execution_id]

    def get_remediation_progress(self, execution_id: str) -> Dict:
        if execution_id in self.active_remediations:
            remediation = self.active_remediations[execution_id]
            total_resources = remediation['resources_processed']
            successful = remediation['resources_successful']
            failed = remediation['resources_failed']

            progress_percent = 0
            if total_resources > 0:
                progress_percent = (successful + failed) / total_resources * 100

            return {
                'execution_id': execution_id,
                'threat_id': remediation['threat_id'],
                'strategy': remediation['strategy'],
                'status': remediation['status'],
                'started_at': remediation['started_at'],
                'progress_percent': progress_percent,
                'resources_processed': total_resources,
                'resources_successful': successful,
                'resources_failed': failed,
                'last_update': remediation['resource_updates'][-1]['timestamp'] if remediation['resource_updates'] else None,
            }

        for remediation in self.completed_remediations:
            if remediation['execution_id'] == execution_id:
                return {
                    'execution_id': execution_id,
                    'threat_id': remediation['threat_id'],
                    'strategy': remediation['strategy'],
                    'status': remediation['status'],
                    'started_at': remediation['started_at'],
                    'completed_at': remediation['completed_at'],
                    'progress_percent': 100.0,
                    'resources_processed': remediation['resources_processed'],
                    'resources_successful': remediation['resources_successful'],
                    'resources_failed': remediation['resources_failed'],
                }

        return {
            'execution_id': execution_id,
            'status': 'not_found',
        }

    def get_threat_timeline(self, threat_id: str) -> List[Dict]:
        timeline = []

        for execution_id, remediation in self.active_remediations.items():
            if remediation['threat_id'] == threat_id:
                timeline.append({
                    'execution_id': execution_id,
                    'timestamp': remediation['started_at'],
                    'event_type': 'remediation_started',
                    'strategy': remediation['strategy'],
                    'status': remediation['status'],
                })

        for remediation in self.completed_remediations:
            if remediation['threat_id'] == threat_id:
                timeline.append({
                    'execution_id': remediation['execution_id'],
                    'timestamp': remediation['started_at'],
                    'event_type': 'remediation_started',
                    'strategy': remediation['strategy'],
                })

                timeline.append({
                    'execution_id': remediation['execution_id'],
                    'timestamp': remediation['completed_at'],
                    'event_type': 'remediation_completed',
                    'status': remediation['status'],
                    'resources_successful': remediation['resources_successful'],
                    'resources_failed': remediation['resources_failed'],
                })

        timeline.sort(key=lambda x: x['timestamp'])
        return timeline

    def get_progress_summary(self) -> Dict:
        total_active = len(self.active_remediations)
        total_completed = len(self.completed_remediations)

        total_resources_processed = sum(r['resources_processed'] for r in self.completed_remediations)
        total_resources_successful = sum(r['resources_successful'] for r in self.completed_remediations)
        total_resources_failed = sum(r['resources_failed'] for r in self.completed_remediations)

        success_rate = 0.0
        if total_resources_processed > 0:
            success_rate = total_resources_successful / total_resources_processed

        return {
            'active_remediations': total_active,
            'completed_remediations': total_completed,
            'total_resources_processed': total_resources_processed,
            'total_resources_successful': total_resources_successful,
            'total_resources_failed': total_resources_failed,
            'overall_success_rate': success_rate,
        }
