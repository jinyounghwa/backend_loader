"""Sprint 70 Phase 2: IAM Anomaly Detection & Permission Analysis (17 tests)"""

import pytest
from datetime import datetime


class TestIAMPolicyAnalyzer:
    """Test IAM policy analysis and risk scoring."""

    def test_analyze_admin_policy(self):
        """✅ Analyze AdministratorAccess policy risk."""
        from guardian.analyzers.iam_analyzer import IAMPolicyAnalyzer

        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': '*',
                    'Resource': '*'
                }
            ]
        }

        analyzer = IAMPolicyAnalyzer()
        risk = analyzer.analyze_policy(policy)

        assert risk['risk_score'] == 100
        assert risk['policy_type'] == 'ADMIN_ACCESS'
        assert risk['dangerous_actions'] == ['*']

    def test_analyze_poweruser_policy(self):
        """✅ Analyze PowerUserAccess policy risk."""
        from guardian.analyzers.iam_analyzer import IAMPolicyAnalyzer

        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': ['ec2:*', 's3:*', 'rds:*'],
                    'Resource': '*'
                }
            ]
        }

        analyzer = IAMPolicyAnalyzer()
        risk = analyzer.analyze_policy(policy)

        assert risk['risk_score'] >= 75
        assert risk['policy_type'] == 'POWER_USER'
        assert len(risk['dangerous_actions']) == 3

    def test_analyze_least_privilege_policy(self):
        """✅ Analyze least privilege policy."""
        from guardian.analyzers.iam_analyzer import IAMPolicyAnalyzer

        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': ['s3:GetObject'],
                    'Resource': 'arn:aws:s3:::my-bucket/*'
                }
            ]
        }

        analyzer = IAMPolicyAnalyzer()
        risk = analyzer.analyze_policy(policy)

        assert risk['risk_score'] < 20
        assert risk['policy_type'] == 'RESTRICTED'

    def test_detect_wildcard_actions(self):
        """✅ Detect wildcard in actions."""
        from guardian.analyzers.iam_analyzer import IAMPolicyAnalyzer

        policy = {
            'Statement': [
                {'Effect': 'Allow', 'Action': 'iam:*', 'Resource': '*'}
            ]
        }

        analyzer = IAMPolicyAnalyzer()
        risk = analyzer.analyze_policy(policy)

        assert risk['has_wildcard_action'] is True
        assert risk['risk_score'] > 85


class TestPrivilegeEscalationDetector:
    """Test privilege escalation detection."""

    def test_detect_attach_admin_policy(self):
        """✅ Detect AttachUserPolicy with admin access."""
        from guardian.analyzers.iam_analyzer import PrivilegeEscalationDetector

        event = {
            'eventName': 'AttachUserPolicy',
            'requestParameters': {
                'userName': 'attacker',
                'policyArn': 'arn:aws:iam::aws:policy/AdministratorAccess'
            }
        }

        detector = PrivilegeEscalationDetector()
        result = detector.detect_escalation(event)

        assert result['is_escalation'] is True
        assert result['escalation_type'] == 'direct_admin_attach'
        assert result['risk_score'] > 90

    def test_detect_create_policy_with_admin_access(self):
        """✅ Detect CreatePolicy with admin access."""
        from guardian.analyzers.iam_analyzer import PrivilegeEscalationDetector

        event = {
            'eventName': 'PutUserPolicy',
            'requestParameters': {
                'userName': 'attacker',
                'policyName': 'AdminPolicy',
                'policyDocument': '{"Statement":[{"Effect":"Allow","Action":"*","Resource":"*"}]}'
            }
        }

        detector = PrivilegeEscalationDetector()
        result = detector.detect_escalation(event)

        assert result['is_escalation'] is True
        assert 'admin' in result['escalation_type'].lower()

    def test_detect_access_key_creation(self):
        """✅ Detect CreateAccessKey on privileged user."""
        from guardian.analyzers.iam_analyzer import PrivilegeEscalationDetector

        event = {
            'eventName': 'CreateAccessKey',
            'requestParameters': {
                'userName': 'service-account-prod'
            }
        }

        detector = PrivilegeEscalationDetector()
        result = detector.detect_escalation(event)

        assert result['is_escalation'] is True
        assert result['escalation_type'] == 'access_key_creation'


class TestUnusedRoleDetector:
    """Test unused role detection."""

    def test_detect_role_with_no_usage(self):
        """✅ Detect role not used in 90 days."""
        from guardian.analyzers.iam_analyzer import UnusedRoleDetector
        from datetime import datetime, timedelta

        role = {
            'RoleName': 'old-lambda-role',
            'CreateDate': (datetime.now() - timedelta(days=180)).isoformat(),
            'LastUsed': (datetime.now() - timedelta(days=95)).isoformat()
        }

        detector = UnusedRoleDetector()
        result = detector.detect_unused(role)

        assert result['is_unused'] is True
        assert result['days_unused'] > 90

    def test_detect_role_in_use(self):
        """✅ Detect role actively used."""
        from guardian.analyzers.iam_analyzer import UnusedRoleDetector
        from datetime import datetime, timedelta

        role = {
            'RoleName': 'active-lambda-role',
            'CreateDate': (datetime.now() - timedelta(days=30)).isoformat(),
            'LastUsed': (datetime.now() - timedelta(hours=2)).isoformat()
        }

        detector = UnusedRoleDetector()
        result = detector.detect_unused(role)

        assert result['is_unused'] is False

    def test_detect_role_with_no_last_used(self):
        """✅ Handle role with no LastUsed timestamp."""
        from guardian.analyzers.iam_analyzer import UnusedRoleDetector
        from datetime import datetime, timedelta

        role = {
            'RoleName': 'new-role',
            'CreateDate': (datetime.now() - timedelta(days=5)).isoformat(),
            'LastUsed': None
        }

        detector = UnusedRoleDetector()
        result = detector.detect_unused(role)

        # New role created but never used
        assert result['is_unused'] is True


