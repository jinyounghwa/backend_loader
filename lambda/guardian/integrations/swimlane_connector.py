"""Swimlane SOAR integration"""

import logging
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime, timezone
from .soar_connector import SOARConnector

logger = logging.getLogger(__name__)


class SwimlaneConnector(SOARConnector):
    """Swimlane SOAR platform integration"""

    def __init__(self, base_url: str, api_key: str, app_id: str = None):
        """Initialize Swimlane connector"""
        super().__init__('swimlane', base_url, api_key)
        self.app_id = app_id

    def send_incident_to_soar(self, incident: Dict) -> Optional[str]:
        """Send incident to Swimlane as record"""
        try:
            swimlane_record = self._format_for_swimlane(incident)

            payload = {
                'applicationId': self.app_id or 'default',
                'fields': swimlane_record
            }

            response = requests.post(
                f'{self.base_url}/api/records',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                record_id = response.json().get('id')
                logger.info(f"Created Swimlane record {record_id}")
                return str(record_id)
            else:
                logger.error(f"Failed to create Swimlane record: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error sending to Swimlane: {str(e)}")
            return None

    def trigger_swimlane_workflow(self, record_id: str, workflow_name: str) -> bool:
        """Trigger a Swimlane workflow for a record"""
        try:
            payload = {
                'recordId': record_id,
                'workflowName': workflow_name
            }

            response = requests.post(
                f'{self.base_url}/api/workflows/execute',
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 201]:
                logger.info(f"Triggered Swimlane workflow {workflow_name} for record {record_id}")
                return True
            else:
                logger.error(f"Failed to trigger workflow: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error triggering workflow: {str(e)}")
            return False

    def update_record_status(self, record_id: str, status: str) -> bool:
        """Update Swimlane record status"""
        try:
            payload = {'status': status}

            response = requests.patch(
                f'{self.base_url}/api/records/{record_id}',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                logger.info(f"Updated Swimlane record {record_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to update status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error updating record: {str(e)}")
            return False

    def attach_evidence_to_record(self, record_id: str, evidence: Dict) -> bool:
        """Attach evidence to Swimlane record"""
        try:
            payload = {
                'evidence': json.dumps(evidence, default=str)
            }

            response = requests.patch(
                f'{self.base_url}/api/records/{record_id}/evidence',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                logger.info(f"Attached evidence to Swimlane record {record_id}")
                return True
            else:
                logger.error(f"Failed to attach evidence: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error attaching evidence: {str(e)}")
            return False

    def receive_playbook_result(self, playbook_id: str) -> Optional[Dict]:
        """Get playbook execution result from Swimlane"""
        try:
            response = requests.get(
                f'{self.base_url}/api/workflows/{playbook_id}/result',
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Retrieved Swimlane workflow result {playbook_id}")
                return result
            else:
                logger.error(f"Failed to get result: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting result: {str(e)}")
            return None

    def sync_status_with_soar(self, incident_id: str, status: str) -> bool:
        """Sync status with Swimlane"""
        return self.update_record_status(incident_id, status)

    def get_available_playbooks(self) -> List[Dict]:
        """Get available workflows in Swimlane"""
        try:
            response = requests.get(
                f'{self.base_url}/api/workflows',
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                workflows = response.json().get('data', [])
                logger.info(f"Retrieved {len(workflows)} Swimlane workflows")
                return workflows
            else:
                logger.error(f"Failed to get workflows: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error getting workflows: {str(e)}")
            return []

    def _format_for_swimlane(self, incident: Dict) -> Dict:
        """Format incident for Swimlane"""
        base_format = self._format_incident_for_soar(incident)
        return {
            'title': base_format['title'],
            'description': base_format['description'],
            'severity': base_format['severity'],
            'threat_id': base_format['metadata'].get('threat_id'),
            'account_id': base_format['metadata'].get('account_id')
        }
