"""IAM Policy Validator"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PolicyValidator:
    """Validate IAM policies for compliance and best practices"""

    def __init__(self, iam_client):
        """
        Args:
            iam_client: boto3 IAM client
        """
        self.iam = iam_client

    def validate_iam_policy(self, policy: Dict) -> Dict:
        """
        Validate IAM policy structure and compliance

        Args:
            policy: IAM policy document

        Returns:
            Validation result with findings
        """
        try:
            validation = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'score': 100,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Check policy structure
            if 'Version' not in policy:
                validation['errors'].append("Missing 'Version' field")
                validation['is_valid'] = False
                validation['score'] -= 20

            if 'Statement' not in policy or not isinstance(policy.get('Statement'), list):
                validation['errors'].append("Invalid or missing 'Statement' array")
                validation['is_valid'] = False
                validation['score'] -= 30

            # Check statements
            for idx, statement in enumerate(policy.get('Statement', [])):
                stmt_errors = self._validate_statement(statement, idx)
                validation['errors'].extend(stmt_errors)

            # Check for overly permissive policies
            if self._is_overly_permissive(policy):
                validation['warnings'].append("Policy grants overly broad permissions")
                validation['score'] -= 25

            # Ensure score is within bounds
            validation['score'] = max(0, min(100, validation['score']))

            logger.info(f"Validated policy: score={validation['score']}")
            return validation

        except Exception as e:
            logger.error(f"Failed to validate policy: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def _validate_statement(self, statement: Dict, index: int) -> List[str]:
        """Helper: Validate individual policy statement"""
        errors = []

        if 'Effect' not in statement:
            errors.append(f"Statement {index}: Missing 'Effect' field")

        if 'Action' not in statement:
            errors.append(f"Statement {index}: Missing 'Action' field")

        if 'Resource' not in statement:
            errors.append(f"Statement {index}: Missing 'Resource' field")

        return errors

    def _is_overly_permissive(self, policy: Dict) -> bool:
        """Helper: Check if policy is overly permissive"""
        for statement in policy.get('Statement', []):
            if statement.get('Effect') != 'Allow':
                continue

            action = statement.get('Action', '')
            resource = statement.get('Resource', '')

            # Check for wildcard action and resource
            if action == '*' and resource == '*':
                return True

            # Check for Administrator role
            if action == '*' and 'arn:aws:iam::' in str(resource) and ':root' in str(resource):
                return True

        return False

    def check_least_privilege(self, policy: Dict) -> bool:
        """
        Check if policy follows least privilege principle

        Args:
            policy: IAM policy document

        Returns:
            True if policy follows least privilege
        """
        try:
            # Least privilege means specific actions and resources
            for statement in policy.get('Statement', []):
                if statement.get('Effect') != 'Allow':
                    continue

                action = statement.get('Action', '')
                resource = statement.get('Resource', '')

                # Wildcard action is not least privilege
                if action == '*' or (isinstance(action, list) and '*' in action):
                    logger.debug("Found wildcard action - not least privilege")
                    return False

                # Wildcard resource is not least privilege
                if resource == '*' or (isinstance(resource, list) and '*' in resource):
                    logger.debug("Found wildcard resource - not least privilege")
                    return False

            logger.info("Policy follows least privilege principle")
            return True

        except Exception as e:
            logger.error(f"Failed to check least privilege: {str(e)}")
            return False

    def detect_overly_permissive_policies(self, policies: List[Dict]) -> Dict:
        """
        Detect overly permissive policies in list

        Args:
            policies: List of IAM policy documents

        Returns:
            Detection result with problematic policies
        """
        try:
            result = {
                'total_policies': len(policies),
                'overly_permissive_count': 0,
                'problematic_policies': [],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            for idx, policy in enumerate(policies):
                if self._is_overly_permissive(policy):
                    result['overly_permissive_count'] += 1
                    result['problematic_policies'].append({
                        'index': idx,
                        'policy_version': policy.get('Version'),
                        'issue': 'Overly permissive - wildcard actions/resources'
                    })

            logger.info(f"Detected {result['overly_permissive_count']} overly permissive policies")
            return result

        except Exception as e:
            logger.error(f"Failed to detect overly permissive policies: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def suggest_policy_improvements(self, policy: Dict) -> List[Dict]:
        """
        Suggest improvements for IAM policy

        Args:
            policy: IAM policy document

        Returns:
            List of improvement suggestions
        """
        try:
            suggestions = []

            # Check for overly broad permissions
            if self._is_overly_permissive(policy):
                suggestions.append({
                    'severity': 'high',
                    'issue': 'Overly permissive actions and resources',
                    'suggestion': 'Replace * with specific actions and resource ARNs',
                    'example': 's3:GetObject on specific bucket ARN'
                })

            # Check for missing conditions
            has_conditions = any('Condition' in stmt for stmt in policy.get('Statement', []))
            if not has_conditions:
                suggestions.append({
                    'severity': 'medium',
                    'issue': 'No conditions on policy statements',
                    'suggestion': 'Add conditions to restrict when policy applies (IP, MFA, etc.)',
                    'example': 'Add aws:SourceIp or aws:MultiFactorAuthPresent conditions'
                })

            # Check for resource restrictions
            for statement in policy.get('Statement', []):
                if statement.get('Resource') == '*':
                    suggestions.append({
                        'severity': 'high',
                        'issue': 'Resource uses wildcard (*)',
                        'suggestion': 'Specify exact resource ARNs',
                        'example': 'arn:aws:s3:::specific-bucket/*'
                    })
                    break

            logger.info(f"Generated {len(suggestions)} improvement suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Failed to suggest improvements: {str(e)}")
            return []
