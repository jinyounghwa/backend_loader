"""IAM policy analysis and anomaly detection."""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import json


class IAMPolicyAnalyzer:
    """Analyze IAM policies for risk."""

    ADMIN_ACTIONS = ['*', 'iam:*', 'sts:*']
    DANGEROUS_ACTIONS = ['iam:*', 'ec2:*', 's3:*', 'rds:*', 'lambda:*']

    def analyze_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze policy and calculate risk score."""
        statements = policy.get('Statement', [])

        if not statements:
            return {
                'risk_score': 0,
                'policy_type': 'EMPTY',
                'dangerous_actions': [],
                'has_wildcard_action': False
            }

        all_actions = set()
        has_wildcard = False
        allow_statements = [s for s in statements if s.get('Effect') == 'Allow']

        for stmt in allow_statements:
            actions = stmt.get('Action', [])
            if isinstance(actions, str):
                actions = [actions]

            for action in actions:
                all_actions.add(action)
                if action == '*' or action.endswith(':*'):
                    has_wildcard = True

        # Determine policy type
        if '*' in all_actions:
            policy_type = 'ADMIN_ACCESS'
            risk_score = 100
        elif 'iam:*' in all_actions or 'sts:*' in all_actions:
            # IAM and STS wildcards are extremely dangerous
            policy_type = 'PRIVILEGE_ESCALATION'
            risk_score = 95
        elif any(action in self.DANGEROUS_ACTIONS for action in all_actions):
            policy_type = 'POWER_USER'
            risk_score = 80
        elif has_wildcard:
            policy_type = 'WILDCARD'
            risk_score = 90
        else:
            policy_type = 'RESTRICTED'
            risk_score = 10

        dangerous_actions = [a for a in all_actions if a in self.DANGEROUS_ACTIONS or '*' in a]

        return {
            'risk_score': risk_score,
            'policy_type': policy_type,
            'dangerous_actions': dangerous_actions,
            'has_wildcard_action': has_wildcard,
            'total_actions': len(all_actions)
        }


class PrivilegeEscalationDetector:
    """Detect privilege escalation patterns."""

    ESCALATION_EVENTS = {
        'AttachUserPolicy': 'policy_attachment',
        'AttachRolePolicy': 'policy_attachment',
        'PutUserPolicy': 'inline_policy',
        'CreateAccessKey': 'access_key',
        'CreateLoginProfile': 'login_profile',
        'UpdateAssumeRolePolicy': 'trust_policy',
    }

    def detect_escalation(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Detect privilege escalation in an event."""
        event_name = event.get('eventName')
        params = event.get('requestParameters', {})

        if event_name not in self.ESCALATION_EVENTS:
            return {'is_escalation': False}

        escalation_type = self.ESCALATION_EVENTS[event_name]

        # Check if attaching admin policy
        if event_name in ['AttachUserPolicy', 'AttachRolePolicy']:
            policy_arn = params.get('policyArn', '')
            if 'AdministratorAccess' in policy_arn:
                return {
                    'is_escalation': True,
                    'escalation_type': 'direct_admin_attach',
                    'risk_score': 95,
                    'policy': policy_arn
                }

        # Check for inline admin policy
        if event_name == 'PutUserPolicy':
            policy_doc = params.get('policyDocument', '{}')
            try:
                if isinstance(policy_doc, str):
                    policy = json.loads(policy_doc)
                else:
                    policy = policy_doc

                analyzer = IAMPolicyAnalyzer()
                risk = analyzer.analyze_policy(policy)

                if risk['risk_score'] >= 80:
                    return {
                        'is_escalation': True,
                        'escalation_type': 'inline_admin_policy',
                        'risk_score': risk['risk_score'],
                        'policy_type': risk['policy_type']
                    }
            except Exception:
                pass

        # Access key creation on privileged account
        if event_name == 'CreateAccessKey':
            user = params.get('userName', '')
            if 'service' in user.lower() or 'prod' in user.lower():
                return {
                    'is_escalation': True,
                    'escalation_type': 'access_key_creation',
                    'risk_score': 70,
                    'user': user
                }

        return {'is_escalation': False}


class UnusedRoleDetector:
    """Detect unused IAM roles."""

    UNUSED_THRESHOLD_DAYS = 90

    def detect_unused(self, role: Dict[str, Any]) -> Dict[str, Any]:
        """Detect if role is unused."""
        role_name = role.get('RoleName', 'unknown')
        create_date = self._parse_date(role.get('CreateDate'))
        last_used = self._parse_date(role.get('LastUsed'))

        if create_date is None:
            return {'is_unused': False, 'days_unused': 0}

        # If no last used, consider it unused
        if last_used is None:
            days_since_creation = (datetime.now() - create_date).days
            return {
                'is_unused': True,
                'days_unused': days_since_creation,
                'reason': 'never_used',
                'role': role_name
            }

        # Check if unused for more than threshold
        days_since_last_use = (datetime.now() - last_used).days
        is_unused = days_since_last_use > self.UNUSED_THRESHOLD_DAYS

        return {
            'is_unused': is_unused,
            'days_unused': days_since_last_use,
            'threshold_days': self.UNUSED_THRESHOLD_DAYS,
            'role': role_name,
            'last_used': last_used.isoformat() if last_used else None
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 datetime."""
        if not date_str:
            return None
        try:
            if isinstance(date_str, str):
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date_str
        except Exception:
            return None


class CrossAccountAnalyzer:
    """Analyze cross-account IAM permissions."""

    def analyze_trust(self, trust_policy: Dict[str, Any], current_account: str) -> Dict[str, Any]:
        """Analyze trust relationships."""
        statements = trust_policy.get('Statement', [])

        external_accounts: Set[str] = set()
        has_wildcard = False
        is_service_principal = False

        for stmt in statements:
            if stmt.get('Effect') != 'Allow':
                continue

            principal = stmt.get('Principal', {})

            # Check for wildcard principal
            if principal == '*':
                has_wildcard = True
                continue

            # Check for service principal
            if isinstance(principal, dict) and 'Service' in principal:
                is_service_principal = True
                continue

            # Check for AWS principals (accounts)
            if isinstance(principal, dict) and 'AWS' in principal:
                aws_principals = principal['AWS']
                if isinstance(aws_principals, str):
                    aws_principals = [aws_principals]

                for arn in aws_principals:
                    account = self._extract_account_from_arn(arn)
                    if account and account != current_account:
                        external_accounts.add(account)

        has_cross_account = len(external_accounts) > 0

        risk_score = 0
        if has_wildcard:
            risk_score = 95
        elif has_cross_account:
            risk_score = 60
        elif is_service_principal:
            risk_score = 20

        return {
            'has_cross_account': has_cross_account,
            'external_accounts': sorted(list(external_accounts)),
            'is_service_principal': is_service_principal,
            'has_wildcard_principal': has_wildcard,
            'risk_score': risk_score
        }

    def _extract_account_from_arn(self, arn: str) -> Optional[str]:
        """Extract account ID from ARN."""
        parts = arn.split(':')
        if len(parts) >= 5:
            return parts[4]
        return None


