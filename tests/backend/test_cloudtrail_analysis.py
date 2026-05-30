"""Sprint 70 Phase 1: CloudTrail Real-time Log Analysis (17 tests)"""

import pytest
from datetime import datetime


class TestCloudTrailEventParser:
    """Test CloudTrail event parsing and normalization."""

    def test_parse_ec2_launch_event(self):
        """✅ Parse EC2 launch event."""
        from guardian.integrations.cloudtrail_analyzer import CloudTrailEventParser

        event = {
            'eventName': 'RunInstances',
            'eventTime': '2026-05-30T10:15:00Z',
            'sourceIPAddress': '203.0.113.45',
            'userAgent': 'console.amazonaws.com',
            'requestParameters': {
                'instanceType': 't3.large',
                'minCount': 1,
                'maxCount': 1
            },
            'responseElements': {
                'instancesSet': {
                    'items': [{'instanceId': 'i-abc123'}]
                }
            }
        }

        parser = CloudTrailEventParser()
        normalized = parser.parse(event)

        assert normalized['event_type'] == 'EC2_LAUNCH'
        assert normalized['instance_id'] == 'i-abc123'
        assert normalized['timestamp'] is not None

    def test_parse_iam_policy_update(self):
        """✅ Parse IAM policy update event."""
        from guardian.integrations.cloudtrail_analyzer import CloudTrailEventParser

        event = {
            'eventName': 'PutUserPolicy',
            'eventTime': '2026-05-30T11:20:00Z',
            'requestParameters': {
                'userName': 'john',
                'policyName': 'AdminPolicy'
            }
        }

        parser = CloudTrailEventParser()
        normalized = parser.parse(event)

        assert normalized['event_type'] == 'IAM_POLICY_UPDATE'
        assert normalized['resource'] == 'john'

    def test_parse_s3_deletion_event(self):
        """✅ Parse S3 bucket deletion event."""
        from guardian.integrations.cloudtrail_analyzer import CloudTrailEventParser

        event = {
            'eventName': 'DeleteBucket',
            'eventTime': '2026-05-30T12:00:00Z',
            'requestParameters': {
                'bucketName': 'my-data-bucket'
            }
        }

        parser = CloudTrailEventParser()
        normalized = parser.parse(event)

        assert normalized['event_type'] == 'S3_DELETION'
        assert normalized['resource'] == 'my-data-bucket'


class TestAnomalousActivityDetector:
    """Test anomalous API activity detection."""

    def test_detect_unusual_api_frequency(self):
        """✅ Detect unusually high API call frequency."""
        from guardian.integrations.cloudtrail_analyzer import AnomalousActivityDetector

        # Create 15 events in same minute (threshold is 10)
        events = [
            {'eventName': 'DescribeInstances', 'timestamp': datetime(2026, 5, 30, 10, 0, i)}
            for i in range(15)
        ]

        detector = AnomalousActivityDetector()
        result = detector.detect_frequency_anomaly(events)

        assert result['is_anomalous'] is True
        assert result['anomaly_score'] > 70

    def test_detect_failed_auth_attempts(self):
        """✅ Detect multiple failed authentication attempts."""
        from guardian.integrations.cloudtrail_analyzer import AnomalousActivityDetector

        events = [
            {'eventName': 'ConsoleLogin', 'errorCode': 'UnauthorizedOperation', 'sourceIPAddress': '203.0.113.50'},
            {'eventName': 'ConsoleLogin', 'errorCode': 'UnauthorizedOperation', 'sourceIPAddress': '203.0.113.50'},
            {'eventName': 'ConsoleLogin', 'errorCode': 'UnauthorizedOperation', 'sourceIPAddress': '203.0.113.50'},
        ]

        detector = AnomalousActivityDetector()
        result = detector.detect_auth_anomaly(events)

        assert result['is_anomalous'] is True
        assert result['anomaly_type'] == 'brute_force_attempt'

    def test_detect_unauthorized_region_access(self):
        """✅ Detect API calls from unauthorized regions."""
        from guardian.integrations.cloudtrail_analyzer import AnomalousActivityDetector

        event = {
            'eventName': 'CreateSecurityGroup',
            'sourceIPAddress': '203.0.113.100',
            'awsRegion': 'eu-west-1'  # Unexpected region
        }

        detector = AnomalousActivityDetector()
        result = detector.detect_region_anomaly(event, authorized_regions=['us-east-1', 'us-west-2'])

        assert result['is_anomalous'] is True
        assert result['anomaly_score'] > 60

    def test_detect_permission_escalation_pattern(self):
        """✅ Detect permission escalation patterns."""
        from guardian.integrations.cloudtrail_analyzer import AnomalousActivityDetector

        events = [
            {'eventName': 'AttachUserPolicy', 'requestParameters': {'policyArn': 'arn:aws:iam::aws:policy/AdministratorAccess'}},
            {'eventName': 'CreateAccessKey', 'requestParameters': {'userName': 'attacker'}},
        ]

        detector = AnomalousActivityDetector()
        result = detector.detect_escalation_pattern(events)

        assert result['is_anomalous'] is True
        assert 'escalation' in result['pattern_type'].lower()


