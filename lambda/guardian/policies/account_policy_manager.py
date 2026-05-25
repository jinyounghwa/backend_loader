from typing import Dict, List


class AccountPolicyManager:
    def __init__(self, policy_storage=None, audit_logger=None):
        self.policies = policy_storage or {}
        self.audit = audit_logger
        self.account_policies = {}

    def register_account_policy(self, account_id: str, policy: Dict) -> None:
        self.account_policies[account_id] = policy

    def get_account_policy(self, account_id: str) -> Dict:
        return self.account_policies.get(account_id, {})

    def evaluate_threat_against_policy(self, threat: Dict, account_id: str) -> Dict:
        policy = self.get_account_policy(account_id)

        if not policy:
            return {
                'allowed_strategies': ['MONITOR', 'ISOLATE', 'REMEDIATE', 'TERMINATE'],
                'restricted_strategies': [],
                'approval_required': False,
                'escalation_required': False,
            }

        allowed_strategies = policy.get('allowed_strategies', ['MONITOR', 'ISOLATE', 'REMEDIATE', 'TERMINATE'])
        restricted_strategies = [s for s in ['MONITOR', 'ISOLATE', 'REMEDIATE', 'TERMINATE'] if s not in allowed_strategies]

        threat_severity = threat.get('severity', 5)
        approval_required = threat_severity >= policy.get('approval_threshold', 8)
        escalation_required = threat_severity >= policy.get('escalation_threshold', 9)

        return {
            'allowed_strategies': allowed_strategies,
            'restricted_strategies': restricted_strategies,
            'approval_required': approval_required,
            'escalation_required': escalation_required,
        }

    def apply_policy_constraints(self, strategy: str, account_id: str) -> Dict:
        policy = self.get_account_policy(account_id)

        if not policy:
            return {
                'strategy': strategy,
                'allowed': True,
                'constraints': [],
            }

        allowed_strategies = policy.get('allowed_strategies', ['MONITOR', 'ISOLATE', 'REMEDIATE', 'TERMINATE'])
        is_allowed = strategy in allowed_strategies

        constraints = []
        if not is_allowed:
            constraints.append(f"Strategy {strategy} is restricted by account policy")

        max_resources = policy.get('max_resources_per_action', None)
        if max_resources:
            constraints.append(f"Maximum {max_resources} resources per action")

        return {
            'strategy': strategy,
            'allowed': is_allowed,
            'constraints': constraints,
        }

    def get_policy_violations(self, threat: Dict, account_id: str) -> List[Dict]:
        violations = []
        policy = self.get_account_policy(account_id)

        if not policy:
            return violations

        threat_severity = threat.get('severity', 5)

        if threat_severity >= policy.get('critical_threshold', 10):
            violations.append({
                'violation_type': 'critical_threat',
                'severity': threat_severity,
                'policy_limit': policy.get('critical_threshold'),
            })

        threat_type = threat.get('threat_type', '')
        restricted_types = policy.get('restricted_threat_types', [])
        if threat_type in restricted_types:
            violations.append({
                'violation_type': 'restricted_threat_type',
                'threat_type': threat_type,
            })

        return violations
