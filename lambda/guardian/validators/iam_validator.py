"""IAM policy validation and scoring."""

from typing import Dict, List, Any, Optional
import json


class MinimumPrivilegeValidator:
    """Validate IAM policies for minimum privilege principle."""

    DANGEROUS_COMBINATIONS = [
        ('*', '*'),  # Action * with Resource *
        ('iam:*', '*'),  # All IAM with all resources
        ('sts:*', '*'),  # All STS with all resources
    ]

    CRITICAL_ACTIONS = [
        'iam:*',
        'ec2:*',
        's3:DeleteBucket',
        'rds:DeleteDBInstance',
        'sts:AssumeRole'
    ]

    def validate(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Validate policy for minimum privilege compliance."""
        statements = policy.get('Statement', [])
        issues = []
        compliance_score = 100

        for idx, stmt in enumerate(statements):
            if stmt.get('Effect') != 'Allow':
                continue

            stmt_issues = self._validate_statement(stmt)
            issues.extend(stmt_issues)

            # Very aggressive penalty for wildcard violations (especially action * and resource *)
            if stmt_issues:
                wildcard_count = len([i for i in stmt_issues if 'Wildcard' in i])
                if wildcard_count >= 2:  # Both action * and resource *
                    compliance_score -= 85
                elif wildcard_count > 0:
                    compliance_score -= 50
                else:
                    compliance_score -= 15 * len(stmt_issues)

        compliance_score = max(0, min(100, compliance_score))
        is_valid = compliance_score >= 70 and not issues

        return {
            'is_valid': is_valid,
            'compliance_score': compliance_score,
            'issues': issues,
            'total_statements': len(statements),
            'allow_statements': len([s for s in statements if s.get('Effect') == 'Allow'])
        }

    def _validate_statement(self, statement: Dict[str, Any]) -> List[str]:
        """Validate individual statement."""
        issues = []

        actions = statement.get('Action', [])
        if isinstance(actions, str):
            actions = [actions]

        resources = statement.get('Resource', [])
        if isinstance(resources, str):
            resources = [resources]

        # Check for wildcard action
        if '*' in actions:
            issues.append("Wildcard action (*) grants all permissions")

        # Check for wildcard resource
        if '*' in resources:
            issues.append("Wildcard resource (*) grants access to all resources")

        # Check for dangerous action combinations
        for action in actions:
            if action in self.CRITICAL_ACTIONS:
                issues.append(f"Critical action {action} should be restricted")
            elif action.endswith(':*'):
                issues.append(f"Service-wide wildcard {action} grants broad permissions")

        # Check for missing resource restrictions on dangerous actions
        if '*' in resources:
            dangerous = [a for a in actions if a in self.CRITICAL_ACTIONS]
            if dangerous:
                issues.append(f"Unrestricted access to dangerous actions: {', '.join(dangerous)}")

        # Check for inline policies with high privilege
        if len(actions) > 5 and '*' not in resources:
            issues.append("Policy grants too many permissions without clear scope")

        return issues


class PolicyRiskScorer:
    """Score IAM policy risk (0-100)."""

    ADMIN_THRESHOLD = 100
    POWER_USER_THRESHOLD = 80
    ELEVATED_THRESHOLD = 50

    def score(self, policy: Dict[str, Any]) -> float:
        """Calculate policy risk score."""
        statements = policy.get('Statement', [])

        if not statements:
            return 0

        # Track highest risk score
        max_score = 0

        for stmt in statements:
            if stmt.get('Effect') == 'Deny':
                # Deny statements reduce risk, but we still track them
                continue

            if stmt.get('Effect') != 'Allow':
                continue

            stmt_score = self._score_statement(stmt)
            max_score = max(max_score, stmt_score)

        return max_score

    def _score_statement(self, statement: Dict[str, Any]) -> float:
        """Score individual Allow statement."""
        actions = statement.get('Action', [])
        if isinstance(actions, str):
            actions = [actions]

        resources = statement.get('Resource', [])
        if isinstance(resources, str):
            resources = [resources]

        # Admin access (Action * and Resource *)
        if '*' in actions and '*' in resources:
            return 100

        # Check for wildcard action
        if '*' in actions:
            return 85

        # Check for dangerous action patterns (including service:* patterns)
        dangerous_count = 0
        service_wildcard_count = 0

        for action in actions:
            if action.endswith(':*'):
                service_wildcard_count += 1
            if action in ['iam:*', 'ec2:*', 's3:*', 'rds:*', 'sts:*']:
                dangerous_count += 1

        # Service wildcards like ec2:*, s3:* are very risky
        total_dangerous = dangerous_count + service_wildcard_count

        # Calculate score based on dangerous actions
        if total_dangerous > 2:
            if '*' in resources:
                return 80
            else:
                return 70
        elif total_dangerous > 1:
            if '*' in resources:
                return 75
            else:
                return 65
        elif total_dangerous == 1:
            if '*' in resources:
                return 70
            else:
                return 45

        # Restricted access
        if '*' not in resources:
            return 15
        else:
            return 25