class TestCrossAccountAnalyzer:
    """Test cross-account permission analysis."""

    def test_detect_cross_account_trust(self):
        """✅ Detect cross-account assume role."""
        from guardian.analyzers.iam_analyzer import CrossAccountAnalyzer

        trust_policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {
                        'AWS': 'arn:aws:iam::999999999999:root'
                    },
                    'Action': 'sts:AssumeRole'
                }
            ]
        }

        analyzer = CrossAccountAnalyzer()
        result = analyzer.analyze_trust(trust_policy, current_account='123456789012')

        assert result['has_cross_account'] is True
        assert len(result['external_accounts']) > 0
        assert '999999999999' in result['external_accounts']

    def test_detect_trusted_service_principal(self):
        """✅ Detect service principal trust."""
        from guardian.analyzers.iam_analyzer import CrossAccountAnalyzer

        trust_policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {
                        'Service': 'lambda.amazonaws.com'
                    },
                    'Action': 'sts:AssumeRole'
                }
            ]
        }

        analyzer = CrossAccountAnalyzer()
        result = analyzer.analyze_trust(trust_policy, current_account='123456789012')

        assert result['has_cross_account'] is False
        assert result['is_service_principal'] is True

    def test_detect_wildcard_principal(self):
        """✅ Detect wildcard principal in trust."""
        from guardian.analyzers.iam_analyzer import CrossAccountAnalyzer

        trust_policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': '*',
                    'Action': 'sts:AssumeRole'
                }
            ]
        }

        analyzer = CrossAccountAnalyzer()
        result = analyzer.analyze_trust(trust_policy, current_account='123456789012')

        assert result['has_wildcard_principal'] is True
        assert result['risk_score'] > 85


class TestMinimumPrivilegeValidator:
    """Test minimum privilege principle validation."""

    def test_validate_least_privilege(self):
        """✅ Validate least privilege policy."""
        from guardian.validators.iam_validator import MinimumPrivilegeValidator

        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': ['s3:GetObject', 's3:ListBucket'],
                    'Resource': 'arn:aws:s3:::my-bucket/*'
                }
            ]
        }

        validator = MinimumPrivilegeValidator()
        result = validator.validate(policy)

        assert result['is_valid'] is True
        assert result['compliance_score'] > 80

    def test_detect_over_privileged_policy(self):
        """✅ Detect over-privileged policy."""
        from guardian.validators.iam_validator import MinimumPrivilegeValidator

        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': '*',
                    'Resource': '*'
                }
            ]
        }

        validator = MinimumPrivilegeValidator()
        result = validator.validate(policy)

        assert result['is_valid'] is False
        assert result['compliance_score'] < 20
        assert 'wildcard' in result['issues'][0].lower()

    def test_detect_missing_resource_restriction(self):
        """✅ Detect missing resource restriction."""
        from guardian.validators.iam_validator import MinimumPrivilegeValidator

        policy = {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 's3:DeleteBucket',
                    'Resource': '*'
                }
            ]
        }

        validator = MinimumPrivilegeValidator()
        result = validator.validate(policy)

        assert result['is_valid'] is False
        assert any('resource' in issue.lower() for issue in result['issues'])


class TestPolicyRiskScorer:
    """Test policy risk scoring."""

    def test_score_admin_access(self):
        """✅ Score AdministratorAccess as 100."""
        from guardian.validators.iam_validator import PolicyRiskScorer

        policy = {
            'Statement': [{'Effect': 'Allow', 'Action': '*', 'Resource': '*'}]
        }

        scorer = PolicyRiskScorer()
        score = scorer.score(policy)

        assert score == 100

    def test_score_poweruser_access(self):
        """✅ Score PowerUserAccess as 80."""
        from guardian.validators.iam_validator import PolicyRiskScorer

        policy = {
            'Statement': [
                {'Effect': 'Allow', 'Action': ['ec2:*', 's3:*'], 'Resource': '*'}
            ]
        }

        scorer = PolicyRiskScorer()
        score = scorer.score(policy)

        assert 70 <= score <= 90

    def test_score_restricted_access(self):
        """✅ Score restricted access as low."""
        from guardian.validators.iam_validator import PolicyRiskScorer

        policy = {
            'Statement': [
                {'Effect': 'Allow', 'Action': 's3:GetObject', 'Resource': 'arn:aws:s3:::bucket/*'}
            ]
        }

        scorer = PolicyRiskScorer()
        score = scorer.score(policy)

        assert score < 30

    def test_score_deny_policies(self):
        """✅ Score explicit deny policies correctly."""
        from guardian.validators.iam_validator import PolicyRiskScorer

        policy = {
            'Statement': [
                {'Effect': 'Allow', 'Action': '*', 'Resource': '*'},
                {'Effect': 'Deny', 'Action': 'iam:*', 'Resource': '*'}
            ]
        }

        scorer = PolicyRiskScorer()
        score = scorer.score(policy)

        # Deny doesn't reduce overall risk if Allow is admin
        assert score > 80
