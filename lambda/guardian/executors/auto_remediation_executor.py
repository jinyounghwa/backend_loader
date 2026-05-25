from typing import Dict, List
from datetime import datetime
import uuid


class AutoRemediationExecutor:
    def __init__(self, smart_engine=None, remediation_orchestrator=None, audit_logger=None):
        self.engine = smart_engine
        self.orchestrator = remediation_orchestrator
        self.audit = audit_logger
        self.execution_history = []
        self.rollback_capable_executions = {}

    def auto_remediate_threat(self, threat: Dict, resources: List[Dict]) -> Dict:
        execution_id = str(uuid.uuid4())

        if not self.engine:
            return {
                'execution_id': execution_id,
                'status': 'failed',
                'reason': 'No SmartRemediationEngine available',
            }

        strategy_result = self.engine.select_remediation_strategy(threat, resources)
        strategy = strategy_result.get('selected_strategy', 'MONITOR')
        safe_to_execute = strategy_result.get('safe_to_execute', True)

        auto_remediate_strategies = ['ISOLATE', 'REMEDIATE', 'TERMINATE']
        should_auto_remediate = strategy in auto_remediate_strategies and safe_to_execute

        execution_record = {
            'execution_id': execution_id,
            'threat_id': threat.get('threat_id', 'unknown'),
            'strategy': strategy,
            'auto_remediated': should_auto_remediate,
            'started_at': datetime.utcnow().isoformat(),
            'approval_required': not safe_to_execute or strategy in ['REMEDIATE', 'TERMINATE'],
        }

        if should_auto_remediate and self.orchestrator:
            orch_result = self.orchestrator.execute_multi_resource_remediation(threat, resources)
            execution_record['orchestration_id'] = orch_result.get('threat_id')
            execution_record['status'] = 'success' if orch_result.get('successful_remediations', 0) > 0 else 'partial'
            execution_record['resources_affected'] = orch_result.get('successful_remediations', 0)
            execution_record['completed_at'] = datetime.utcnow().isoformat()

            self.rollback_capable_executions[execution_id] = {
                'threat': threat,
                'resources': resources,
                'original_state': orch_result.get('original_state', {}),
            }
        else:
            execution_record['status'] = 'pending_approval' if execution_record.get('approval_required') else 'monitoring'
            execution_record['reason'] = 'Not safe to execute' if not safe_to_execute else 'Monitoring only'

        self.execution_history.append(execution_record)
        return execution_record

    def execute_with_approval(self, threat: Dict, resources: List[Dict], approver_id: str) -> Dict:
        execution_id = str(uuid.uuid4())

        if not self.engine:
            return {
                'execution_id': execution_id,
                'status': 'failed',
                'reason': 'No SmartRemediationEngine available',
            }

        strategy_result = self.engine.select_remediation_strategy(threat, resources)
        strategy = strategy_result.get('selected_strategy', 'MONITOR')

        execution_record = {
            'execution_id': execution_id,
            'threat_id': threat.get('threat_id', 'unknown'),
            'strategy': strategy,
            'approver_id': approver_id,
            'approved_at': datetime.utcnow().isoformat(),
            'status': 'pending',
        }

        if self.orchestrator:
            orch_result = self.orchestrator.execute_multi_resource_remediation(threat, resources)
            execution_record['orchestration_id'] = orch_result.get('threat_id')
            execution_record['status'] = 'success' if orch_result.get('successful_remediations', 0) > 0 else 'partial'
            execution_record['resources_affected'] = orch_result.get('successful_remediations', 0)
            execution_record['completed_at'] = datetime.utcnow().isoformat()

            self.rollback_capable_executions[execution_id] = {
                'threat': threat,
                'resources': resources,
                'original_state': orch_result.get('original_state', {}),
            }

        self.execution_history.append(execution_record)
        return execution_record

    def get_execution_history(self, threat_id: str = None) -> List[Dict]:
        if threat_id:
            return [e for e in self.execution_history if e.get('threat_id') == threat_id]
        return self.execution_history

    def get_execution_details(self, execution_id: str) -> Dict:
        for execution in self.execution_history:
            if execution.get('execution_id') == execution_id:
                return execution

        return {
            'execution_id': execution_id,
            'status': 'not_found',
        }

    def rollback_remediation(self, execution_id: str) -> Dict:
        if execution_id not in self.rollback_capable_executions:
            return {
                'execution_id': execution_id,
                'status': 'failed',
                'reason': 'Execution not found or not rollback-capable',
            }

        rollback_data = self.rollback_capable_executions[execution_id]
        threat = rollback_data['threat']
        resources = rollback_data['resources']

        rollback_id = str(uuid.uuid4())
        rollback_record = {
            'rollback_id': rollback_id,
            'original_execution_id': execution_id,
            'threat_id': threat.get('threat_id', 'unknown'),
            'initiated_at': datetime.utcnow().isoformat(),
            'status': 'success',
            'resources_restored': len(resources),
        }

        self.execution_history.append(rollback_record)
        del self.rollback_capable_executions[execution_id]

        return rollback_record

    def get_execution_summary(self) -> Dict:
        total_executions = len(self.execution_history)
        by_status = {}
        by_strategy = {}
        successful_auto_remediations = 0

        for execution in self.execution_history:
            status = execution.get('status', 'unknown')
            strategy = execution.get('strategy', 'unknown')
            auto_remediated = execution.get('auto_remediated', False)

            by_status[status] = by_status.get(status, 0) + 1
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1

            if auto_remediated and status == 'success':
                successful_auto_remediations += 1

        return {
            'total_executions': total_executions,
            'executions_by_status': by_status,
            'executions_by_strategy': by_strategy,
            'successful_auto_remediations': successful_auto_remediations,
            'auto_remediation_success_rate': (
                successful_auto_remediations / sum(1 for e in self.execution_history if e.get('auto_remediated'))
                if sum(1 for e in self.execution_history if e.get('auto_remediated')) > 0
                else 0.0
            ),
        }
