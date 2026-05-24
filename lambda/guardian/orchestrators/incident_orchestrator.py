"""End-to-end incident orchestration from detection to resolution"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class IncidentOrchestrator:
    """Orchestrate complete incident response workflow"""

    def __init__(self, ticketing_handler=None, workflow_engine=None, soar_connector=None):
        """
        Args:
            ticketing_handler: Handler for ticket creation
            workflow_engine: Engine for workflow execution
            soar_connector: SOAR platform connector
        """
        self.ticketing = ticketing_handler
        self.workflows = workflow_engine
        self.soar = soar_connector
        self.incidents = {}

    def orchestrate_incident_response(self, threat: Dict) -> Dict:
        """
        Orchestrate complete incident response from threat to resolution

        Args:
            threat: Threat detection event

        Returns:
            Orchestration result with all response components
        """
        try:
            incident_id = str(uuid.uuid4())
            incident = {
                'incident_id': incident_id,
                'threat_id': threat.get('rule_id'),
                'severity': threat.get('severity', 5),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'detected',
                'components': {
                    'ticket': None,
                    'workflow': None,
                    'soar': None
                },
                'timeline': []
            }

            self.incidents[incident_id] = incident

            incident = self._create_ticket(incident, threat)
            incident = self._execute_workflow(incident, threat)
            incident = self._send_to_soar(incident, threat)

            incident['status'] = 'orchestrated'
            incident['orchestrated_at'] = datetime.now(timezone.utc).isoformat()

            logger.info(f"Orchestrated incident {incident_id} for threat {threat.get('rule_id')}")
            return incident

        except Exception as e:
            logger.error(f"Error orchestrating incident: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def coordinate_parallel_workflows(self, workflows: List[Dict], threat: Dict) -> Dict:
        """
        Execute multiple workflows in parallel for threat

        Args:
            workflows: List of workflows to execute
            threat: Threat event

        Returns:
            Coordination result with all execution results
        """
        try:
            result = {
                'threat_id': threat.get('rule_id'),
                'workflow_count': len(workflows),
                'executions': [],
                'success_count': 0,
                'failure_count': 0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            for workflow in workflows:
                execution = self.workflows.execute_workflow(workflow, threat) if self.workflows else {}

                execution_result = {
                    'workflow_id': workflow.get('workflow_id'),
                    'status': execution.get('status', 'unknown'),
                    'success_count': execution.get('success_count', 0),
                    'failure_count': execution.get('failure_count', 0)
                }

                result['executions'].append(execution_result)

                if execution.get('status') in ['success', 'partial_success']:
                    result['success_count'] += 1
                else:
                    result['failure_count'] += 1

            logger.info(f"Coordinated {len(workflows)} workflows for threat {threat.get('rule_id')}")
            return result

        except Exception as e:
            logger.error(f"Error coordinating workflows: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def track_incident_to_resolution(self, incident_id: str) -> Optional[Dict]:
        """
        Track incident from detection through resolution

        Args:
            incident_id: Incident ID to track

        Returns:
            Full incident lifecycle and resolution status
        """
        try:
            if incident_id not in self.incidents:
                logger.warning(f"Incident {incident_id} not found")
                return None

            incident = self.incidents[incident_id]
            incident['tracked_at'] = datetime.now(timezone.utc).isoformat()

            incident['lifecycle'] = {
                'created': incident.get('created_at'),
                'orchestrated': incident.get('orchestrated_at'),
                'tracked': incident['tracked_at'],
                'status': incident['status'],
                'components': incident['components']
            }

            logger.info(f"Tracked incident {incident_id} status: {incident['status']}")
            return incident

        except Exception as e:
            logger.error(f"Error tracking incident: {str(e)}")
            return None

    def generate_incident_report(self, incident_id: str) -> Optional[Dict]:
        """
        Generate comprehensive incident response report

        Args:
            incident_id: Incident ID to report on

        Returns:
            Incident response report
        """
        try:
            if incident_id not in self.incidents:
                logger.warning(f"Incident {incident_id} not found")
                return None

            incident = self.incidents[incident_id]

            report = {
                'incident_id': incident_id,
                'threat_id': incident.get('threat_id'),
                'severity': incident.get('severity'),
                'timeline': incident.get('timeline', []),
                'response_summary': {
                    'ticket_created': incident['components'].get('ticket') is not None,
                    'workflow_executed': incident['components'].get('workflow') is not None,
                    'soar_integration': incident['components'].get('soar') is not None
                },
                'resolution_status': incident.get('status'),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Generated report for incident {incident_id}")
            return report

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return None

    def _create_ticket(self, incident: Dict, threat: Dict) -> Dict:
        """Create ticket for incident"""
        if not self.ticketing:
            return incident

        try:
            ticket_result = self.ticketing.create_ticket(threat)

            incident['components']['ticket'] = {
                'jira': ticket_result.get('tickets', {}).get('jira'),
                'servicenow': ticket_result.get('tickets', {}).get('servicenow'),
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            incident['timeline'].append({
                'event': 'ticket_created',
                'timestamp': incident['components']['ticket']['created_at'],
                'details': incident['components']['ticket']
            })

            logger.info(f"Created ticket for incident {incident['incident_id']}")

        except Exception as e:
            logger.error(f"Error creating ticket: {str(e)}")

        return incident

    def _execute_workflow(self, incident: Dict, threat: Dict) -> Dict:
        """Execute remediation workflow"""
        if not self.workflows:
            return incident

        try:
            sample_workflow = {
                'workflow_id': 'default_remediation',
                'enabled': True,
                'condition': {'rules': []},
                'steps': []
            }

            execution = self.workflows.execute_workflow(sample_workflow, threat)

            incident['components']['workflow'] = {
                'workflow_id': execution.get('workflow_id'),
                'execution_id': execution.get('execution_id'),
                'status': execution.get('status'),
                'executed_at': datetime.now(timezone.utc).isoformat()
            }

            incident['timeline'].append({
                'event': 'workflow_executed',
                'timestamp': incident['components']['workflow']['executed_at'],
                'details': incident['components']['workflow']
            })

            logger.info(f"Executed workflow for incident {incident['incident_id']}")

        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")

        return incident

    def _send_to_soar(self, incident: Dict, threat: Dict) -> Dict:
        """Send incident to SOAR platform"""
        if not self.soar:
            return incident

        try:
            soar_result = self.soar.send_incident_to_soar(threat)

            incident['components']['soar'] = {
                'platform': self.soar.platform,
                'incident_id': soar_result,
                'sent_at': datetime.now(timezone.utc).isoformat()
            }

            incident['timeline'].append({
                'event': 'sent_to_soar',
                'timestamp': incident['components']['soar']['sent_at'],
                'details': incident['components']['soar']
            })

            logger.info(f"Sent incident {incident['incident_id']} to SOAR platform")

        except Exception as e:
            logger.error(f"Error sending to SOAR: {str(e)}")

        return incident
