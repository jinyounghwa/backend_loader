"""Smart Remediation Engine - Impact assessment, cost estimation, and risk scoring."""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class RiskLevel(Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SmartRemediationEngine:
    """Intelligent remediation decision making with impact analysis."""

    # Threat severity to remediation strategy mapping
    THREAT_STRATEGY_MAP = {
        1: {'action': 'monitor', 'auto_remediate': False, 'approval': 'none'},
        2: {'action': 'monitor', 'auto_remediate': False, 'approval': 'none'},
        3: {'action': 'investigate', 'auto_remediate': False, 'approval': 'none'},
        4: {'action': 'investigate', 'auto_remediate': False, 'approval': 'single'},
        5: {'action': 'remediate', 'auto_remediate': True, 'approval': 'single'},
        6: {'action': 'remediate', 'auto_remediate': True, 'approval': 'single'},
        7: {'action': 'isolate', 'auto_remediate': True, 'approval': 'multi'},
        8: {'action': 'isolate', 'auto_remediate': True, 'approval': 'multi'},
        9: {'action': 'isolate', 'auto_remediate': True, 'approval': 'multi'},
        10: {'action': 'emergency', 'auto_remediate': True, 'approval': 'multi'}
    }

    # Cost estimates for remediation actions
    COST_ESTIMATE_MAP = {
        'ec2_stop': 0,  # Stopping instance is free
        'ec2_terminate': 0,  # Terminating instance is free
        'network_isolate': 0,  # SG modification is free
        's3_block_public': 0,  # Public access block is free
        'iam_revoke': 0  # Revoking policies is free
    }

    def __init__(self, audit_logger):
        """Initialize smart remediation engine."""
        self.audit = audit_logger
        self.analysis_history = {}

    def get_remediation_strategy(self, threat: Dict) -> Dict:
        """
        Determine optimal remediation strategy based on threat severity.

        Args:
            threat: Threat details with severity (1-10)

        Returns:
            {
                'threat_id': str,
                'severity': int,
                'recommended_action': str,
                'auto_remediate': bool,
                'approval_required': str,  # none|single|multi
                'confidence_score': float,
                'reasoning': str
            }
        """
        severity = threat.get('severity', 5)
        threat_id = threat.get('threat_id', 'unknown')

        # Get strategy from mapping
        strategy = self.THREAT_STRATEGY_MAP.get(severity, {
            'action': 'investigate',
            'auto_remediate': False,
            'approval': 'single'
        })

        # Calculate confidence score (based on threat type and evidence)
        confidence = self._calculate_confidence_score(threat)

        result = {
            'threat_id': threat_id,
            'severity': severity,
            'recommended_action': strategy['action'],
            'auto_remediate': strategy['auto_remediate'],
            'approval_required': strategy['approval'],
            'confidence_score': confidence,
            'reasoning': self._generate_reasoning(severity, strategy, confidence),
            'timestamp': datetime.utcnow().isoformat()
        }

        return result

    def assess_remediation_impact(self, threat: Dict, remediation_plan: Dict) -> Dict:
        """
        Assess potential impact of remediation actions.

        Args:
            threat: Threat details
            remediation_plan: Planned remediation steps

        Returns:
            {
                'impact_assessment': {
                    'system_availability': risk_level,
                    'user_impact': risk_level,
                    'data_loss_risk': risk_level,
                    'overall_risk': risk_level
                },
                'affected_resources': {count},
                'estimated_downtime_minutes': int,
                'risk_level': str
            }
        """
        impact = {
            'threat_id': threat.get('threat_id'),
            'impact_assessment': {
                'system_availability': RiskLevel.LOW.value,
                'user_impact': RiskLevel.LOW.value,
                'data_loss_risk': RiskLevel.LOW.value,
                'overall_risk': RiskLevel.LOW.value
            },
            'affected_resources': 0,
            'estimated_downtime_minutes': 0,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Analyze each remediation step
        steps = remediation_plan.get('steps', [])
        impact['affected_resources'] = len(steps)

        for step in steps:
            if step.get('type') == 'ec2_stop':
                # Stopping an instance may impact users
                impact['impact_assessment']['system_availability'] = RiskLevel.MEDIUM.value
                impact['impact_assessment']['user_impact'] = RiskLevel.MEDIUM.value
                impact['estimated_downtime_minutes'] = 5

            elif step.get('type') == 'network_isolate':
                # Isolating network has moderate impact
                impact['impact_assessment']['system_availability'] = RiskLevel.MEDIUM.value
                impact['estimated_downtime_minutes'] = 2

            elif step.get('type') == 's3_block_public':
                # Blocking public access is low risk
                if not impact['impact_assessment']['user_impact'] == RiskLevel.MEDIUM.value:
                    impact['impact_assessment']['user_impact'] = RiskLevel.LOW.value

            elif step.get('type') == 'iam_revoke':
                # Revoking permissions is low risk if not excessive
                if not impact['impact_assessment']['system_availability'] == RiskLevel.MEDIUM.value:
                    impact['impact_assessment']['system_availability'] = RiskLevel.LOW.value

        # Determine overall risk
        impact['impact_assessment']['overall_risk'] = impact['impact_assessment']['system_availability']
        impact['risk_level'] = impact['impact_assessment']['overall_risk']

        return impact

    def estimate_cost_impact(self, remediation_plan: Dict) -> Dict:
        """
        Estimate cost savings from remediation.

        Args:
            remediation_plan: Planned remediation steps

        Returns:
            {
                'actions': [{'action': str, 'estimated_cost': float}],
                'total_cost': float,
                'savings_prevented': float,  # Estimated cost of incident if not remediated
                'roi': float
            }
        """
        cost_breakdown = {
            'actions': [],
            'total_cost': 0,
            'savings_prevented': 0,
            'roi': 0,
            'timestamp': datetime.utcnow().isoformat()
        }

        steps = remediation_plan.get('steps', [])

        for step in steps:
            action_type = step.get('type', 'unknown')
            estimated_cost = self.COST_ESTIMATE_MAP.get(action_type, 0)

            cost_breakdown['actions'].append({
                'action': action_type,
                'estimated_cost': estimated_cost
            })
            cost_breakdown['total_cost'] += estimated_cost

        # Calculate prevented costs (typical incident costs)
        incident_cost = 5000  # Base incident cost in dollars
        if len(steps) > 0:
            cost_breakdown['savings_prevented'] = incident_cost * len(steps)

        # Calculate ROI
        if cost_breakdown['total_cost'] > 0:
            cost_breakdown['roi'] = cost_breakdown['savings_prevented'] / cost_breakdown['total_cost']
        else:
            cost_breakdown['roi'] = float('inf')  # Free remediation with savings

        return cost_breakdown

    def correlate_resources_by_threat(self, threat_id: str, resources: Dict) -> Dict:
        """
        Identify and correlate all resources affected by same threat.

        Args:
            threat_id: Threat identifier
            resources: Dict of resource types and IDs

        Returns:
            {
                'threat_id': str,
                'correlated_resources': {
                    'instances': [...],
                    'principals': [...],
                    'buckets': [...]
                },
                'correlation_confidence': float,
                'recommended_actions': [...]
            }
        """
        correlation = {
            'threat_id': threat_id,
            'correlated_resources': resources,
            'correlation_confidence': 0.95,  # High confidence correlation
            'recommended_actions': [],
            'timestamp': datetime.utcnow().isoformat()
        }

        # Generate recommendations based on resources
        if resources.get('instances'):
            correlation['recommended_actions'].append('isolate_instances')
        if resources.get('principals'):
            correlation['recommended_actions'].append('revoke_permissions')
        if resources.get('buckets'):
            correlation['recommended_actions'].append('block_public_access')

        return correlation

    def _calculate_confidence_score(self, threat: Dict) -> float:
        """Calculate threat detection confidence score (0.0 to 1.0)."""
        # Base confidence from threat severity
        severity = threat.get('severity', 5)
        confidence = severity / 10.0

        # Adjust by threat type certainty
        if threat.get('source') == 'guardduty':
            confidence = min(1.0, confidence + 0.1)
        elif threat.get('source') == 'cloudtrail':
            confidence = min(1.0, confidence + 0.05)

        # Multiple evidence increases confidence
        evidence_count = len(threat.get('evidence', []))
        if evidence_count > 1:
            confidence = min(1.0, confidence + 0.1)

        return round(confidence, 2)

    def _generate_reasoning(self, severity: int, strategy: Dict, confidence: float) -> str:
        """Generate human-readable reasoning for remediation strategy."""
        if confidence < 0.5:
            return f"Low confidence ({confidence:.0%}) - {strategy['action']} recommended with manual review"
        elif confidence >= 0.9:
            return f"High confidence ({confidence:.0%}) - {strategy['action']} can proceed automatically"
        else:
            return f"Medium confidence ({confidence:.0%}) - {strategy['action']} with single approval"
