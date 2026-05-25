import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List


class RemediationOrchestrator:
    RESOURCE_TYPE_ORDER = ['ec2', 'network', 's3', 'iam']

    THREAT_TYPE_MAPPING = {
        'Unauthorized EC2': 'ec2',
        'Public Bucket': 's3',
        'Unauthorized Access': 'iam',
        'Network Breach': 'network',
    }

    SERVICE_IMPACT = {
        'ec2': {'downtime_minutes': 2.0, 'service': 'Compute'},
        'network': {'downtime_minutes': 1.5, 'service': 'Connectivity'},
        's3': {'downtime_minutes': 0.0, 'service': 'Storage'},
        'iam': {'downtime_minutes': 0.0, 'service': 'Authorization'},
    }

    def __init__(self, audit_logger=None, max_workers: int = 3):
        self.audit = audit_logger
        self.max_workers = max_workers
        self.execution_history = []

    def execute_multi_resource_remediation(self, threat: Dict, resources: List[Dict]) -> Dict:
        start_time = time.time()
        remediation_chain = []

        sorted_resources = self._sort_resources_by_type(resources)

        for resource in sorted_resources:
            if self._threat_affects_resource(threat, resource):
                result = self._remediate_resource(threat, resource)
                remediation_chain.append(result)

        execution_time = time.time() - start_time

        successful = sum(1 for r in remediation_chain if r['status'] == 'success')
        failed = len(remediation_chain) - successful

        result = {
            'threat_id': threat.get('threat_id', threat.get('id', 'unknown')),
            'total_resources': len(remediation_chain),
            'successful_remediations': successful,
            'failed_remediations': failed,
            'execution_time_seconds': execution_time,
            'remediation_chain': remediation_chain,
        }

        self.execution_history.append(result)
        return result

    def execute_parallel_remediation(self, threat: Dict, resources: List[Dict]) -> Dict:
        start_time = time.time()
        remediation_chain = []

        self._group_resources_by_type(resources)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for resource in resources:
                if self._threat_affects_resource(threat, resource):
                    future = executor.submit(self._remediate_resource, threat, resource)
                    futures[future] = resource

            for future in futures:
                result = future.result()
                remediation_chain.append(result)

        execution_time = time.time() - start_time

        successful = sum(1 for r in remediation_chain if r['status'] == 'success')
        failed = len(remediation_chain) - successful

        result = {
            'threat_id': threat.get('threat_id', threat.get('id', 'unknown')),
            'total_resources': len(remediation_chain),
            'successful_remediations': successful,
            'failed_remediations': failed,
            'execution_time_seconds': execution_time,
            'remediation_chain': remediation_chain,
        }

        self.execution_history.append(result)
        return result

    def correlate_resources_by_threat(self, threat: Dict, all_resources: List[Dict]) -> List[Dict]:
        threat_type = threat.get('threat_type', '')
        target_resource_type = self.THREAT_TYPE_MAPPING.get(threat_type)

        if not target_resource_type:
            return []

        account_id = threat.get('account_id')

        correlated = []
        for resource in all_resources:
            if resource.get('resource_type') == target_resource_type:
                if account_id is None or resource.get('account_id') == account_id:
                    correlated.append(resource)

        return correlated

    def assess_remediation_impact(self, threat: Dict, resources: List[Dict]) -> Dict:
        resource_types = set()
        total_downtime = 0.0
        affected_services = []

        for resource in resources:
            if self._threat_affects_resource(threat, resource):
                res_type = resource.get('resource_type', '')
                resource_types.add(res_type)

                if res_type in self.SERVICE_IMPACT:
                    impact = self.SERVICE_IMPACT[res_type]
                    total_downtime += impact['downtime_minutes']
                    affected_services.append(impact['service'])

        affected_services = list(dict.fromkeys(affected_services))
        affected_services.sort()

        severity = threat.get('severity', 5)

        if severity >= 8:
            customer_impact = 'Critical - immediate remediation required'
            recommendations = ['Proceed immediately', 'Notify customer of impact']
        elif severity >= 6:
            customer_impact = 'High - remediation recommended'
            recommendations = ['Schedule remediation', 'Monitor after remediation']
        else:
            customer_impact = 'Medium - consider impact before remediation'
            recommendations = ['Review impact assessment', 'Schedule during maintenance window']

        return {
            'estimated_downtime_minutes': total_downtime,
            'affected_services': affected_services,
            'customer_impact': customer_impact,
            'recommendations': recommendations,
            'safe_to_proceed': severity >= 6,
        }

    def estimate_remediation_cost(self, threat: Dict, resources: List[Dict]) -> Dict:
        estimated_cost = 0.0
        cost_breakdown = {}

        severity = threat.get('severity', 5)

        for resource in resources:
            res_type = resource.get('resource_type', '')

            if res_type == 'ec2':
                if severity >= 9:
                    action = f"terminate_{resource.get('resource_id', 'unknown')}"
                    cost = 0.05
                    cost_breakdown[action] = cost
                    estimated_cost += cost

        if estimated_cost > 0:
            cost_vs_risk = 'Cost justified by high severity threat'
        elif severity >= 6:
            cost_vs_risk = 'No immediate cost, but threat requires remediation'
        else:
            cost_vs_risk = 'Low cost, medium threat severity'

        return {
            'estimated_cost_usd': round(estimated_cost, 2),
            'cost_breakdown': cost_breakdown,
            'cost_vs_risk': cost_vs_risk,
        }

    def get_orchestration_summary(self) -> Dict:
        if not self.execution_history:
            return {
                'total_executions': 0,
                'total_resources_remediated': 0,
                'successful_remediations': 0,
                'failed_remediations': 0,
                'average_execution_time_seconds': 0.0,
                'success_rate': 0.0,
            }

        total_executions = len(self.execution_history)
        total_resources = sum(h['total_resources'] for h in self.execution_history)
        successful = sum(h['successful_remediations'] for h in self.execution_history)
        failed = sum(h['failed_remediations'] for h in self.execution_history)
        avg_time = sum(h['execution_time_seconds'] for h in self.execution_history) / total_executions

        success_rate = successful / total_resources if total_resources > 0 else 0.0

        return {
            'total_executions': total_executions,
            'total_resources_remediated': total_resources,
            'successful_remediations': successful,
            'failed_remediations': failed,
            'average_execution_time_seconds': round(avg_time, 3),
            'success_rate': round(success_rate, 2),
        }

    def _remediate_resource(self, threat: Dict, resource: Dict) -> Dict:
        res_type = resource.get('resource_type', '')
        severity = threat.get('severity', 5)

        if res_type == 'ec2':
            if severity >= 9:
                action = 'terminate'
            else:
                action = 'stop'
        elif res_type == 'network':
            action = 'isolate'
        elif res_type == 's3':
            action = 'block_public'
        elif res_type == 'iam':
            action = 'revoke_permissions'
        else:
            action = 'unknown'

        is_compromised = resource.get('compromised', False)
        status = 'failed' if is_compromised else 'success'

        return {
            'resource_id': resource.get('resource_id', 'unknown'),
            'resource_type': res_type,
            'action': action,
            'status': status,
            'timestamp': datetime.utcnow().isoformat(),
        }

    def _threat_affects_resource(self, threat: Dict, resource: Dict) -> bool:
        threat_type = threat.get('threat_type', '')
        resource_type = resource.get('resource_type', '')

        target_type = self.THREAT_TYPE_MAPPING.get(threat_type)

        return target_type == resource_type

    def _sort_resources_by_type(self, resources: List[Dict]) -> List[Dict]:
        sorted_resources = []
        for res_type in self.RESOURCE_TYPE_ORDER:
            for resource in resources:
                if resource.get('resource_type') == res_type:
                    sorted_resources.append(resource)
        return sorted_resources

    def _group_resources_by_type(self, resources: List[Dict]) -> Dict[str, List[Dict]]:
        grouped = {}
        for resource in resources:
            res_type = resource.get('resource_type', '')
            if res_type not in grouped:
                grouped[res_type] = []
            grouped[res_type].append(resource)
        return grouped
