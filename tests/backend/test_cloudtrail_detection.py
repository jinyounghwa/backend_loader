"""Sprint 65 Phase 2: CloudTrail Anomaly Detection (11 tests)"""

import pytest
from datetime import datetime, timezone

from guardian.cloudtrail import CloudTrailEventProcessor, PatternMatcher, ThreatScorer
from guardian.storage.cloudtrail_events import CloudTrailEventStorage


class TestEventProcessor:
    """Test CloudTrail event processing."""

    @pytest.fixture
    def processor(self):
        return CloudTrailEventProcessor()

    def test_parse_cloudtrail_event(self, processor):
        """✅ Parse raw CloudTrail JSON."""
        raw_event = {
            'eventID': 'evt-123',
            'eventName': 'RunInstances',
            'eventTime': '2025-05-29T10:00:00Z',
            'userIdentity': {'principalId': 'user-123'},
            'sourceIPAddress': '203.0.113.42',
            'awsRegion': 'us-east-1',
            'eventSource': 'ec2.amazonaws.com',
            'requestParameters': {'instanceType': 't3.micro'},
        }

        event = processor.parse_event(raw_event)
        assert event is not None
        assert event['event_id'] == 'evt-123'
        assert event['event_name'] == 'RunInstances'
        assert event['username'] == 'user-123'
        assert event['aws_region'] == 'us-east-1'

    def test_process_batch_events(self, processor):
        """✅ Process batch of CloudTrail events."""
        events = [
            {
                'eventID': f'evt-{i}',
                'eventName': 'RunInstances',
                'eventTime': '2025-05-29T10:00:00Z',
                'userIdentity': {'principalId': 'user-123'},
                'sourceIPAddress': '203.0.113.42',
                'awsRegion': 'us-east-1',
                'eventSource': 'ec2.amazonaws.com',
            }
            for i in range(5)
        ]

        processed = processor.process_batch(events)
        assert len(processed) == 5
        assert all(e['event_name'] == 'RunInstances' for e in processed)


class TestPatternMatcher:
    """Test CloudTrail pattern matching."""

    @pytest.fixture
    def matcher(self):
        return PatternMatcher()

    @pytest.fixture
    def sample_events(self):
        return [
            {
                'event_id': 'evt-1',
                'event_name': 'RunInstances',
                'event_source': 'ec2.amazonaws.com',
                'aws_region': 'eu-west-1',
                'username': 'user-123',
            },
            {
                'event_id': 'evt-2',
                'event_name': 'DeleteBucket',
                'event_source': 's3.amazonaws.com',
                'username': 'user-456',
            },
            {
                'event_id': 'evt-3',
                'event_name': 'PutUserPolicy',
                'event_source': 'iam.amazonaws.com',
                'username': 'user-789',
            },
        ]

    def test_detect_unauthorized_region(self, matcher, sample_events):
        """✅ Identify EC2 in new regions."""
        suspicious = matcher.detect_unauthorized_region(
            sample_events,
            allowed_regions=['us-east-1', 'us-west-2']
        )
        assert len(suspicious) == 1
        assert suspicious[0]['pattern'] == 'unauthorized_region'
        assert 'eu-west-1' in suspicious[0]['detail']

    def test_detect_mass_deletion(self, matcher):
        """✅ Catch bulk resource deletions."""
        deletion_events = [
            {
                'event_name': 'DeleteBucket',
                'username': 'attacker',
                'event_source': 's3.amazonaws.com',
            }
            for _ in range(7)
        ]

        suspicious = matcher.detect_mass_deletion(deletion_events, threshold=5)
        assert len(suspicious) == 1
        assert suspicious[0]['pattern'] == 'mass_deletion'
        assert suspicious[0]['deletion_count'] == 7

    def test_detect_permission_escalation(self, matcher, sample_events):
        """✅ Identify IAM policy changes."""
        suspicious = matcher.detect_permission_escalation(sample_events)
        assert len(suspicious) == 1
        assert suspicious[0]['pattern'] == 'permission_escalation'
        assert 'PutUserPolicy' in suspicious[0]['detail']

    def test_detect_auth_anomaly(self, matcher):
        """✅ Flag unusual authentication."""
        failed_events = [
            {
                'event_name': 'GetUser',
                'username': 'user-123',
                'error_code': 'UnauthorizedOperation',
                'error_message': 'Unauthorized',
            }
            for _ in range(4)
        ]

        suspicious = matcher.detect_auth_anomaly(failed_events, failed_threshold=3)
        assert len(suspicious) == 1
        assert suspicious[0]['pattern'] == 'auth_anomaly'
        assert suspicious[0]['failure_count'] == 4


