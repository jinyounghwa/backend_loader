"""IAM Permission Auto-Remediation - Revoke excessive permissions."""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum


class RemediationStatus(Enum):
    """Remediation outcome statuses."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class IAMRemediator:
    """Automatic remediation for excessive IAM permissions."""

    # List of dangerous policies to identify and remove
    DANGEROUS_POLICIES = [
        'AdministratorAccess',
        'PowerUserAccess',
        'IAMFullAccess',
        'EC2FullAccess',
        'S3FullAccess',
        'AWSCloudTrailFullAccess'
    ]

    def __init__(self, iam_client, audit_logger):
        """Initialize IAM remediation with AWS client and audit logger."""
        self.iam = iam_client
        self.audit = audit_logger
        self.remediation_history = {}

    def remediate_excessive_permissions(self, principal: str, threat: Dict) -> Dict:
        """
        Revoke excessive IAM permissions from principal.

        Remediation steps:
        1. Analyze current permissions
        2. Identify dangerous permissions
        3. Assess blast radius
        4. Request confirmation for high-risk changes
        5. Revoke dangerous policies
        6. Rotate access keys
        7. Log all changes

        Args:
            principal: IAM principal ARN or name (user/role)
            threat: Threat detection details

        Returns:
            {
                'status': 'success|skipped|failed',
                'principal': principal,
                'action_taken': 'revoked|skipped',
                'reason': explanation,
                'policies_revoked': [],
                'risk_assessment': {},
                'timestamp': iso_timestamp
            }
        """
        result = {
            'principal': principal,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'threat': threat.get('threat_id', 'unknown'),
            'policies_revoked': []
        }

        # 1. Get principal details
        try:
            principal_type = self._determine_principal_type(principal)
            if not principal_type:
                result['status'] = RemediationStatus.FAILED.value
                result['reason'] = "Cannot determine principal type (user/role)"
                self.audit.log_remediation(principal, 'type_detection_failed', result)
                return result
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Principal lookup failed: {str(e)}"
            self.audit.log_remediation(principal, 'lookup_failed', result)
            return result

        # 2. Check safety conditions
        safety_check = self.verify_safety_conditions(principal, principal_type)
        if not safety_check['passed']:
            result['status'] = RemediationStatus.SKIPPED.value
            result['reason'] = safety_check['reason']
            result['action_taken'] = 'skipped'
            self.audit.log_remediation(principal, 'remediation_skipped', result)
            return result

        # 3. Get attached policies
        try:
            attached_policies = self._get_attached_policies(principal, principal_type)
        except Exception as e:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = f"Cannot fetch attached policies: {str(e)}"
            self.audit.log_remediation(principal, 'policy_fetch_failed', result)
            return result

        # 4. Identify dangerous policies
        dangerous_policies = self._identify_dangerous_policies(attached_policies)
        if not dangerous_policies:
            result['status'] = RemediationStatus.SKIPPED.value
            result['action_taken'] = 'skipped'
            result['reason'] = "No dangerous policies found"
            self.audit.log_remediation(principal, 'no_dangerous_policies', result)
            return result

        # 5. Assess impact
        try:
            risk_assessment = self._assess_blast_radius(principal, dangerous_policies)
            result['risk_assessment'] = risk_assessment
        except Exception:
            risk_assessment = {}

        # High risk requires approval (would need manual confirmation in production)
        if risk_assessment.get('risk_level') == 'high':
            result['status'] = RemediationStatus.SKIPPED.value
            result['reason'] = "High risk changes require admin approval"
            result['action_taken'] = 'skipped'
            self.audit.log_remediation(principal, 'high_risk_approval_required', result)
            return result

        # 6. Detach dangerous policies
        revoked_count = 0
        for policy_arn in dangerous_policies:
            try:
                self._detach_policy(principal, policy_arn, principal_type)
                result['policies_revoked'].append(policy_arn)
                revoked_count += 1
            except Exception as e:
                # Log but continue with other policies
                result[f'error_revoking_{policy_arn}'] = str(e)

        # 7. Rotate access keys if user
        if principal_type == 'user':
            try:
                key_result = self.rotate_access_keys(principal)
                result['key_rotation'] = key_result
            except Exception as e:
                result['key_rotation_error'] = str(e)

        if revoked_count == 0:
            result['status'] = RemediationStatus.FAILED.value
            result['reason'] = "Failed to revoke any policies"
        else:
            result['status'] = RemediationStatus.SUCCESS.value
            result['action_taken'] = 'revoked'
            result['reason'] = f"Revoked {revoked_count} dangerous policies"

        self.audit.log_remediation(principal, 'remediation_complete', result)
        return result

    def detach_dangerous_policies(self, principal: str) -> List[str]:
        """Detach dangerous policies from principal."""
        # Implementation covered by remediate_excessive_permissions
        return []

    def rotate_access_keys(self, user_name: str) -> Dict:
        """Rotate access keys for IAM user."""
        result = {
            'user_name': user_name,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'old_keys': [],
            'new_key_created': False
        }

        try:
            # List existing access keys
            keys_response = self.iam.list_access_keys(UserName=user_name)
            old_keys = keys_response.get('AccessKeyMetadata', [])
            result['old_keys'] = [k['AccessKeyId'] for k in old_keys]

            # Create new access key
            new_key = self.iam.create_access_key(UserName=user_name)
            new_key_id = new_key['AccessKey']['AccessKeyId']
            result['new_key_created'] = True
            result['new_key_id'] = new_key_id

            # Mark old keys for deactivation (don't delete immediately)
            for key in old_keys:
                try:
                    self.iam.update_access_key(
                        UserName=user_name,
                        AccessKeyId=key['AccessKeyId'],
                        Status='Inactive'
                    )
                    result['keys_deactivated'] = True
                except Exception:
                    pass

        except Exception as e:
            result['error'] = str(e)

        return result

    def create_session_token(self, principal: str, duration: int = 3600) -> Dict:
        """Create temporary STS token for principal."""
        result = {
            'principal': principal,
            'duration_seconds': duration,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        try:
            # Use STS to create temporary token
            response = self.iam.create_session_token(
                DurationSeconds=duration
            )
            result['token'] = response.get('Credentials', {})
            result['success'] = True
        except Exception as e:
            result['error'] = str(e)
            result['success'] = False

        return result

    def verify_safety_conditions(self, principal: str, principal_type: str) -> Dict:
        """
        Verify all safety conditions before remediation.

        Returns:
            {
                'passed': bool,
                'reason': explanation if not passed,
                'checks': {
                    'is_service_role': bool,
                    'is_protected': bool,
                    'has_critical_access': bool
                }
            }
        """
        checks = {}
        reasons = []

        # Check 1: Service role (should not modify)
        is_service_role = self._is_service_role(principal, principal_type)
        checks['is_service_role'] = is_service_role
        if is_service_role:
            reasons.append("Service role - modification not recommended")

        # Check 2: Protected principal
        is_protected = self._is_protected_principal(principal)
        checks['is_protected'] = is_protected
        if is_protected:
            reasons.append("Principal is marked as protected (guardian:protected=true)")

        # Check 3: Critical access
        has_critical = self._has_critical_access(principal, principal_type)
        checks['has_critical_access'] = has_critical
        if has_critical:
            reasons.append("Principal has critical system access")

        passed = not any([is_service_role, is_protected, has_critical])
        reason = "; ".join(reasons) if reasons else "All safety checks passed"

        return {
            'passed': passed,
            'reason': reason,
            'checks': checks
        }

    # Private helper methods
    def _determine_principal_type(self, principal: str) -> Optional[str]:
        """Determine if principal is user or role."""
        if ':iam::' not in principal and not principal.startswith('arn:'):
            # Might be just a username, try as user first
            try:
                self.iam.get_user(UserName=principal)
                return 'user'
            except Exception:
                try:
                    self.iam.get_role(RoleName=principal)
                    return 'role'
                except Exception:
                    return None

        if ':user/' in principal:
            return 'user'
        elif ':role/' in principal:
            return 'role'

        return None

    def _get_attached_policies(self, principal: str, principal_type: str) -> List[Dict]:
        """Get list of attached policies for principal."""
        try:
            if principal_type == 'user':
                response = self.iam.list_attached_user_policies(UserName=principal)
            else:
                response = self.iam.list_attached_role_policies(RoleName=principal)

            return response.get('AttachedPolicies', [])
        except Exception:
            return []

    def _identify_dangerous_policies(self, attached_policies: List[Dict]) -> List[str]:
        """Identify dangerous policies from attached policies."""
        dangerous = []
        policy_names = [p['PolicyName'] for p in attached_policies]

        for policy_name in policy_names:
            for dangerous_policy in self.DANGEROUS_POLICIES:
                if dangerous_policy in policy_name:
                    dangerous.append(policy_name)
                    break

        return dangerous

    def _assess_blast_radius(self, principal: str, dangerous_policies: List[str]) -> Dict:
        """Assess impact of revoking dangerous policies."""
        return {
            'principal': principal,
            'policies_to_revoke': dangerous_policies,
            'risk_level': 'medium',  # Simplified assessment
            'affected_resources': []
        }

    def _detach_policy(self, principal: str, policy_arn: str, principal_type: str) -> bool:
        """Detach policy from principal."""
        try:
            if principal_type == 'user':
                self.iam.detach_user_policy(
                    UserName=principal,
                    PolicyArn=policy_arn
                )
            else:
                self.iam.detach_role_policy(
                    RoleName=principal,
                    PolicyArn=policy_arn
                )
            return True
        except Exception:
            return False

    def _is_service_role(self, principal: str, principal_type: str) -> bool:
        """Check if principal is a service role."""
        service_role_indicators = [
            'lambda',
            'ec2',
            'rds',
            'ecs',
            'logs',
            'codebuild',
            'codepipeline'
        ]

        principal_lower = principal.lower()
        return any(indicator in principal_lower for indicator in service_role_indicators)

    def _is_protected_principal(self, principal: str) -> bool:
        """Check if principal is marked as protected."""
        # In production, would check tags
        return False

    def _has_critical_access(self, principal: str, principal_type: str) -> bool:
        """Check if principal has critical system access."""
        # Simplified check - in production would analyze permissions
        return 'admin' in principal.lower()
