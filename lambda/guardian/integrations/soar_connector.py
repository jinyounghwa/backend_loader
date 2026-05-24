"""Base SOAR platform connector for orchestration platform integration"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SOARConnector:
    """Base connector for SOAR (Security Orchestration, Automation and Response) platforms"""

    def __init__(self, platform: str, base_url: str, api_key: str):
        """
        Args:
            platform: SOAR platform name (phantom, swimlane, etc)
            base_url: SOAR platform API base URL
            api_key: API authentication key
        """
        self.platform = platform
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    def send_incident_to_soar(self, incident: Dict) -> Optional[str]:
        """
        Send incident/case to SOAR platform

        Args:
            incident: Incident data with threat information

        Returns:
            Incident/case ID on SOAR platform or None
        """
        raise NotImplementedError("Subclass must implement send_incident_to_soar")

    def receive_playbook_result(self, playbook_id: str) -> Optional[Dict]:
        """
        Retrieve results from executed playbook

        Args:
            playbook_id: ID of executed playbook

        Returns:
            Playbook execution results
        """
        raise NotImplementedError("Subclass must implement receive_playbook_result")

    def sync_status_with_soar(self, incident_id: str, status: str) -> bool:
        """
        Synchronize incident status with SOAR platform

        Args:
            incident_id: Incident ID on SOAR
            status: New status

        Returns:
            True if sync successful
        """
        raise NotImplementedError("Subclass must implement sync_status_with_soar")

    def get_available_playbooks(self) -> List[Dict]:
        """
        Get list of available playbooks on platform

        Returns:
            List of playbook definitions
        """
        raise NotImplementedError("Subclass must implement get_available_playbooks")

    def _format_incident_for_soar(self, incident: Dict) -> Dict:
        """Format incident for SOAR platform"""
        return {
            'title': incident.get('title', incident.get('message', 'Security Incident')),
            'description': incident.get('description', ''),
            'severity': self._convert_severity(incident.get('severity', 5)),
            'source': 'aws_guardian',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': {
                'threat_id': incident.get('threat_id'),
                'account_id': incident.get('account_id'),
                'threat_type': incident.get('threat_type')
            }
        }

    def _convert_severity(self, aws_severity: int) -> str:
        """Convert AWS severity (0-10) to SOAR severity level"""
        if aws_severity >= 8:
            return 'critical'
        elif aws_severity >= 6:
            return 'high'
        elif aws_severity >= 4:
            return 'medium'
        else:
            return 'low'
