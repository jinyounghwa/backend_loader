from typing import Dict, List
from datetime import datetime, timezone
import uuid


class MultiAccountRemediationOrchestrator:
    def __init__(self, remediation_executors=None, policy_manager=None, audit_logger=None):
        self.executors = remediation_executors or {}
        self.policy_manager = policy_manager
        self.audit = audit_logger
        self.cross_account_executions = []

    def register_account_executor(self, account_id: str, executor) -> None:
        self.executors[account_id] = executor

    def remediate_threat_across_accounts(self, threat: Dict, resource_map: Dict) -> Dict:
        execution_id = str(uuid.uuid4())
        results = {}

        for account_id, resources in resource_map.items():
            if account_id not in self.executors:
                results[account_id] = {
                    'status': 'failed',
                    'reason': 'executor_not_registered'
                }
                continue

            executor = self.executors[account_id]
            try:
                result = executor.auto_remediate_threat(threat, resources)
                results[account_id] = {
                    'status': 'success',
                    'execution_id': result.get('execution_id'),
                    'strategy': result.get('strategy'),
                }
            except Exception as e:
                results[account_id] = {
                    'status': 'failed',
                    'reason': str(e)
                }

        execution_record = {
            'execution_id': execution_id,
            'threat_id': threat.get('threat_id'),
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'accounts_targeted': len(resource_map),
            'results': results,
        }

        self.cross_account_executions.append(execution_record)
        return execution_record

    def apply_account_policy(self, threat: Dict, account_id: str, policy: Dict) -> Dict:
        if not self.policy_manager:
            return {'status': 'policy_manager_not_configured'}

        evaluation = self.policy_manager.evaluate_threat_against_policy(threat, account_id)

        return {
            'account_id': account_id,
            'threat_id': threat.get('threat_id'),
            'policy_evaluation': evaluation,
            'allowed_strategies': evaluation.get('allowed_strategies', []),
            'restricted_strategies': evaluation.get('restricted_strategies', []),
            'approval_required': evaluation.get('approval_required', False),
        }

    def coordinate_remediation_sequence(self, threats: List[Dict], dependency_map: Dict) -> Dict:
        execution_order = []
        processed = set()

        for threat_id in dependency_map.keys():
            if threat_id in processed:
                continue

            dependencies = dependency_map.get(threat_id, [])
            for dep in dependencies:
                if dep not in processed:
                    execution_order.append(dep)
                    processed.add(dep)

            execution_order.append(threat_id)
            processed.add(threat_id)

        return {
            'execution_sequence': execution_order,
            'total_threats': len(threats),
            'ordered_threats': len(execution_order),
        }

    def get_cross_account_execution_status(self, execution_id: str) -> Dict:
        for execution in self.cross_account_executions:
            if execution.get('execution_id') == execution_id:
                return execution

        return {'status': 'execution_not_found'}

    def get_multi_account_summary(self) -> Dict:
        if not self.cross_account_executions:
            return {
                'total_executions': 0,
                'successful_accounts': 0,
                'failed_accounts': 0,
                'success_rate': 0.0,
            }

        total_accounts = 0
        successful_accounts = 0

        for execution in self.cross_account_executions:
            results = execution.get('results', {})
            for account_id, result in results.items():
                total_accounts += 1
                if result.get('status') == 'success':
                    successful_accounts += 1

        success_rate = (successful_accounts / total_accounts * 100.0) if total_accounts > 0 else 0.0

        return {
            'total_executions': len(self.cross_account_executions),
            'total_accounts_targeted': total_accounts,
            'successful_accounts': successful_accounts,
            'failed_accounts': total_accounts - successful_accounts,
            'success_rate': success_rate,
        }
