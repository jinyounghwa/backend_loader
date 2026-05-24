"""ServiceNow incident management service for security alerts"""

import logging
import json
import requests
from typing import Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ServiceNowTicketService:
    """Create and manage security incidents in ServiceNow"""

    def __init__(self, instance_url: str, api_key: str):
        """
        Args:
            instance_url: ServiceNow instance URL (e.g., https://company.service-now.com)
            api_key: ServiceNow API key or OAuth token
        """
        self.instance_url = instance_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def create_incident(self, threat: Dict) -> Optional[str]:
        """
        Create a ServiceNow incident from threat detection

        Args:
            threat: Threat object with rule_id, severity, message, evidence

        Returns:
            ServiceNow incident number (e.g., 'INC0123456') or None on failure
        """
        try:
            severity = self._convert_severity_to_servicenow(threat.get('severity', 5))
            urgency = self._get_urgency_by_severity(threat.get('severity', 5))

            payload = {
                'short_description': f"[AWS] {threat.get('message', 'Security Threat Detected')}",
                'description': self._format_incident_description(threat),
                'incident_state': 1,
                'severity': severity,
                'urgency': urgency,
                'impact': self._get_impact_by_severity(threat.get('severity', 5)),
                'category': 'security',
                'subcategory': 'aws_security',
                'cmdb_ci': threat.get('account_id', 'aws-account'),
                'assignment_group': 'AWS Security Team',
                'caller_id': 'AWS Guardian System'
            }

            response = requests.post(
                f'{self.instance_url}/api/now/table/incident',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                incident_number = response.json().get('result', {}).get('number')
                logger.info(f"Created ServiceNow incident {incident_number} for threat {threat.get('rule_id')}")
                return incident_number
            else:
                logger.error(f"Failed to create ServiceNow incident: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating ServiceNow incident: {str(e)}")
            return None

    def attach_evidence_to_incident(self, incident_number: str, evidence: Dict) -> bool:
        """
        Attach CloudTrail evidence to incident as work notes

        Args:
            incident_number: ServiceNow incident number
            evidence: CloudTrail logs or other evidence

        Returns:
            True if successful
        """
        try:
            work_notes = f"CloudTrail Evidence:\n{json.dumps(evidence, indent=2, default=str)}"

            payload = {
                'work_notes': work_notes
            }

            response = requests.patch(
                f'{self.instance_url}/api/now/table/incident?sysparm_query=number={incident_number}',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                logger.info(f"Attached evidence to incident {incident_number}")
                return True
            else:
                logger.error(f"Failed to attach evidence: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error attaching evidence: {str(e)}")
            return False

    def escalate_incident(self, incident_number: str, severity: int) -> bool:
        """
        Escalate incident based on threat severity

        Args:
            incident_number: ServiceNow incident number
            severity: Threat severity (0-10 scale)

        Returns:
            True if escalation successful
        """
        try:
            if severity >= 8:
                escalation_level = 3
                assignment_group = 'AWS Security Leadership'
                priority = 1
            elif severity >= 6:
                escalation_level = 2
                assignment_group = 'AWS Security Team'
                priority = 2
            else:
                escalation_level = 1
                assignment_group = 'AWS Operations'
                priority = 3

            payload = {
                'escalation': escalation_level,
                'assignment_group': assignment_group,
                'priority': priority
            }

            response = requests.post(
                f'{self.instance_url}/api/now/table/incident?sysparm_query=number={incident_number}',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                logger.info(f"Escalated incident {incident_number} to level {escalation_level}")
                return True
            else:
                logger.error(f"Failed to escalate incident: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error escalating incident: {str(e)}")
            return False

    def update_incident_status(self, incident_number: str, status: str, resolution: Optional[str] = None) -> bool:
        """
        Update incident status (1=New, 2=In Progress, 7=Resolved, 8=Closed)

        Args:
            incident_number: ServiceNow incident number
            status: Status value (1, 2, 7, 8)
            resolution: Resolution notes if closing

        Returns:
            True if successful
        """
        try:
            status_map = {
                'new': 1,
                'in_progress': 2,
                'on_hold': 3,
                'resolved': 7,
                'closed': 8
            }

            status_value = status_map.get(status.lower(), status)

            payload = {
                'incident_state': status_value
            }

            if resolution:
                payload['resolution_notes'] = resolution

            response = requests.patch(
                f'{self.instance_url}/api/now/table/incident?sysparm_query=number={incident_number}',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                logger.info(f"Updated incident {incident_number} status to {status}")
                return True
            else:
                logger.error(f"Failed to update status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error updating incident status: {str(e)}")
            return False

    def _convert_severity_to_servicenow(self, aws_severity: int) -> int:
        if aws_severity >= 8:
            return 1
        elif aws_severity >= 6:
            return 2
        elif aws_severity >= 4:
            return 3
        else:
            return 4

    def _get_urgency_by_severity(self, severity: int) -> int:
        if severity >= 8:
            return 1
        elif severity >= 6:
            return 2
        else:
            return 3

    def _get_impact_by_severity(self, severity: int) -> int:
        if severity >= 8:
            return 1
        elif severity >= 6:
            return 2
        else:
            return 3

    def _format_incident_description(self, threat: Dict) -> str:
        lines = [
            f"AWS Guardian Security Alert",
            f"",
            f"Rule ID: {threat.get('rule_id', 'unknown')}",
            f"Severity: {threat.get('severity', 5)}/10",
            f"Account: {threat.get('account_id', 'unknown')}",
            f"Threat Type: {threat.get('threat_type', 'unknown')}",
            f"Timestamp: {threat.get('timestamp', datetime.now(timezone.utc).isoformat())}",
            f"",
            f"Details:",
            f"{threat.get('message', 'No details provided')}",
            f"",
            f"Next Steps:",
            f"1. Review CloudTrail logs",
            f"2. Verify resource status",
            f"3. Take corrective action",
            f"4. Update incident with findings"
        ]
        return '\n'.join(lines)
