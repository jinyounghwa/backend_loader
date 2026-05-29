"""Intelligent remediation engine."""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SmartRemediation:
    """Intelligent remediation with safety checks."""

    def __init__(self):
        """Initialize remediation engine."""
        self.remediation_history = []
        self.blocked_actions = []

    def suggest_remediation(
        self, finding: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Suggest safe remediation for a finding.
        
        Args:
            finding: Finding dict with type, severity, resource
            
        Returns:
            Remediation suggestion or None
        """
        finding_type = finding.get('type')
        resource = finding.get('resource')
        severity = finding.get('severity')

        # Don't suggest stopping production EC2 instances
        if finding_type == 'high_cpu' and 'prod' in resource.lower():
            return {
                'action': 'recommend_reserved_instance',
                'reason': 'Production instance - suggest RI purchase instead of stopping',
                'safe': True,
            }

        # For public buckets, block access instead of deleting
        if finding_type == 'public_bucket':
            return {
                'action': 'block_public_access',
                'reason': 'Block public access configuration',
                'safe': True,
            }

        # For high costs, suggest optimization
        if finding_type == 'cost_spike':
            return {
                'action': 'recommend_scale_down',
                'reason': 'Cost spike - recommend scaling down non-production resources',
                'safe': True,
            }

        return None

    def should_execute(
        self, remediation: Dict[str, Any], risk_level: str = 'LOW'
    ) -> bool:
        """Determine if remediation should be auto-executed.
        
        Args:
            remediation: Remediation suggestion
            risk_level: Risk level of the remediation
            
        Returns:
            True if safe to execute
        """
        # Never auto-execute high-risk actions
        if risk_level == 'HIGH':
            return False

        # Check if action is marked as safe
        if not remediation.get('safe', False):
            return False

        # Check if action is blocked
        if remediation.get('action') in self.blocked_actions:
            return False

        return True

    def track_remediation(
        self, remediation: Dict[str, Any], result: Dict[str, Any]
    ) -> bool:
        """Track remediation execution.
        
        Args:
            remediation: Remediation action
            result: Result of execution
            
        Returns:
            True if tracked successfully
        """
        try:
            record = {
                'action': remediation.get('action'),
                'timestamp': __import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc
                ).isoformat(),
                'result': result.get('status'),
                'details': result.get('details'),
            }
            self.remediation_history.append(record)
            logger.info(f"Tracked remediation: {record['action']}")
            return True
        except Exception as e:
            logger.error(f"Failed to track remediation: {e}")
            return False

    def get_remediation_success_rate(self) -> float:
        """Get success rate of remediations.
        
        Returns:
            Success rate (0-1)
        """
        if not self.remediation_history:
            return 0.0

        successful = sum(
            1 for r in self.remediation_history
            if r.get('result') == 'success'
        )
        return successful / len(self.remediation_history)