class TestPermissionChangeTracker:
    """Test IAM permission change tracking."""

    def test_track_policy_attachment(self):
        """✅ Track IAM policy attachment."""
        from guardian.integrations.cloudtrail_analyzer import PermissionChangeTracker

        event = {
            'eventName': 'AttachUserPolicy',
            'eventTime': '2026-05-30T14:30:00Z',
            'requestParameters': {
                'userName': 'alice',
                'policyArn': 'arn:aws:iam::aws:policy/PowerUserAccess'
            }
        }

        tracker = PermissionChangeTracker()
        change = tracker.track_change(event)

        assert change['change_type'] == 'policy_attached'
        assert change['principal'] == 'alice'
        assert change['policy'] == 'PowerUserAccess'

    def test_track_role_assumption(self):
        """✅ Track assume role events."""
        from guardian.integrations.cloudtrail_analyzer import PermissionChangeTracker

        event = {
            'eventName': 'AssumeRole',
            'eventTime': '2026-05-30T15:00:00Z',
            'requestParameters': {
                'roleArn': 'arn:aws:iam::123456789012:role/LambdaExecutionRole'
            }
        }

        tracker = PermissionChangeTracker()
        change = tracker.track_change(event)

        assert change['change_type'] == 'assume_role'
        assert 'LambdaExecutionRole' in change['role']

    def test_track_permission_removal(self):
        """✅ Track permission removal."""
        from guardian.integrations.cloudtrail_analyzer import PermissionChangeTracker

        event = {
            'eventName': 'DetachUserPolicy',
            'eventTime': '2026-05-30T15:30:00Z',
            'requestParameters': {
                'userName': 'bob',
                'policyArn': 'arn:aws:iam::aws:policy/AdministratorAccess'
            }
        }

        tracker = PermissionChangeTracker()
        change = tracker.track_change(event)

        assert change['change_type'] == 'policy_detached'
        assert change['principal'] == 'bob'


class TestResourceDeleteMonitor:
    """Test resource deletion monitoring."""

    def test_detect_ec2_termination(self):
        """✅ Detect EC2 instance termination."""
        from guardian.integrations.cloudtrail_analyzer import ResourceDeleteMonitor

        event = {
            'eventName': 'TerminateInstances',
            'eventTime': '2026-05-30T16:00:00Z',
            'requestParameters': {
                'instancesSet': {
                    'items': [{'instanceId': 'i-important-prod'}]
                }
            }
        }

        monitor = ResourceDeleteMonitor()
        deletion = monitor.detect_deletion(event)

        assert deletion['is_deletion'] is True
        assert deletion['resource_type'] == 'EC2_INSTANCE'
        assert 'i-important-prod' in deletion['resource_id']

    def test_detect_s3_bucket_deletion(self):
        """✅ Detect S3 bucket deletion."""
        from guardian.integrations.cloudtrail_analyzer import ResourceDeleteMonitor

        event = {
            'eventName': 'DeleteBucket',
            'eventTime': '2026-05-30T16:30:00Z',
            'requestParameters': {
                'bucketName': 'customer-data-backup'
            }
        }

        monitor = ResourceDeleteMonitor()
        deletion = monitor.detect_deletion(event)

        assert deletion['is_deletion'] is True
        assert deletion['resource_type'] == 'S3_BUCKET'
        assert deletion['resource_id'] == 'customer-data-backup'
        assert deletion['risk_score'] > 80

    def test_detect_database_deletion(self):
        """✅ Detect RDS database deletion."""
        from guardian.integrations.cloudtrail_analyzer import ResourceDeleteMonitor

        event = {
            'eventName': 'DeleteDBInstance',
            'eventTime': '2026-05-30T17:00:00Z',
            'requestParameters': {
                'dBInstanceIdentifier': 'production-db'
            }
        }

        monitor = ResourceDeleteMonitor()
        deletion = monitor.detect_deletion(event)

        assert deletion['is_deletion'] is True
        assert deletion['resource_type'] == 'RDS_DATABASE'
        assert deletion['risk_score'] >= 85


