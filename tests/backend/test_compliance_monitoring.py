"""Sprint 42 Phase 3: Compliance & Policy Monitoring"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
import sys
from pathlib import Path
from guardian.monitors.compliance_monitor import ComplianceMonitor
from guardian.validators.policy_validator import PolicyValidator


# ==========================================
# Test Group 1: Encryption & Logging (2 tests)
# ==========================================

def test_compliance_monitor_initialization():
    """Test compliance monitor initialization"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    cloudtrail_client = MagicMock()

    monitor = ComplianceMonitor(ec2_client, s3_client, cloudtrail_client)

    assert monitor is not None
    assert monitor.ec2 is not None
    assert monitor.s3 is not None


def test_check_encryption_status():
    """Test checking encryption status of resources"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    cloudtrail_client = MagicMock()

    monitor = ComplianceMonitor(ec2_client, s3_client, cloudtrail_client)

    # Mock EBS encryption check
    ec2_client.describe_volumes.return_value = {
        'Volumes': [
            {'VolumeId': 'vol-001', 'Encrypted': True},
            {'VolumeId': 'vol-002', 'Encrypted': False}
        ]
    }

    result = monitor.check_encryption_status('EBS')

    assert result is not None
    assert isinstance(result, dict)


def test_verify_logging_enabled():
    """Test verifying logging is enabled for resources"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    cloudtrail_client = MagicMock()

    monitor = ComplianceMonitor(ec2_client, s3_client, cloudtrail_client)

    # Mock CloudTrail logging check
    cloudtrail_client.describe_trails.return_value = {
        'trailList': [
            {'TrailName': 'trail-1', 'IsLogging': True},
            {'TrailName': 'trail-2', 'IsLogging': False}
        ]
    }

    result = monitor.verify_logging_enabled('acc-001')

    assert result is not None


# ==========================================
# Test Group 2: IAM Policy Validation (2 tests)
# ==========================================

def test_policy_validator_initialization():
    """Test policy validator initialization"""
    iam_client = MagicMock()

    validator = PolicyValidator(iam_client)

    assert validator is not None
    assert validator.iam is not None


def test_validate_iam_policy():
    """Test validating IAM policy for compliance"""
    iam_client = MagicMock()

    validator = PolicyValidator(iam_client)

    policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': 's3:GetObject',
                'Resource': 'arn:aws:s3:::specific-bucket/*'
            }
        ]
    }

    result = validator.validate_iam_policy(policy)

    assert result is not None
    assert isinstance(result, dict)


# ==========================================
# Test Group 3: Compliance Score (3 tests)
# ==========================================

def test_generate_compliance_report():
    """Test generating compliance report for account"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    cloudtrail_client = MagicMock()

    monitor = ComplianceMonitor(ec2_client, s3_client, cloudtrail_client)

    report = monitor.generate_compliance_report('acc-001')

    assert report is not None
    assert isinstance(report, dict)


def test_calculate_compliance_score():
    """Test calculating overall compliance score"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    cloudtrail_client = MagicMock()

    monitor = ComplianceMonitor(ec2_client, s3_client, cloudtrail_client)

    checks = {
        'encryption': True,
        'logging': True,
        'mfa_enforcement': False,
        'public_resources': False,
        'iam_policy': True
    }

    score = monitor.calculate_compliance_score(checks)

    assert score is not None
    assert isinstance(score, (int, float))
    assert 0 <= score <= 100


def test_check_mfa_enforcement():
    """Test checking MFA enforcement for IAM users"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    cloudtrail_client = MagicMock()

    monitor = ComplianceMonitor(ec2_client, s3_client, cloudtrail_client)

    result = monitor.check_mfa_enforcement('acc-001')

    assert result is not None


# ==========================================
# Test Group 4: Policy Remediation (3 tests)
# ==========================================

def test_detect_overly_permissive_policies():
    """Test detecting overly permissive IAM policies"""
    iam_client = MagicMock()

    validator = PolicyValidator(iam_client)

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

    result = validator.detect_overly_permissive_policies([policy])

    assert result is not None


def test_check_least_privilege():
    """Test checking if policies follow least privilege principle"""
    iam_client = MagicMock()

    validator = PolicyValidator(iam_client)

    policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': 's3:*',
                'Resource': 'arn:aws:s3:::bucket/*'
            }
        ]
    }

    is_least_privilege = validator.check_least_privilege(policy)

    assert is_least_privilege is not None


def test_suggest_policy_improvements():
    """Test suggesting policy improvements"""
    iam_client = MagicMock()

    validator = PolicyValidator(iam_client)

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

    suggestions = validator.suggest_policy_improvements(policy)

    assert suggestions is not None
    assert isinstance(suggestions, list)


def test_scan_public_resources():
    """Test scanning for publicly accessible resources"""
    ec2_client = MagicMock()
    s3_client = MagicMock()
    cloudtrail_client = MagicMock()

    monitor = ComplianceMonitor(ec2_client, s3_client, cloudtrail_client)

    result = monitor.scan_public_resources('acc-001')

    assert result is not None
