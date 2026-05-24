"""Splunk Phantom SOAR integration"""

import logging
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime, timezone
from .soar_connector import SOARConnector

logger = logging.getLogger(__name__)


class SplunkPhantomConnector(SOARConnector):
    """Splunk Phantom SOAR platform integration"""

    def __init__(self, base_url: str, api_key: str):
        """Initialize Splunk Phantom connector"""
        super().__init__('splunk_phantom', base_url, api_key)

    def send_incident_to_soar(self, incident: Dict) -> Optional[str]:
        """Send incident to Splunk Phantom as container"""
        try:
            phantom_incident = self._format_incident_for_soar(incident)
            phantom_incident['container_type'] = 'security_incident'

            payload = {
                'name': phantom_incident['title'],
                'description': phantom_incident['description'],
                'severity': phantom_incident['severity'],
                'label': 'aws_guardian',
                'data': json.dumps(phantom_incident['metadata'])
            }

            response = requests.post(
                f'{self.base_url}/rest/container',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                container_id = response.json().get('id')
                logger.info(f"Created Phantom container {container_id}")
                return str(container_id)
            else:
                logger.error(f"Failed to create Phantom container: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error sending incident to Phantom: {str(e)}")
            return None

    def run_phantom_playbook(self, container_id: str, playbook_name: str) -> Optional[str]:
        """Run a Phantom playbook on a container"""
        try:
            payload = {
                'container_id': container_id,
                'playbook_name': playbook_name
            }

            response = requests.post(
                f'{self.base_url}/rest/playbook_run',
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 201]:
                playbook_run_id = response.json().get('id')
                logger.info(f"Started Phantom playbook {playbook_name} run {playbook_run_id}")
                return str(playbook_run_id)
            else:
                logger.error(f"Failed to run playbook: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error running Phantom playbook: {str(e)}")
            return None

    def track_playbook_status(self, playbook_run_id: str) -> Optional[Dict]:
        """Track Phantom playbook execution status"""
        try:
            response = requests.get(
                f'{self.base_url}/rest/playbook_run/{playbook_run_id}',
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                run_data = response.json()
                status_info = {
                    'run_id': playbook_run_id,
                    'status': run_data.get('status'),
                    'result': run_data.get('result'),
                    'message': run_data.get('message', ''),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                logger.info(f"Phantom playbook {playbook_run_id} status: {status_info['status']}")
                return status_info
            else:
                logger.error(f"Failed to get playbook status: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error tracking playbook: {str(e)}")
            return None

    def receive_playbook_result(self, playbook_id: str) -> Optional[Dict]:
        """Get results from executed playbook"""
        return self.track_playbook_status(playbook_id)

    def sync_status_with_soar(self, incident_id: str, status: str) -> bool:
        """Sync incident status with Phantom"""
        try:
            payload = {'status': status}

            response = requests.post(
                f'{self.base_url}/rest/container/{incident_id}',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                logger.info(f"Synced Phantom container {incident_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to sync status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error syncing status: {str(e)}")
            return False

    def get_available_playbooks(self) -> List[Dict]:
        """Get list of available playbooks"""
        try:
            response = requests.get(
                f'{self.base_url}/rest/playbook',
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                playbooks = response.json().get('data', [])
                logger.info(f"Retrieved {len(playbooks)} available playbooks")
                return playbooks
            else:
                logger.error(f"Failed to get playbooks: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error getting playbooks: {str(e)}")
            return []

    def get_phantom_case_summary(self, container_id: str) -> Optional[Dict]:
        """Get summary of Phantom case/container"""
        try:
            response = requests.get(
                f'{self.base_url}/rest/container/{container_id}',
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                container = response.json()
                summary = {
                    'container_id': container_id,
                    'name': container.get('name'),
                    'status': container.get('status'),
                    'severity': container.get('severity'),
                    'artifact_count': container.get('artifact_count', 0)
                }
                logger.info(f"Retrieved Phantom case {container_id} summary")
                return summary
            else:
                logger.error(f"Failed to get case summary: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting case summary: {str(e)}")
            return None
