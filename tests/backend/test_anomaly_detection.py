"""Sprint 33 Phase 2: Anomaly Detection Tests

Tests for threat detection engine evaluating rules against audit logs.
Covers connection spikes, auth failures, region anomalies, and public buckets.
"""

import pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from detectors.anomaly_detector import AnomalyDetector, Threat


class TestAnomalyDetector:
    """Test AnomalyDetector threat detection"""

    @pytest.fixture
    def mock_tables(self):
        """Mock DynamoDB tables"""
        rules_table = MagicMock()
        audit_logs_table = MagicMock()
        return rules_table, audit_logs_table

    @pytest.fixture
    def detector(self, mock_tables):
        """Create detector with mocked tables"""
        rules_table, audit_logs_table = mock_tables
        with patch('guardian.detectors.anomaly_detector.boto3.resource') as mock_boto3:
            mock_boto3.return_value.Table.side_effect = [rules_table, audit_logs_table]
            detector = AnomalyDetector('test-rules', 'test-logs')
            detector.rules_table = rules_table
            detector.audit_logs_table = audit_logs_table
            return detector

    def test_detect_anomalies_empty_logs(self, detector):
        """Test detection with no logs"""
        detector.rules_table.query.return_value = {'Items': []}

        threats = detector.detect_anomalies('123456789')

        assert threats == []

    def test_detect_connection_spike(self, detector):
        """Test detecting connection spike anomaly"""
        rule = {
            'rule_id': 'spike-rule-1',
            'rule_type': 'connection_spike',
            'condition': json.dumps({
                'threshold': 10,
                'window_minutes': 5,
            }),
            'priority': 8,
            'enabled': True,
            'account_id': '123456789',
        }

        # Create 15 connection events, all within the last 5 minutes
        now = datetime.utcnow()
        connect_logs = [
            {
                'event_type': '$connect',
                'timestamp': (now - timedelta(seconds=i*10)).isoformat(),  # 10-second intervals
                'connection_id': f'conn-{i}',
                'account_id': '123456789',
            }
            for i in range(15)
        ]

        detector.rules_table.query.return_value = {'Items': [rule]}
        detector.audit_logs_table.query.return_value = {'Items': connect_logs}

        threats = detector.detect_anomalies('123456789', lookback_minutes=60)

        assert len(threats) == 1
        assert threats[0].rule_id == 'spike-rule-1'
        assert threats[0].severity == 8
        assert 'Connection spike' in threats[0].message

    def test_detect_auth_failure_rate(self, detector):
        """Test detecting high authentication failure rate"""
        rule = {
            'rule_id': 'auth-rule-1',
            'rule_type': 'auth_failure',
            'condition': json.dumps({
                'threshold': 5,
            }),
            'priority': 7,
            'enabled': True,
            'account_id': '111111111111',
        }

        # Create 6 auth failure events
        now = datetime.utcnow()
        auth_logs = [
            {
                'event_type': '$auth',
                'status': 'error',
                'timestamp': (now - timedelta(minutes=i)).isoformat(),
                'user_id': f'user-{i}',
                'account_id': '111111111111',
            }
            for i in range(6)
        ]

        detector.rules_table.query.return_value = {'Items': [rule]}
        detector.audit_logs_table.query.return_value = {'Items': auth_logs}

        threats = detector.detect_anomalies('111111111111', lookback_minutes=60)

        assert len(threats) == 1
        assert threats[0].rule_id == 'auth-rule-1'
        assert 'authentication failure' in threats[0].message.lower()

    def test_detect_unknown_region(self, detector):
        """Test detecting operations from unknown regions"""
        rule = {
            'rule_id': 'region-rule-1',
            'rule_type': 'unknown_region',
            'condition': json.dumps({
                'allowed_regions': ['ap-northeast-1', 'us-east-1'],
            }),
            'priority': 6,
            'enabled': True,
            'account_id': '123456789',
        }

        # Create logs with unknown region
        now = datetime.utcnow()
        region_logs = [
            {
                'event_type': 'ec2-run-instances',
                'region': 'eu-west-1',
                'timestamp': now.isoformat(),
                'account_id': '123456789',
            },
            {
                'event_type': 'describe-instances',
                'region': 'ap-southeast-1',
                'timestamp': (now - timedelta(minutes=1)).isoformat(),
                'account_id': '123456789',
            },
        ]

        detector.rules_table.query.return_value = {'Items': [rule]}
        detector.audit_logs_table.query.return_value = {'Items': region_logs}

        threats = detector.detect_anomalies('123456789', lookback_minutes=60)

        assert len(threats) >= 1
        assert threats[0].rule_id == 'region-rule-1'

    def test_detect_public_bucket(self, detector):
        """Test detecting public bucket creation"""
        rule = {
            'rule_id': 'bucket-rule-1',
            'rule_type': 'public_bucket',
            'condition': json.dumps({}),
            'priority': 9,
            'enabled': True,
            'account_id': '123456789',
        }

        # Create S3 public bucket event
        now = datetime.utcnow()
        bucket_logs = [
            {
                'event_type': 'CreateBucket',
                'service': 's3',
                'timestamp': now.isoformat(),
                'details': json.dumps({'acl': 'public-read'}),
                'account_id': '123456789',
            },
        ]

        detector.rules_table.query.return_value = {'Items': [rule]}
        detector.audit_logs_table.query.return_value = {'Items': bucket_logs}

        threats = detector.detect_anomalies('123456789', lookback_minutes=60)

        assert len(threats) == 1
        assert threats[0].severity == 9
        assert 'public bucket' in threats[0].message.lower()

    def test_multiple_threats_sorted_by_severity(self, detector):
        """Test multiple threats are sorted by severity"""
        rules = [
            {
                'rule_id': 'rule-1',
                'rule_type': 'connection_spike',
                'condition': json.dumps({'threshold': 5, 'window_minutes': 5}),
                'priority': 3,
                'enabled': True,
                'account_id': '123456789',
            },
            {
                'rule_id': 'rule-2',
                'rule_type': 'public_bucket',
                'condition': json.dumps({}),
                'priority': 9,
                'enabled': True,
                'account_id': '123456789',
            },
            {
                'rule_id': 'rule-3',
                'rule_type': 'auth_failure',
                'condition': json.dumps({'threshold': 3}),
                'priority': 6,
                'enabled': True,
                'account_id': '123456789',
            },
        ]

        now = datetime.utcnow()
        all_logs = [
            # Connection spike logs - 6 within 5 minute window (10-sec intervals)
            {'event_type': '$connect', 'timestamp': (now - timedelta(seconds=i*10)).isoformat(), 'account_id': '123456789'}
            for i in range(6)
        ] + [
            # Auth failure logs - 4 auth failures
            {'event_type': '$auth', 'status': 'error', 'timestamp': (now - timedelta(minutes=i)).isoformat(), 'account_id': '123456789'}
            for i in range(4)
        ] + [
            # Public bucket logs
            {
                'event_type': 'CreateBucket',
                'service': 's3',
                'timestamp': now.isoformat(),
                'details': json.dumps({'acl': 'public-read'}),
                'account_id': '123456789',
            },
        ]

        detector.rules_table.query.return_value = {'Items': rules}
        detector.audit_logs_table.query.return_value = {'Items': all_logs}

        threats = detector.detect_anomalies('123456789', lookback_minutes=60)

        # Should be sorted by severity (9, 6, 3)
        assert threats[0].severity == 9  # public bucket
        assert threats[1].severity == 6  # auth failure
        assert threats[2].severity == 3  # connection spike

    def test_no_threat_when_below_threshold(self, detector):
        """Test no threat when event count is below threshold"""
        rule = {
            'rule_id': 'spike-rule-1',
            'rule_type': 'connection_spike',
            'condition': json.dumps({
                'threshold': 10,
                'window_minutes': 5,
            }),
            'priority': 8,
            'enabled': True,
            'account_id': '123456789',
        }

        # Only 5 connection events (below threshold of 10)
        now = datetime.utcnow()
        connect_logs = [
            {
                'event_type': '$connect',
                'timestamp': (now - timedelta(minutes=i)).isoformat(),
                'connection_id': f'conn-{i}',
                'account_id': '123456789',
            }
            for i in range(5)
        ]

        detector.rules_table.query.return_value = {'Items': [rule]}
        detector.audit_logs_table.query.return_value = {'Items': connect_logs}

        threats = detector.detect_anomalies('123456789', lookback_minutes=60)

        assert len(threats) == 0

    def test_ignores_disabled_rules(self, detector):
        """Test that disabled rules are ignored"""
        rule = {
            'rule_id': 'spike-rule-1',
            'rule_type': 'connection_spike',
            'condition': json.dumps({'threshold': 5, 'window_minutes': 5}),
            'priority': 8,
            'enabled': False,  # Disabled
            'account_id': '123456789',
        }

        # Create many connection events
        now = datetime.utcnow()
        connect_logs = [
            {
                'event_type': '$connect',
                'timestamp': (now - timedelta(minutes=i)).isoformat(),
                'connection_id': f'conn-{i}',
                'account_id': '123456789',
            }
            for i in range(10)
        ]

        detector.rules_table.query.return_value = {'Items': []}  # No enabled rules
        detector.audit_logs_table.query.return_value = {'Items': connect_logs}

        threats = detector.detect_anomalies('123456789', lookback_minutes=60)

        assert len(threats) == 0
