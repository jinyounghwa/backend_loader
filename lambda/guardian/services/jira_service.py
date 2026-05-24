"""Jira ticket management service for security incidents"""

import logging
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class JiraTicketService:
    """Create and manage security incident tickets in Jira"""

    def __init__(self, base_url: str, api_token: str, project_key: str):
        """
        Args:
            base_url: Jira instance URL (e.g., https://company.atlassian.net)
            api_token: Jira API token for authentication
            project_key: Jira project key (e.g., 'SEC', 'OPS')
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.project_key = project_key
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }

    def create_issue(self, threat: Dict) -> Optional[str]:
        """
        Create a Jira security issue from threat detection

        Args:
            threat: Threat object with rule_id, severity, message, evidence

        Returns:
            Jira issue key (e.g., 'SEC-123') or None on failure
        """
        try:
            issue_type = self._get_issue_type_by_severity(threat.get('severity', 5))
            labels = self._extract_labels(threat)

            payload = {
                'fields': {
                    'project': {'key': self.project_key},
                    'summary': f"[{threat.get('severity', 5)}/10] {threat.get('message', 'Security Threat Detected')}",
                    'description': self._format_issue_description(threat),
                    'issuetype': {'name': issue_type},
                    'priority': {'name': self._get_priority_by_severity(threat.get('severity', 5))},
                    'labels': labels,
                    'customfield_account': threat.get('account_id', 'unknown'),
                    'customfield_threat_type': threat.get('threat_type', 'unknown')
                }
            }

            response = requests.post(
                f'{self.base_url}/rest/api/3/issues',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 201:
                issue_key = response.json().get('key')
                logger.info(f"Created Jira issue {issue_key} for threat {threat.get('rule_id')}")
                return issue_key
            else:
                logger.error(f"Failed to create Jira issue: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating Jira issue: {str(e)}")
            return None

    def update_issue_status(self, issue_key: str, status: str) -> bool:
        """
        Update Jira issue status

        Args:
            issue_key: Jira issue key (e.g., 'SEC-123')
            status: New status ('To Do', 'In Progress', 'Done', etc.)

        Returns:
            True if successful
        """
        try:
            transition_id = self._get_transition_id(issue_key, status)
            if not transition_id:
                logger.warning(f"No transition found from current status to {status}")
                return False

            payload = {'transition': {'id': transition_id}}

            response = requests.post(
                f'{self.base_url}/rest/api/3/issues/{issue_key}/transitions',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                logger.info(f"Updated {issue_key} status to {status}")
                return True
            else:
                logger.error(f"Failed to update issue status: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error updating Jira issue status: {str(e)}")
            return False

    def add_comment_with_evidence(self, issue_key: str, evidence: Dict) -> bool:
        """
        Add CloudTrail evidence as a comment to issue

        Args:
            issue_key: Jira issue key
            evidence: CloudTrail logs or other evidence

        Returns:
            True if successful
        """
        try:
            comment_text = self._format_evidence_comment(evidence)

            payload = {
                'body': {
                    'content': [
                        {
                            'type': 'paragraph',
                            'content': [
                                {
                                    'type': 'text',
                                    'text': comment_text
                                }
                            ]
                        }
                    ]
                }
            }

            response = requests.post(
                f'{self.base_url}/rest/api/3/issues/{issue_key}/comments',
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 201]:
                logger.info(f"Added evidence comment to {issue_key}")
                return True
            else:
                logger.error(f"Failed to add comment: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error adding evidence comment: {str(e)}")
            return False

    def link_related_issues(self, issue_key: str, related_issues: List[str], link_type: str = 'relates to') -> bool:
        """
        Link related Jira issues (e.g., previous incidents)

        Args:
            issue_key: Jira issue key
            related_issues: List of related issue keys
            link_type: Link type ('relates to', 'duplicates', 'is blocked by', etc.)

        Returns:
            True if all links successful
        """
        try:
            all_success = True

            for related_key in related_issues:
                payload = {
                    'type': {'name': link_type},
                    'inwardIssue': {'key': issue_key},
                    'outwardIssue': {'key': related_key}
                }

                response = requests.post(
                    f'{self.base_url}/rest/api/3/issueLink',
                    headers=self.headers,
                    json=payload,
                    timeout=10
                )

                if response.status_code not in [200, 201]:
                    logger.warning(f"Failed to link {issue_key} to {related_key}")
                    all_success = False
                else:
                    logger.info(f"Linked {issue_key} to {related_key}")

            return all_success

        except Exception as e:
            logger.error(f"Error linking issues: {str(e)}")
            return False

    def _get_issue_type_by_severity(self, severity: int) -> str:
        if severity >= 8:
            return 'Critical'
        elif severity >= 6:
            return 'Major'
        elif severity >= 4:
            return 'Minor'
        else:
            return 'Trivial'

    def _get_priority_by_severity(self, severity: int) -> str:
        if severity >= 8:
            return 'Highest'
        elif severity >= 6:
            return 'High'
        elif severity >= 4:
            return 'Medium'
        else:
            return 'Low'

    def _extract_labels(self, threat: Dict) -> List[str]:
        labels = ['security', 'aws-guardian']
        if threat.get('threat_type'):
            labels.append(threat['threat_type'].lower().replace('_', '-'))
        if threat.get('account_id'):
            labels.append(f"account-{threat['account_id']}")
        return labels

    def _format_issue_description(self, threat: Dict) -> str:
        lines = [
            f"h3. Security Threat Alert",
            f"Rule ID: {threat.get('rule_id', 'unknown')}",
            f"Severity: {threat.get('severity', 5)}/10",
            f"Account: {threat.get('account_id', 'unknown')}",
            f"Timestamp: {threat.get('timestamp', datetime.now(timezone.utc).isoformat())}",
            f"",
            f"h4. Details",
            f"{threat.get('message', 'No details provided')}",
            f"",
            f"h4. Evidence",
            f"See comments for detailed CloudTrail logs",
            f"",
            f"h4. Recommended Actions",
            f"* Review CloudTrail logs",
            f"* Verify resource changes",
            f"* Take corrective action if needed"
        ]
        return '\n'.join(lines)

    def _format_evidence_comment(self, evidence: Dict) -> str:
        try:
            if isinstance(evidence, dict):
                evidence_str = json.dumps(evidence, indent=2, default=str)
            else:
                evidence_str = str(evidence)
            return f"CloudTrail Evidence:\n{{{{{evidence_str}}}}}"
        except Exception as e:
            logger.error(f"Error formatting evidence: {str(e)}")
            return "Evidence could not be formatted"

    def _get_transition_id(self, issue_key: str, target_status: str) -> Optional[str]:
        try:
            response = requests.get(
                f'{self.base_url}/rest/api/3/issues/{issue_key}/transitions',
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                transitions = response.json().get('transitions', [])
                for transition in transitions:
                    if transition.get('to', {}).get('name') == target_status:
                        return transition.get('id')

            return None

        except Exception as e:
            logger.error(f"Error getting transitions: {str(e)}")
            return None
