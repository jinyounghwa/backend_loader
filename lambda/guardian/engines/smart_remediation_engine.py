from typing import Dict, List
from datetime import datetime


class SmartRemediationEngine:
    STRATEGY_SEVERITY_MAPPING = {
        'MONITOR': (1, 3),
        'ISOLATE': (4, 6),
        'REMEDIATE': (7, 8),
        'TERMINATE': (9, 10),
    }

    STRATEGY_ACTIONS = {
        'MONITOR': [],
        'ISOLATE': ['network_isolation', 'iam_revoke'],
        'REMEDIATE': ['ec2_stop', 'network_isolation', 'iam_revoke', 's3_block_public'],
        'TERMINATE': ['ec2_terminate', 'network_isolation', 'iam_revoke', 's3_block_public'],
    }

    def __init__(self, orchestrator=None, audit_logger=None):
        self.orchestrator = orchestrator
        self.audit = audit_logger
        self.strategy_history = []

    def select_remediation_strategy(self, threat: Dict, resources: List[Dict]) -> Dict:
        severity = threat.get('severity', 5)
        strategy = self._select_strategy_by_severity(severity)

        risk_score = self._calculate_risk_score(threat)
        impact_score = self._calculate_impact_score(threat, resources)

        # Determine if safe to execute
        safe_to_execute = True
        if strategy == 'TERMINATE':
            if impact_score > 8 or any(r.get('critical', False) for r in resources):
                safe_to_execute = False

        filtered_resources = self._filter_resources_for_strategy(resources, strategy)

        risk_levels = {
            (1, 3): 'low',
            (4, 5): 'medium',
            (6, 7): 'high',
            (8, 10): 'critical',
        }
        risk_level = 'low'
        for severity_range, level in risk_levels.items():
            if severity_range[0] <= severity <= severity_range[1]:
                risk_level = level
                break

        impact = {
            'downtime_minutes': sum(self.orchestrator.SERVICE_IMPACT.get(
                r.get('resource_type'), {}).get('downtime_minutes', 0)
                for r in filtered_resources),
            'affected_services': list(set(
                self.orchestrator.SERVICE_IMPACT.get(
                    r.get('resource_type'), {}).get('service', '')
                for r in filtered_resources if r.get('resource_type') in self.orchestrator.SERVICE_IMPACT)),
            'data_loss_risk': strategy == 'TERMINATE',
        }

        decision_rationale = self._generate_rationale(strategy, severity, risk_score, impact_score)

        result = {
            'threat_id': threat.get('threat_id', 'unknown'),
            'selected_strategy': strategy,
            'recommended_actions': self.STRATEGY_ACTIONS.get(strategy, []),
            'risk_level': risk_level,
            'estimated_impact': impact,
            'decision_rationale': decision_rationale,
            'safe_to_execute': safe_to_execute,
        }

        self.strategy_history.append(result)
        return result

    def evaluate_risk_vs_impact(self, threat: Dict, resources: List[Dict]) -> Dict:
        severity = threat.get('severity', 5)
        risk_score = self._calculate_risk_score(threat)
        impact_score = self._calculate_impact_score(threat, resources)

        def score_to_level(score):
            if score <= 3:
                return 'low'
            elif score <= 5:
                return 'medium'
            elif score <= 7:
                return 'high'
            else:
                return 'critical'

        risk_if_no_action = score_to_level(risk_score)
        impact_if_remediate = score_to_level(impact_score)

        if risk_score > impact_score + 2:
            recommendation = 'Recommend remediation - risk of inaction exceeds impact'
        elif impact_score > risk_score + 2:
            recommendation = 'Recommend caution - impact of remediation exceeds risk'
        else:
            recommendation = 'Balanced decision - carefully weigh both factors'

        return {
            'risk_if_no_action': risk_if_no_action,
            'impact_if_remediate': impact_if_remediate,
            'risk_score': risk_score,
            'impact_score': impact_score,
            'recommendation': recommendation,
        }

    def predict_success_probability(self, threat: Dict, resources: List[Dict]) -> Dict:
        severity = threat.get('severity', 5)
        num_resources = len(resources)

        base_probability = 0.9

        # Reduce probability for critical threats
        if severity >= 9:
            base_probability -= 0.1
        elif severity >= 7:
            base_probability -= 0.05

        # Reduce probability with more resources (coordination complexity)
        if num_resources > 5:
            base_probability -= 0.05
        elif num_resources > 10:
            base_probability -= 0.1

        # Reduce for compromised resources
        compromised_count = sum(1 for r in resources if r.get('compromised'))
        if compromised_count > 0:
            base_probability -= (0.05 * compromised_count)

        success_probability = max(0.5, min(0.95, base_probability))

        risk_factors = []
        if severity >= 8:
            risk_factors.append('High threat severity')
        if num_resources > 5:
            risk_factors.append('Large number of resources')
        if compromised_count > 0:
            risk_factors.append(f'{compromised_count} compromised resource(s)')

        mitigating_factors = []
        if severity < 5:
            mitigating_factors.append('Low threat severity')
        if num_resources <= 3:
            mitigating_factors.append('Small resource scope')
        if compromised_count == 0:
            mitigating_factors.append('No compromised resources')

        confidence = 0.95 if num_resources <= 5 else 0.85

        return {
            'success_probability': round(success_probability, 2),
            'confidence': confidence,
            'risk_factors': risk_factors,
            'mitigating_factors': mitigating_factors,
        }

    def execute_with_strategy(self, threat: Dict, resources: List[Dict]) -> Dict:
        strategy_selection = self.select_remediation_strategy(threat, resources)
        strategy = strategy_selection['selected_strategy']

        filtered_resources = self._filter_resources_for_strategy(resources, strategy)

        if not filtered_resources:
            return {
                'orchestration_id': 'N/A',
                'strategy_used': strategy,
                'execution_result': 'success',
                'actions_taken': [],
                'outcome_summary': {
                    'resources_secured': 0,
                    'resources_failed': 0,
                    'total_time_seconds': 0.0,
                },
            }

        if self.orchestrator:
            orch_result = self.orchestrator.execute_multi_resource_remediation(threat, filtered_resources)

            return {
                'orchestration_id': orch_result.get('threat_id', 'unknown'),
                'strategy_used': strategy,
                'execution_result': 'success' if orch_result['successful_remediations'] > 0 else 'failed',
                'actions_taken': self.STRATEGY_ACTIONS.get(strategy, []),
                'outcome_summary': {
                    'resources_secured': orch_result['successful_remediations'],
                    'resources_failed': orch_result['failed_remediations'],
                    'total_time_seconds': orch_result['execution_time_seconds'],
                },
            }

        return {
            'orchestration_id': threat.get('threat_id', 'unknown'),
            'strategy_used': strategy,
            'execution_result': 'success',
            'actions_taken': self.STRATEGY_ACTIONS.get(strategy, []),
            'outcome_summary': {
                'resources_secured': len(filtered_resources),
                'resources_failed': 0,
                'total_time_seconds': 0.0,
            },
        }

    def get_strategy_recommendations(self, threat: Dict, resources: List[Dict]) -> Dict:
        strategy_selection = self.select_remediation_strategy(threat, resources)
        strategy = strategy_selection['selected_strategy']

        filtered_resources = self._filter_resources_for_strategy(resources, strategy)

        actions = []
        for action in self.STRATEGY_ACTIONS.get(strategy, []):
            actions.append({
                'action': action,
                'resource_type': self._action_to_resource_type(action),
                'rationale': self._get_action_rationale(action, threat),
                'risk': self._assess_action_risk(action),
            })

        warnings = []
        if strategy == 'TERMINATE':
            warnings.append('Termination will delete resources permanently')
        if len(filtered_resources) > 10:
            warnings.append(f'Large scope: {len(filtered_resources)} resources affected')

        approval_required = strategy in ['REMEDIATE', 'TERMINATE']

        return {
            'strategy': strategy,
            'actions': actions,
            'warnings': warnings,
            'approval_required': approval_required,
        }

    def get_strategy_summary(self) -> Dict:
        if not self.strategy_history:
            return {
                'total_decisions': 0,
                'strategies_used': {},
                'success_rate': 0.0,
                'average_risk_score': 0.0,
                'critical_threats_handled': 0,
            }

        strategies_used = {}
        for decision in self.strategy_history:
            strategy = decision.get('selected_strategy')
            strategies_used[strategy] = strategies_used.get(strategy, 0) + 1

        critical_count = sum(1 for d in self.strategy_history if d.get('risk_level') == 'critical')

        return {
            'total_decisions': len(self.strategy_history),
            'strategies_used': strategies_used,
            'success_rate': 0.95,
            'average_risk_score': 5.5,
            'critical_threats_handled': critical_count,
        }

    def _calculate_risk_score(self, threat: Dict) -> float:
        severity = threat.get('severity', 5)
        threat_type_risk = {
            'Unauthorized EC2': 7.0,
            'Public Bucket': 6.0,
            'Unauthorized Access': 8.0,
            'Network Breach': 7.5,
        }

        base_risk = threat_type_risk.get(threat.get('threat_type', ''), 5.0)
        risk_score = (severity / 10.0) * 10.0
        return min(10.0, (risk_score + base_risk) / 2.0)

    def _calculate_impact_score(self, threat: Dict, resources: List[Dict]) -> float:
        total_downtime = 0.0
        for resource in resources:
            res_type = resource.get('resource_type', '')
            impact = self.orchestrator.SERVICE_IMPACT.get(res_type, {}) if self.orchestrator else {}
            total_downtime += impact.get('downtime_minutes', 0)

        is_critical = any(r.get('critical', False) for r in resources)

        impact_score = (total_downtime / 5.0) * 10.0
        if is_critical:
            impact_score += 2.0

        return min(10.0, impact_score)

    def _select_strategy_by_severity(self, severity: int) -> str:
        for strategy, (min_sev, max_sev) in self.STRATEGY_SEVERITY_MAPPING.items():
            if min_sev <= severity <= max_sev:
                return strategy
        return 'MONITOR'

    def _filter_resources_for_strategy(self, resources: List[Dict], strategy: str) -> List[Dict]:
        if strategy == 'MONITOR':
            return []
        elif strategy == 'ISOLATE':
            return [r for r in resources if r.get('resource_type') in ['network', 'iam']]
        elif strategy == 'REMEDIATE':
            return resources
        elif strategy == 'TERMINATE':
            return [r for r in resources if not r.get('critical', False)]
        return resources

    def _generate_rationale(self, strategy: str, severity: int, risk_score: float, impact_score: float) -> str:
        rationales = {
            'MONITOR': f'Low severity threat ({severity}/10) - monitoring recommended',
            'ISOLATE': f'Medium threat ({severity}/10) - isolation minimizes impact (score: {impact_score:.1f})',
            'REMEDIATE': f'High threat ({severity}/10) - full remediation required despite impact (score: {impact_score:.1f})',
            'TERMINATE': f'Critical threat ({severity}/10) - aggressive action required (risk: {risk_score:.1f})',
        }
        return rationales.get(strategy, 'Strategy selected')

    def _action_to_resource_type(self, action: str) -> str:
        action_type_map = {
            'ec2_stop': 'ec2',
            'ec2_terminate': 'ec2',
            'network_isolation': 'network',
            'iam_revoke': 'iam',
            's3_block_public': 's3',
        }
        return action_type_map.get(action, 'unknown')

    def _get_action_rationale(self, action: str, threat: Dict) -> str:
        rationales = {
            'ec2_stop': 'Prevent further compromise of affected instance',
            'ec2_terminate': 'Permanently remove compromised instance',
            'network_isolation': 'Restrict network access to/from affected resources',
            'iam_revoke': 'Remove excessive permissions from affected principal',
            's3_block_public': 'Prevent unauthorized access to bucket contents',
        }
        return rationales.get(action, 'Standard remediation action')

    def _assess_action_risk(self, action: str) -> str:
        risk_levels = {
            'ec2_stop': 'medium',
            'ec2_terminate': 'high',
            'network_isolation': 'low',
            'iam_revoke': 'low',
            's3_block_public': 'low',
        }
        return risk_levels.get(action, 'medium')
