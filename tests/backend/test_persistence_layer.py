"""Tests for Phase 1 Persistence Layer (EventStore, DecisionStore, FeedbackStore, S3Archive)."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ==========================================
# EventStore Tests
# ==========================================


class TestEventStore:
    """Test EventStore functionality."""

    @pytest.fixture
    def event_store_mock(self):
        """Create a mock EventStore for testing."""
        from guardian.storage.event_store import EventStore

        with patch("guardian.storage.event_store.AWSClientProvider"):
            store = EventStore(table_name="test-events")
            store.table = MagicMock()
            return store

    def test_save_single_event(self, event_store_mock):
        """Test saving a single event to EventStore."""
        event_data = {
            "event_id": "evt-001",
            "timestamp": "2026-05-27T10:00:00Z",
            "account_id": "123456789",
            "event_type": "RunInstances",
            "severity": "HIGH",
            "region": "us-east-1",
            "principal_id": "AIDAI12345678901234",
        }

        result = event_store_mock.save_event(event_data)

        assert result is True
        event_store_mock.table.put_item.assert_called_once()
        call_args = event_store_mock.table.put_item.call_args
        item = call_args[1]["Item"]
        assert item["event_id"] == "evt-001"
        assert item["account_id"] == "123456789"

    def test_save_events_batch(self, event_store_mock):
        """Test saving multiple events in batch."""
        events = [
            {
                "event_id": "evt-001",
                "timestamp": "2026-05-27T10:00:00Z",
                "account_id": "123456789",
                "event_type": "RunInstances",
            },
            {
                "event_id": "evt-002",
                "timestamp": "2026-05-27T10:01:00Z",
                "account_id": "123456789",
                "event_type": "PutObject",
            },
        ]

        batch_writer = MagicMock()
        event_store_mock.table.batch_writer.return_value.__enter__.return_value = batch_writer

        result = event_store_mock.save_events_batch(events)

        assert result == 2
        assert batch_writer.put_item.call_count == 2

    def test_get_event(self, event_store_mock):
        """Test retrieving a single event by ID."""
        event_store_mock.table.get_item.return_value = {
            "Item": {
                "event_id": "evt-001",
                "timestamp": "2026-05-27T10:00:00Z",
                "account_id": "123456789",
                "raw_event": json.dumps({"test": "data"}),
            }
        }

        result = event_store_mock.get_event("evt-001")

        assert result is not None
        assert result["event_id"] == "evt-001"
        assert result["raw_event"] == {"test": "data"}
        event_store_mock.table.get_item.assert_called_once()

    def test_query_events_by_account(self, event_store_mock):
        """Test querying events by account ID."""
        event_store_mock.table.query.return_value = {
            "Items": [
                {
                    "event_id": "evt-001",
                    "timestamp": "2026-05-27T10:00:00Z",
                    "account_id": "123456789",
                    "raw_event": "{}",
                },
                {
                    "event_id": "evt-002",
                    "timestamp": "2026-05-27T10:01:00Z",
                    "account_id": "123456789",
                    "raw_event": "{}",
                },
            ]
        }

        result = event_store_mock.query_events_by_account("123456789", lookback_minutes=60)

        assert len(result) == 2
        assert all(e["account_id"] == "123456789" for e in result)
        event_store_mock.table.query.assert_called_once()


# ==========================================
# DecisionStore Tests
# ==========================================


class TestDecisionStore:
    """Test DecisionStore functionality."""

    @pytest.fixture
    def decision_store_mock(self):
        """Create a mock DecisionStore for testing."""
        from guardian.storage.decision_store import DecisionStore

        with patch("guardian.storage.decision_store.AWSClientProvider"):
            store = DecisionStore(table_name="test-decisions")
            store.table = MagicMock()
            return store

    def test_save_single_decision(self, decision_store_mock):
        """Test saving a single decision."""
        decision_data = {
            "decision_id": "dec-001",
            "threat_id": "thr-001",
            "severity": "CRITICAL",
            "detection_type": "volumetric_anomaly",
            "event_count": 150,
            "confidence": 0.95,
            "z_score": 3.5,
            "recommended_action": "terminate_resource",
        }

        result = decision_store_mock.save_decision(decision_data)

        assert result is True
        decision_store_mock.table.put_item.assert_called_once()
        call_args = decision_store_mock.table.put_item.call_args
        item = call_args[1]["Item"]
        assert item["decision_id"] == "dec-001"
        assert item["severity"] == "CRITICAL"

    def test_save_decisions_batch(self, decision_store_mock):
        """Test saving multiple decisions in batch."""
        decisions = [
            {"decision_id": "dec-001", "threat_id": "thr-001", "severity": "CRITICAL"},
            {"decision_id": "dec-002", "threat_id": "thr-002", "severity": "HIGH"},
        ]

        batch_writer = MagicMock()
        decision_store_mock.table.batch_writer.return_value.__enter__.return_value = batch_writer

        result = decision_store_mock.save_decisions_batch(decisions)

        assert result == 2
        assert batch_writer.put_item.call_count == 2

    def test_get_decision(self, decision_store_mock):
        """Test retrieving a decision by ID."""
        decision_store_mock.table.get_item.return_value = {
            "Item": {
                "decision_id": "dec-001",
                "threat_id": "thr-001",
                "severity": "CRITICAL",
                "confidence": Decimal("0.95"),
                "z_score": Decimal("3.5"),
                "details": json.dumps({"anomaly_type": "volumetric"}),
            }
        }

        result = decision_store_mock.get_decision("dec-001")

        assert result is not None
        assert result["decision_id"] == "dec-001"
        assert result["confidence"] == 0.95
        assert result["z_score"] == 3.5

    def test_query_decisions_by_threat(self, decision_store_mock):
        """Test querying decisions by threat ID."""
        decision_store_mock.table.query.return_value = {
            "Items": [
                {
                    "decision_id": "dec-001",
                    "threat_id": "thr-001",
                    "severity": "CRITICAL",
                    "confidence": Decimal("0.95"),
                    "details": "{}",
                },
                {
                    "decision_id": "dec-002",
                    "threat_id": "thr-001",
                    "severity": "CRITICAL",
                    "confidence": Decimal("0.92"),
                    "details": "{}",
                },
            ]
        }

        result = decision_store_mock.query_decisions_by_threat("thr-001")

        assert len(result) == 2
        assert all(d["threat_id"] == "thr-001" for d in result)

    def test_update_decision_action(self, decision_store_mock):
        """Test updating decision with executed action."""
        result = decision_store_mock.update_decision_action("dec-001", "terminate_resource", 500)

        assert result is True
        decision_store_mock.table.update_item.assert_called_once()
        call_args = decision_store_mock.table.update_item.call_args
        assert ":action" in call_args[1]["ExpressionAttributeValues"]
        assert ":cost" in call_args[1]["ExpressionAttributeValues"]


# ==========================================
# FeedbackStore Tests
# ==========================================


class TestFeedbackStore:
    """Test FeedbackStore functionality."""

    @pytest.fixture
    def feedback_store_mock(self):
        """Create a mock FeedbackStore for testing."""
        from guardian.storage.feedback_store import FeedbackStore

        with patch("guardian.storage.feedback_store.AWSClientProvider"):
            store = FeedbackStore(table_name="test-feedback")
            store.table = MagicMock()
            return store

    def test_save_single_feedback(self, feedback_store_mock):
        """Test saving feedback entry."""
        feedback_data = {
            "feedback_id": "fb-001",
            "decision_id": "dec-001",
            "feedback_type": "success",
            "rating": 9,
            "confidence": 0.98,
            "comments": "Action was effective",
        }

        result = feedback_store_mock.save_feedback(feedback_data)

        assert result is True
        feedback_store_mock.table.put_item.assert_called_once()
        call_args = feedback_store_mock.table.put_item.call_args
        item = call_args[1]["Item"]
        assert item["feedback_id"] == "fb-001"
        assert item["feedback_type"] == "success"

    def test_save_feedback_batch(self, feedback_store_mock):
        """Test saving multiple feedback entries in batch."""
        feedbacks = [
            {"feedback_id": "fb-001", "decision_id": "dec-001", "feedback_type": "success"},
            {"feedback_id": "fb-002", "decision_id": "dec-002", "feedback_type": "partial"},
        ]

        batch_writer = MagicMock()
        feedback_store_mock.table.batch_writer.return_value.__enter__.return_value = batch_writer

        result = feedback_store_mock.save_feedback_batch(feedbacks)

        assert result == 2
        assert batch_writer.put_item.call_count == 2

    def test_get_feedback(self, feedback_store_mock):
        """Test retrieving feedback by ID."""
        feedback_store_mock.table.get_item.return_value = {
            "Item": {
                "feedback_id": "fb-001",
                "decision_id": "dec-001",
                "feedback_type": "success",
                "rating": Decimal("9"),
                "confidence": Decimal("0.98"),
            }
        }

        result = feedback_store_mock.get_feedback("fb-001")

        assert result is not None
        assert result["feedback_id"] == "fb-001"
        assert result["rating"] == 9
        assert result["confidence"] == 0.98

    def test_update_feedback(self, feedback_store_mock):
        """Test updating feedback entry."""
        updates = {"rating": 10, "comments": "Updated feedback"}

        result = feedback_store_mock.update_feedback("fb-001", updates)

        assert result is True
        feedback_store_mock.table.update_item.assert_called_once()

    def test_get_learning_summary(self, feedback_store_mock):
        """Test getting learning summary from feedback."""
        feedback_store_mock.table.scan.return_value = {
            "Items": [
                {
                    "feedback_type": "success",
                    "rating": Decimal("9"),
                    "confidence": Decimal("0.95"),
                },
                {
                    "feedback_type": "success",
                    "rating": Decimal("8"),
                    "confidence": Decimal("0.92"),
                },
                {
                    "feedback_type": "partial",
                    "rating": Decimal("6"),
                    "confidence": Decimal("0.75"),
                },
            ]
        }

        result = feedback_store_mock.get_learning_summary(lookback_hours=24)

        assert result is not None
        assert result["total_feedback"] == 3
        assert result["by_type"]["success"] == 2
        assert result["by_type"]["partial"] == 1


# ==========================================
# S3ArchiveManager Tests
# ==========================================


class TestS3ArchiveManager:
    """Test S3ArchiveManager functionality."""

    @pytest.fixture
    def archive_manager_mock(self):
        """Create a mock S3ArchiveManager for testing."""
        from guardian.storage.s3_archive import S3ArchiveManager

        with patch("guardian.storage.s3_archive.AWSClientProvider"):
            manager = S3ArchiveManager(bucket_name="test-archive")
            manager.s3_client = MagicMock()
            return manager

    def test_archive_events(self, archive_manager_mock):
        """Test archiving events to S3."""
        events = [
            {
                "event_id": "evt-001",
                "account_id": "123456789",
                "event_type": "RunInstances",
                "raw_event": {"detail": "test"},
            },
            {
                "event_id": "evt-002",
                "account_id": "123456789",
                "event_type": "PutObject",
                "raw_event": {"detail": "test"},
            },
        ]

        result = archive_manager_mock.archive_events(events)

        assert result is True
        archive_manager_mock.s3_client.put_object.assert_called_once()
        call_args = archive_manager_mock.s3_client.put_object.call_args
        assert "events/" in call_args[1]["Key"]

    def test_archive_decisions(self, archive_manager_mock):
        """Test archiving decisions to S3."""
        decisions = [
            {
                "decision_id": "dec-001",
                "threat_id": "thr-001",
                "severity": "CRITICAL",
                "confidence": 0.95,
                "details": {"type": "volumetric"},
            },
        ]

        result = archive_manager_mock.archive_decisions(decisions)

        assert result is True
        archive_manager_mock.s3_client.put_object.assert_called_once()
        call_args = archive_manager_mock.s3_client.put_object.call_args
        assert "decisions/" in call_args[1]["Key"]

    def test_archive_feedback(self, archive_manager_mock):
        """Test archiving feedback to S3."""
        feedbacks = [
            {
                "feedback_id": "fb-001",
                "decision_id": "dec-001",
                "feedback_type": "success",
                "rating": 9,
            },
        ]

        result = archive_manager_mock.archive_feedback(feedbacks)

        assert result is True
        archive_manager_mock.s3_client.put_object.assert_called_once()
        call_args = archive_manager_mock.s3_client.put_object.call_args
        assert "feedback/" in call_args[1]["Key"]

    def test_list_archives(self, archive_manager_mock):
        """Test listing archives from S3."""
        archive_manager_mock.s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "events/2026/05/27/events-123.json.gz",
                    "Size": 1024,
                    "LastModified": datetime.now(timezone.utc),
                    "StorageClass": "STANDARD",
                },
                {
                    "Key": "decisions/2026/05/27/decisions-123.json.gz",
                    "Size": 2048,
                    "LastModified": datetime.now(timezone.utc),
                    "StorageClass": "STANDARD",
                },
            ]
        }

        result = archive_manager_mock.list_archives()

        assert len(result) == 2
        assert result[0]["key"] == "events/2026/05/27/events-123.json.gz"

    def test_retrieve_archive(self, archive_manager_mock):
        """Test retrieving archived data from S3."""
        import gzip

        test_data = [{"event_id": "evt-001", "data": "test"}]
        compressed = gzip.compress(json.dumps(test_data).encode("utf-8"))

        archive_manager_mock.s3_client.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=compressed))}

        result = archive_manager_mock.retrieve_archive("events/2026/05/27/events-123.json.gz")

        assert result is not None
        assert len(result) == 1
        assert result[0]["event_id"] == "evt-001"

    def test_get_archive_statistics(self, archive_manager_mock):
        """Test getting archive statistics."""
        archive_manager_mock.s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "events/2026/05/27/events-123.json.gz",
                    "Size": 1024,
                    "LastModified": datetime.now(timezone.utc),
                },
                {
                    "Key": "decisions/2026/05/27/decisions-123.json.gz",
                    "Size": 2048,
                    "LastModified": datetime.now(timezone.utc),
                },
                {
                    "Key": "feedback/2026/05/27/feedback-123.json.gz",
                    "Size": 512,
                    "LastModified": datetime.now(timezone.utc),
                },
            ]
        }

        result = archive_manager_mock.get_archive_statistics()

        assert result["total_objects"] == 3
        assert result["total_size_bytes"] == 3584
        assert result["by_type"]["events"] == 1
        assert result["by_type"]["decisions"] == 1
        assert result["by_type"]["feedback"] == 1


# ==========================================
# Integration Tests
# ==========================================


class TestPersistenceLayerIntegration:
    """Integration tests for entire persistence layer."""

    def test_event_to_decision_to_feedback_flow(self):
        """Test complete flow from event to decision to feedback."""
        from guardian.storage.event_store import EventStore
        from guardian.storage.decision_store import DecisionStore
        from guardian.storage.feedback_store import FeedbackStore

        with patch("guardian.storage.event_store.AWSClientProvider"), patch(
            "guardian.storage.decision_store.AWSClientProvider"
        ), patch("guardian.storage.feedback_store.AWSClientProvider"):

            event_store = EventStore(table_name="test-events")
            decision_store = DecisionStore(table_name="test-decisions")
            feedback_store = FeedbackStore(table_name="test-feedback")

            event_store.table = MagicMock()
            decision_store.table = MagicMock()
            feedback_store.table = MagicMock()

            # Step 1: Save event
            event_data = {
                "event_id": "evt-001",
                "account_id": "123456789",
                "event_type": "RunInstances",
                "severity": "HIGH",
            }
            event_saved = event_store.save_event(event_data)
            assert event_saved is True

            # Step 2: Save decision based on event
            decision_data = {
                "decision_id": "dec-001",
                "threat_id": "evt-001",
                "severity": "HIGH",
                "recommended_action": "isolate_resource",
            }
            decision_saved = decision_store.save_decision(decision_data)
            assert decision_saved is True

            # Step 3: Save feedback on decision
            feedback_data = {
                "feedback_id": "fb-001",
                "decision_id": "dec-001",
                "feedback_type": "success",
                "rating": 9,
            }
            feedback_saved = feedback_store.save_feedback(feedback_data)
            assert feedback_saved is True