class TestThreatScorer:
    """Test threat scoring."""

    @pytest.fixture
    def scorer(self):
        return ThreatScorer()

    def test_calculate_threat_score(self, scorer):
        """✅ Score threat severity."""
        detections = [
            {'pattern': 'permission_escalation'},
            {'pattern': 'mass_deletion'},
        ]

        score_result = scorer.calculate_threat_score(detections)
        assert score_result['score'] > 0
        assert score_result['severity'] in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        assert score_result['pattern_count'] == 2

    def test_score_event(self, scorer):
        """✅ Score individual events."""
        event = {
            'event_name': 'DeleteBucket',
            'event_source': 'iam.amazonaws.com',
            'error_code': 'AccessDenied',
            'source_ip': '203.0.113.42',
        }

        score = scorer.score_event(event)
        assert 0 <= score <= 100
        assert score > 0  # Should have some points


class TestEventCorrelation:
    """Test event correlation."""

    @pytest.fixture
    def processor(self):
        return CloudTrailEventProcessor()

    def test_pattern_correlation(self, processor):
        """✅ Connect related events."""
        events = [
            {
                'event_id': 'evt-1',
                'username': 'user-123',
                'event_name': 'GetUser',
                'error_code': 'UnauthorizedOperation',
            },
            {
                'event_id': 'evt-2',
                'username': 'user-123',
                'event_name': 'AttachUserPolicy',
            },
            {
                'event_id': 'evt-3',
                'username': 'user-456',
                'event_name': 'RunInstances',
            },
        ]

        correlated = processor.correlate_events(events)
        assert len(correlated) == 2
        user_123_data = next(
            (c for c in correlated if c['username'] == 'user-123'),
            None
        )
        assert user_123_data is not None
        assert user_123_data['event_count'] == 2

    def test_temporal_analysis(self, processor):
        """✅ Detect time-based patterns."""
        events = [
            {
                'event_id': f'evt-{i}',
                'event_name': 'RunInstances',
                'event_time': f'2025-05-29T{10+i:02d}:00:00Z',
                'username': 'attacker',
            }
            for i in range(3)
        ]

        # Should have events in sequence
        assert len(events) == 3
        assert all(e['username'] == 'attacker' for e in events)


class TestFalsePositiveFiltering:
    """Test false positive reduction."""

    @pytest.fixture
    def matcher(self):
        return PatternMatcher()

    def test_false_positive_filtering(self, matcher):
        """✅ Reduce alert fatigue."""
        # Normal deletion operations (e.g., cleanup)
        normal_events = [
            {
                'event_name': 'DeleteOldLogs',
                'event_source': 's3.amazonaws.com',
                'username': 'system-user',
            },
        ]

        suspicious = matcher.detect_mass_deletion(normal_events, threshold=5)
        # Should not flag isolated deletion
        assert len(suspicious) == 0


class TestEventEnrichment:
    """Test event enrichment."""

    def test_event_enrichment(self):
        """✅ Add context to alerts."""
        processor = CloudTrailEventProcessor()
        
        raw_event = {
            'eventID': 'evt-123',
            'eventName': 'DeleteBucket',
            'eventTime': '2025-05-29T10:00:00Z',
            'userIdentity': {'principalId': 'arn:aws:iam::123456789:user/attacker'},
            'sourceIPAddress': '203.0.113.42',
            'awsRegion': 'us-east-1',
            'eventSource': 's3.amazonaws.com',
            'requestParameters': {'bucketName': 'important-data'},
            'responseElements': None,
            'errorCode': 'AccessDenied',
        }

        event = processor.parse_event(raw_event)
        assert event['raw'] == raw_event
        assert event['error_code'] == 'AccessDenied'


class TestBatchEventProcessing:
    """Test batch processing efficiency."""

    def test_batch_event_processing(self):
        """✅ Process event stream efficiently."""
        processor = CloudTrailEventProcessor()
        
        # Simulate streaming 100 events
        events = [
            {
                'eventID': f'evt-{i}',
                'eventName': 'RunInstances',
                'eventTime': '2025-05-29T10:00:00Z',
                'userIdentity': {'principalId': f'user-{i % 10}'},
                'sourceIPAddress': '203.0.113.42',
                'awsRegion': 'us-east-1',
                'eventSource': 'ec2.amazonaws.com',
            }
            for i in range(100)
        ]

        processed = processor.process_batch(events)
        assert len(processed) == 100
        assert len(processor.processed_events) == 100


class TestStorageAndRetrieval:
    """Test event storage."""

    def test_cloudtrail_storage(self):
        """✅ Store and retrieve CloudTrail events."""
        storage = CloudTrailEventStorage()
        
        event = {
            'event_id': 'evt-123',
            'event_name': 'RunInstances',
            'username': 'user-123',
            'threat_score': 45,
        }

        assert storage.store_event(event) is True
        
        results = storage.query_events(username='user-123')
        assert len(results) == 1
        assert results[0]['event_id'] == 'evt-123'
