"""Handler for automatic ticket creation from threat detections"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone

from guardian.services.jira_service import JiraTicketService
from guardian.services.servicenow_service import ServiceNowTicketService

logger = logging.getLogger(__name__)


class TicketingHandler:
    """Orchestrate automatic ticket creation from threat detections"""

    def __init__(self, jira_service: Optional[JiraTicketService] = None,
                 servicenow_service: Optional[ServiceNowTicketService] = None):
        """
        Args:
            jira_service: Optional Jira service instance
            servicenow_service: Optional ServiceNow service instance
        """
        self.jira = jira_service
        self.servicenow = servicenow_service
        self.ticket_mapping = {}

    def create_ticket(self, threat: Dict) -> Dict:
        """
        Create ticket(s) for threat detection

        Args:
            threat: Threat object with rule_id, severity, message, evidence, account_id

        Returns:
            Ticket creation result with ticket IDs and platform info
        """
        try:
            enriched_threat = self.enrich_ticket_with_evidence(threat)
            assignee = self.add_assignee_by_rule(enriched_threat)
            enriched_threat['assignee'] = assignee

            result = {
                'threat_id': threat.get('rule_id'),
                'account_id': threat.get('account_id'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'tickets': {},
                'status': 'success'
            }

            if self.jira:
                jira_key = self.jira.create_issue(enriched_threat)
                if jira_key:
                    result['tickets']['jira'] = jira_key
                    self.ticket_mapping[threat.get('rule_id')] = {
                        'jira': jira_key,
                        'threat': enriched_threat
                    }

            if self.servicenow:
                snow_number = self.servicenow.create_incident(enriched_threat)
                if snow_number:
                    result['tickets']['servicenow'] = snow_number
                    if threat.get('rule_id') in self.ticket_mapping:
                        self.ticket_mapping[threat.get('rule_id')]['servicenow'] = snow_number

            if not result['tickets']:
                result['status'] = 'failed'
                logger.error(f"No tickets created for threat {threat.get('rule_id')}")

            logger.info(f"Created tickets for threat {threat.get('rule_id')}: {result['tickets']}")
            return result

        except Exception as e:
            logger.error(f"Error creating ticket: {str(e)}")
            return {
                'threat_id': threat.get('rule_id'),
                'status': 'error',
                'error': str(e)
            }

    def enrich_ticket_with_evidence(self, threat: Dict) -> Dict:
        """
        Enrich threat with CloudTrail evidence for ticket

        Args:
            threat: Threat object

        Returns:
            Enriched threat with formatted evidence
        """
        try:
            enriched = threat.copy()

            if 'evidence' in enriched:
                enriched['evidence_summary'] = self._summarize_evidence(enriched['evidence'])
                enriched['evidence_logs'] = enriched['evidence']

            enriched['detection_timestamp'] = enriched.get('timestamp', datetime.now(timezone.utc).isoformat())
            enriched['risk_score'] = enriched.get('severity', 5)

            logger.debug(f"Enriched threat {threat.get('rule_id')} with evidence")
            return enriched

        except Exception as e:
            logger.error(f"Error enriching threat: {str(e)}")
            return threat

    def add_assignee_by_rule(self, threat: Dict) -> Dict:
        """
        Assign ticket to responsible team based on threat type/rule

        Args:
            threat: Threat object with threat_type and severity

        Returns:
            Assignee info with name and team
        """
        try:
            threat_type = threat.get('threat_type', 'unknown').lower()
            severity = threat.get('severity', 5)

            assignee = {
                'name': 'AWS Security Team',
                'team': 'security'
            }

            if 'ec2' in threat_type or 'compute' in threat_type:
                assignee['team'] = 'infrastructure'
                assignee['on_call_group'] = 'infra-oncall'

            elif 's3' in threat_type or 'storage' in threat_type:
                assignee['team'] = 'storage'
                assignee['on_call_group'] = 'storage-oncall'

            elif 'iam' in threat_type or 'auth' in threat_type:
                assignee['team'] = 'identity'
                assignee['on_call_group'] = 'identity-oncall'

            elif 'cost' in threat_type or 'billing' in threat_type:
                assignee['team'] = 'finance'
                assignee['on_call_group'] = 'finance-oncall'

            if severity >= 8:
                assignee['escalation_required'] = True
                assignee['escalate_to'] = 'Security Leadership'

            logger.info(f"Assigned threat {threat.get('rule_id')} to {assignee['team']}")
            return assignee

        except Exception as e:
            logger.error(f"Error assigning ticket: {str(e)}")
            return {'name': 'AWS Security Team', 'team': 'security'}

    def track_ticket_lifecycle(self, threat_id: str, event_type: str, status: Dict) -> Dict:
        """
        Track ticket lifecycle events (created, updated, resolved)

        Args:
            threat_id: Original threat/rule ID
            event_type: Event type (created, updated, resolved, closed)
            status: Current ticket status with IDs

        Returns:
            Lifecycle tracking record
        """
        try:
            record = {
                'threat_id': threat_id,
                'event_type': event_type,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': status
            }

            if threat_id in self.ticket_mapping:
                record['tickets'] = self.ticket_mapping[threat_id]

            logger.info(f"Tracked lifecycle event {event_type} for threat {threat_id}")
            return record

        except Exception as e:
            logger.error(f"Error tracking lifecycle: {str(e)}")
            return {
                'threat_id': threat_id,
                'event_type': event_type,
                'error': str(e)
            }

    def handle_lambda_event(self, event: Dict) -> Dict:
        """
        Handle Lambda SNS/EventBridge event for threat notification

        Args:
            event: Lambda event from SNS/EventBridge

        Returns:
            Ticketing result
        """
        try:
            threats = self._parse_event_threats(event)
            results = []

            for threat in threats:
                result = self.create_ticket(threat)
                results.append(result)

            return {
                'status': 'success',
                'threats_processed': len(threats),
                'results': results
            }

        except Exception as e:
            logger.error(f"Error handling Lambda event: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _summarize_evidence(self, evidence: Dict) -> str:
        if isinstance(evidence, dict):
            summary = []
            if 'event_name' in evidence:
                summary.append(f"Event: {evidence['event_name']}")
            if 'principal' in evidence:
                summary.append(f"Principal: {evidence['principal']}")
            if 'source_ip' in evidence:
                summary.append(f"Source IP: {evidence['source_ip']}")
            if 'user_agent' in evidence:
                summary.append(f"User Agent: {evidence['user_agent']}")
            return ' | '.join(summary) if summary else "Evidence available in logs"
        return str(evidence)

    def _parse_event_threats(self, event: Dict) -> List[Dict]:
        threats = []

        if 'Records' in event:
            for record in event['Records']:
                if 'Sns' in record:
                    body = json.loads(record['Sns'].get('Message', '{}'))
                    if 'threat' in body:
                        threats.append(body['threat'])
                elif 'detail' in record:
                    if 'threat' in record['detail']:
                        threats.append(record['detail']['threat'])
        elif 'detail' in event:
            if 'threat' in event['detail']:
                threats.append(event['detail']['threat'])
        elif 'threat' in event:
            threats.append(event['threat'])

        return threats
