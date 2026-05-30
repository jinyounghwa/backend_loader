"""Response policies for threat mitigation."""

from typing import Dict, List, Any, Optional


class ResponsePolicy:
    """Define and evaluate response policies."""

    def __init__(self):
        self.rules: List[Dict[str, Any]] = []

    def add_rule(self, rule: Dict[str, Any]) -> None:
        """Add a response rule."""
        self.rules.append(rule)

    def evaluate_threat(self, threat: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate threat against policies."""
        severity = threat.get('severity')

        # Find matching rule
        for rule in self.rules:
            if rule.get('severity') == severity:
                return {
                    'action': rule.get('action'),
                    'delay_seconds': rule.get('delay_seconds', 0),
                    'severity': severity
                }

        return {'action': 'MONITOR', 'delay_seconds': 0}


class PolicyEvaluator:
    """Evaluate policies for threat matching."""

    def __init__(self):
        self.policies: List[Dict[str, Any]] = []

    def add_policy(self, policy: Dict[str, Any]) -> None:
        """Add a matching policy."""
        self.policies.append(policy)

    def matches(self, threat: Dict[str, Any]) -> bool:
        """Check if threat matches any policy."""
        threat_type = threat.get('threat_type')
        resource_type = threat.get('resource_type')

        for policy in self.policies:
            if policy.get('threat_type') == threat_type:
                return True
            if policy.get('resource_type') == resource_type:
                return True

        return False

    def get_action(self, threat: Dict[str, Any]) -> Optional[str]:
        """Get action for threat based on priority."""
        # Sort by priority
        sorted_policies = sorted(
            self.policies,
            key=lambda p: p.get('priority', 999)
        )

        for policy in sorted_policies:
            if self.policy_matches(policy, threat):
                return policy.get('action')

        return None

    def policy_matches(self, policy: Dict[str, Any], threat: Dict[str, Any]) -> bool:
        """Check if policy matches threat."""
        return True  # Simplified matching