class TestCloudTrailPipeline:
    """Test end-to-end CloudTrail pipeline."""

    def test_pipeline_end_to_end(self):
        """✅ Process CloudTrail event through full pipeline."""
        from guardian.pipelines.cloudtrail_pipeline import CloudTrailPipeline

        event = {
            'eventName': 'RunInstances',
            'eventTime': '2026-05-30T18:00:00Z',
            'sourceIPAddress': '203.0.113.45',
            'requestParameters': {
                'instanceType': 't3.large',
                'minCount': 1,
                'maxCount': 1
            },
            'responseElements': {
                'instancesSet': {
                    'items': [{'instanceId': 'i-new-instance'}]
                }
            }
        }

        pipeline = CloudTrailPipeline()
        result = pipeline.process(event)

        assert result['processed'] is True
        assert 'anomaly_score' in result
        assert 'alerts' in result

    def test_pipeline_anomaly_scoring(self):
        """✅ Pipeline calculates anomaly scores (0-100)."""
        from guardian.pipelines.cloudtrail_pipeline import CloudTrailPipeline

        events = [
            {
                'eventName': 'DescribeInstances',
                'eventTime': '2026-05-30T18:30:00Z',
                'sourceIPAddress': '203.0.113.200'
            }
        ] * 20  # Unusual frequency

        pipeline = CloudTrailPipeline()
        for event in events:
            result = pipeline.process(event)

        # Check if anomaly detected on repeated calls
        assert result['anomaly_score'] > 0

    def test_pipeline_alert_generation(self):
        """✅ Pipeline generates alerts for critical events."""
        from guardian.pipelines.cloudtrail_pipeline import CloudTrailPipeline

        event = {
            'eventName': 'DeleteBucket',
            'eventTime': '2026-05-30T19:00:00Z',
            'requestParameters': {
                'bucketName': 'critical-backup'
            }
        }

        pipeline = CloudTrailPipeline()
        result = pipeline.process(event)

        assert len(result['alerts']) > 0
        assert result['anomaly_score'] > 70


class TestCloudTrailPerformance:
    """Test CloudTrail analysis performance."""

    def test_event_parsing_latency(self):
        """✅ Event parsing < 50ms."""
        from guardian.integrations.cloudtrail_analyzer import CloudTrailEventParser
        import time

        event = {
            'eventName': 'RunInstances',
            'eventTime': '2026-05-30T20:00:00Z',
            'requestParameters': {'instanceType': 't3.large'},
            'responseElements': {'instancesSet': {'items': [{'instanceId': 'i-test'}]}}
        }

        parser = CloudTrailEventParser()
        start = time.time()
        for _ in range(100):
            parser.parse(event)
        elapsed = (time.time() - start) * 10  # Convert to ms per event

        assert elapsed < 50

    def test_anomaly_detection_latency(self):
        """✅ Anomaly detection < 100ms for batch."""
        from guardian.integrations.cloudtrail_analyzer import AnomalousActivityDetector
        import time

        detector = AnomalousActivityDetector()
        events = [
            {'eventName': f'Event{i}', 'timestamp': datetime(2026, 5, 30, 10, i % 60)}
            for i in range(50)
        ]

        start = time.time()
        detector.detect_frequency_anomaly(events)
        elapsed = (time.time() - start) * 1000

        assert elapsed < 100
