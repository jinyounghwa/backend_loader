"""Decision Engine - Risk analysis and remediation strategy recommendations."""

from typing import Dict, Optional
from datetime import datetime


class RemediationDecisionEngine:
    """Make intelligent remediation decisions based on risk and confidence."""

    def __init__(self, audit_logger):
        """Initialize decision engine."""
        self.audit = audit_logger

    def analyze_threat_confidence(self, threat: Dict) -> Dict:
        """
        Analyze detection confidence for threat.

        Args:
            threat: Threat details

        Returns:
            {
                'threat_id': str,
                'confidence_score': float (0.0-1.0),
                'confidence_level': 'low|medium|high',
                'evidence_count': int,
                'evidence_quality': 'low|medium|high',
                'recommendation': 'monitor|investigate|remediate|isolate'
            }
        """
        confidence = 0.5  # Base confidence

        # Evidence count increases confidence
        evidence_count = len(threat.get('evidence', []))
        if evidence_count >= 3:
            confidence += 0.3
        elif evidence_count >= 2:
            confidence += 0.2
        elif evidence_count >= 1:
            confidence += 0.1

        # Multiple detection sources increases confidence
        detection_sources = len(set([e.get('source') for e in threat.get('evidence', [])]))
        if detection_sources >= 3:
            confidence += 0.15
        elif detection_sources >= 2:
            confidence += 0.1

        # High severity indicates better detection
        severity = threat.get('severity', 5)
        if severity >= 9:
            confidence += 0.05

        # Cap at 1.0
        confidence = min(1.0, confidence)

        # Determine confidence level
        if confidence >= 0.8:
            confidence_level = 'high'
            recommendation = 'remediate'
        elif confidence >= 0.6:
            confidence_level = 'medium'
            recommendation = 'investigate'
        else:
            confidence_level = 'low'
            recommendation = 'monitor'

        # High severity overrides low confidence
        if severity >= 8:
            recommendation = 'remediate'

        return {
            'threat_id': threat.get('threat_id'),
            'confidence_score': round(confidence, 2),
            'confidence_level': confidence_level,
            'evidence_count': evidence_count,
            'evidence_quality': self._assess_evidence_quality(threat.get('evidence', [])),
            'recommendation': recommendation,
            'timestamp': datetime.utcnow().isoformat()
        }

    def analyze_remediation_risk(self, threat: Dict, remediation_plan: Dict) -> Dict:
        """
        Analyze risk vs. benefit of proposed remediation.

        Args:
            threat: Threat details
            remediation_plan: Proposed remediation actions

        Returns:
            {
                'threat_id': str,
                'risk_score': float (0.0-1.0),
                'benefit_score': float (0.0-1.0),
                'net_score': float,  # benefit - risk
                'recommendation': 'auto_remediate|require_approval|escalate|defer'
            }
        """
        # Benefit: stopping the threat
        threat_severity = threat.get('severity', 5)
        benefit_score = threat_severity / 10.0

        # Risk: impact on business
        affected_resources = len(remediation_plan.get('steps', []))
        risk_score = 0.0

        # Add risk for each action type
        for step in remediation_plan.get('steps', []):
            step_type = step.get('type', '')

            if 'ec2_stop' in step_type:
                risk_score += 0.2  # Stopping instance impacts availability
            elif 'ec2_terminate' in step_type:
                risk_score += 0.4  # Terminating is higher risk
            elif 'iam_revoke' in step_type:
                risk_score += 0.1  # Revoking permissions is low-moderate risk
            elif 'network_isolate' in step_type:
                risk_score += 0.15  # Network isolation is moderate risk
            elif 's3_block_public' in step_type:
                risk_score += 0.05  # Blocking public access is low risk

        # Cap at 1.0
        risk_score = min(1.0, risk_score)

        # Calculate net score
        net_score = benefit_score - risk_score

        # Determine recommendation
        if threat_severity >= 9:
            recommendation = 'auto_remediate'  # Critical threats: immediate action
        elif net_score > 0.5:
            recommendation = 'auto_remediate'
        elif net_score > 0.2:
            recommendation = 'require_approval'
        elif net_score > 0:
            recommendation = 'escalate'
        else:
            recommendation = 'defer'

        return {
            'threat_id': threat.get('threat_id'),
            'risk_score': round(risk_score, 2),
            'benefit_score': round(benefit_score, 2),
            'net_score': round(net_score, 2),
            'affected_resources': affected_resources,
            'recommendation': recommendation,
            'timestamp': datetime.utcnow().isoformat()
        }

    def decide_remediation_strategy(self, threat: Dict, remediation_plan: Dict) -> Dict:
        """
        Make final decision on remediation strategy.

        Args:
            threat: Threat details
            remediation_plan: Proposed remediation

        Returns:
            {
                'threat_id': str,
                'decision': 'auto_remediate|require_approval|manual_review|defer',
                'reasoning': str,
                'confidence': float,
                'required_approvers': int
            }
        """
        confidence_analysis = self.analyze_threat_confidence(threat)
        risk_analysis = self.analyze_remediation_risk(threat, remediation_plan)

        confidence_score = confidence_analysis['confidence_score']
        risk_rec = risk_analysis['recommendation']

        # Combine confidence and risk analyses
        if confidence_score < 0.6:
            decision = 'manual_review'
            reasoning = f"Low confidence ({confidence_score:.0%}) - manual review required"
            required_approvers = 1
        elif risk_rec == 'auto_remediate':
            decision = 'auto_remediate'
            reasoning = f"High confidence ({confidence_score:.0%}) - net benefit {risk_analysis['net_score']:.2f}"
            required_approvers = 0
        elif risk_rec == 'require_approval':
            decision = 'require_approval'
            reasoning = f"Requires approval - risk {risk_analysis['risk_score']:.2f} vs benefit {risk_analysis['benefit_score']:.2f}"
            required_approvers = 1
        else:
            decision = 'manual_review'
            reasoning = f"Escalation required - net score {risk_analysis['net_score']:.2f}"
            required_approvers = 2

        return {
            'threat_id': threat.get('threat_id'),
            'decision': decision,
            'reasoning': reasoning,
            'confidence_score': confidence_score,
            'confidence_level': confidence_analysis['confidence_level'],
            'risk_score': risk_analysis['risk_score'],
            'required_approvers': required_approvers,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _assess_evidence_quality(self, evidence_list: list) -> str:
        """Assess quality of detection evidence."""
        if not evidence_list:
            return 'low'

        high_quality_sources = ['guardduty', 'securityhub', 'macie']
        medium_quality_sources = ['cloudtrail', 'vpc_flow_logs']

        sources = [e.get('source', '') for e in evidence_list]

        high_quality_count = sum(1 for s in sources if s in high_quality_sources)
        medium_quality_count = sum(1 for s in sources if s in medium_quality_sources)

        if high_quality_count >= 2:
            return 'high'
        elif high_quality_count >= 1 or medium_quality_count >= 2:
            return 'medium'
        else:
            return 'low'

    def recommend_escalation(self, threat: Dict, previous_failures: int = 0) -> Dict:
        """
        Recommend escalation based on threat severity and failure history.

        Args:
            threat: Threat details
            previous_failures: Number of previous remediation failures

        Returns:
            {
                'threat_id': str,
                'escalate': bool,
                'escalation_level': 'none|single|multi|critical_override',
                'reason': str
            }
        """
        severity = threat.get('severity', 5)
        escalation_level = 'none'
        escalate = False

        # Base escalation on severity
        if severity >= 9:
            escalation_level = 'critical_override'
            escalate = True
            reason = 'Critical threat - emergency override recommended'
        elif severity >= 8:
            escalation_level = 'multi'
            escalate = True
            reason = 'High-severity threat - multi-person approval required'
        elif previous_failures >= 2:
            escalation_level = 'multi'
            escalate = True
            reason = f"Previous failures ({previous_failures}) - escalate to multi-approval"
        elif severity >= 6 and previous_failures >= 1:
            escalation_level = 'single'
            escalate = True
            reason = 'Prior failure - require single approval'

        return {
            'threat_id': threat.get('threat_id'),
            'escalate': escalate,
            'escalation_level': escalation_level,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }
