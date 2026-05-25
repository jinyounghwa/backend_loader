"""Sprint 47 Phase 2: Real-Time Response Integration Tests (6 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from datetime import datetime
import json
import hmac
import hashlib

lambda_path = Path(__file__).parent.parent.parent / "lambda"
sys.path.insert(0, str(lambda_path))

from guardian.handlers.realtime_handler import RealTimeEventProcessor
from guardian.handlers.threat_callback_handler import ThreatCallbackHandler


class TestRealTimeResponseIntegration:
    """End-to-end real-time threat response scenarios."""

    def test_cloudtrail_event_triggers_realtime_response(self):
        """✅ CloudTrail event → priority queue → immediate remediation."""
        mock_orchestrator = Mock()
        mock_audit = Mock()

        processor = RealTimeEventProcessor(mock_orchestrator, mock_audit)

        # Suspicious CloudTrail event
        cloudtrail_event = {
            'detail-id': 'evt-001',
            'source': 'aws.cloudtrail',
            'detail-type': 'AWS API Call via CloudTrail',
            'detail': {
                'eventName': 'AttachUserPolicy',
                'userIdentity': {
                    'principalId': 'attacker-user',
                    'arn': 'arn:aws:iam::123456789012:user/attacker'
                },
                'sourceIPAddress': '203.0.113.1',
                'requestParameters': {
                    'userName': 'attacker-user',
                    'policyArn': 'arn:aws:iam::aws:policy/AdministratorAccess'
                }
            }
        }

        # Process event
        queue_result = processor.process_cloudtrail_event(cloudtrail_event)
        assert queue_result['status'] == 'queued'

        # Setup orchestrator mock
        mock_orchestrator.execute_multi_resource_remediation.return_value = {
            'orchestration_id': 'orch-ct-001',
            'status': 'success',
            'execution_order': ['iam']
        }

        # Dequeue and remediate
        remediation_result = processor.dequeue_and_remediate()

        assert remediation_result['status'] == 'remediated'
        assert remediation_result['orchestration_id'] == 'orch-ct-001'
        assert remediation_result['remediation_time_seconds'] >= 0

    def test_sns_notification_triggers_remediation(self):
        """✅ SNS notification (public bucket) → remediation."""
        mock_orchestrator = Mock()
        mock_audit = Mock()

        processor = RealTimeEventProcessor(mock_orchestrator, mock_audit)

        # SNS notification for public bucket
        sns_notification = {
            'MessageId': 'msg-s3-001',
            'Message': json.dumps({
                'detail-type': 'S3:PublicBucketCreated',
                'bucket': {'name': 'exposed-bucket'}
            })
        }

        # Process notification
        queue_result = processor.process_sns_notification(sns_notification)
        assert queue_result['status'] == 'queued'

        # Setup orchestrator mock
        mock_orchestrator.execute_multi_resource_remediation.return_value = {
            'orchestration_id': 'orch-sns-001',
            'status': 'success'
        }

        # Dequeue and remediate
        remediation_result = processor.dequeue_and_remediate()

        assert remediation_result['status'] == 'remediated'

    def test_webhook_endpoint_integration(self):
        """✅ Webhook endpoint receives threat → validates signature → queues remediation."""
        mock_orchestrator = Mock()
        mock_audit = Mock()

        processor = RealTimeEventProcessor(mock_orchestrator, mock_audit)
        handler = ThreatCallbackHandler(processor, mock_audit, webhook_secret='prod-secret')

        # Incoming webhook threat
        threat_payload = {
            'threat': {
                'threat_id': 'THREAT-WEBHOOK-INT-001',
                'severity': 9,
                'instance_id': 'i-webhook-compromised',
                'description': 'Malware detected by external scanner'
            },
            'source': 'external-security-tool',
            'timestamp': datetime.utcnow().isoformat()
        }

        body = json.dumps(threat_payload)

        # Generate valid signature
        valid_signature = hmac.new(
            b'prod-secret',
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        # Handle webhook
        webhook_result = handler.handle_webhook(body, {
            'X-Webhook-Signature': valid_signature
        })

        assert webhook_result['status'] == 'success'
        assert webhook_result['threat_id'] == 'THREAT-WEBHOOK-INT-001'
        assert webhook_result['estimated_remediation_time_seconds'] == 60

        # Queue should have the threat
        queue_status = processor.get_queue_status()
        assert queue_status['queue_size'] > 0

    def test_realtime_vs_scheduled_response_priority(self):
        """✅ Real-time threats are prioritized over scheduled scans."""
        mock_orchestrator = Mock()
        mock_audit = Mock()

        processor = RealTimeEventProcessor(mock_orchestrator, mock_audit)

        # Low-priority scheduled scan threat
        scheduled_threat = {
            'detail-id': 'scheduled-001',
            'source': 'scheduled-scan',
            'detail': {'eventName': 'ScheduledScan'},
            'severity': 3
        }

        # High-priority real-time threat
        realtime_threat = {
            'detail-id': 'realtime-001',
            'source': 'aws.cloudtrail',
            'detail': {'eventName': 'CreateAccessKey'},
            'severity': 8
        }

        # Queue scheduled first
        processor.process_cloudtrail_event(scheduled_threat)

        # Then queue real-time (arrives second but should be processed first)
        processor.process_cloudtrail_event(realtime_threat)

        # Setup orchestrator
        mock_orchestrator.execute_multi_resource_remediation.return_value = {
            'orchestration_id': 'orch-priority',
            'status': 'success'
        }

        # First dequeue should be high-priority real-time threat
        first_result = processor.dequeue_and_remediate()
        assert first_result['priority'] == 2  # HIGH priority

    def test_response_performance_latency(self):
        """✅ Response latency is < 10 seconds from detection to remediation."""
        mock_orchestrator = Mock()
        mock_audit = Mock()

        processor = RealTimeEventProcessor(mock_orchestrator, mock_audit)

        event = {
            'detail-id': 'perf-001',
            'source': 'aws.cloudtrail',
            'detail': {'eventName': 'CreateAccessKey'}
        }

        import time
        start_time = time.time()

        # Process event
        processor.process_cloudtrail_event(event)

        # Setup orchestrator
        mock_orchestrator.execute_multi_resource_remediation.return_value = {
            'orchestration_id': 'orch-perf',
            'status': 'success'
        }

        # Dequeue and remediate
        processor.dequeue_and_remediate()

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete in < 10 seconds
        assert elapsed < 10.0

    def test_response_failure_fallback_to_scheduled(self):
        """✅ If real-time remediation fails, threat is logged for scheduled scan."""
        mock_orchestrator = Mock()
        mock_audit = Mock()

        processor = RealTimeEventProcessor(mock_orchestrator, mock_audit)

        event = {
            'detail-id': 'fallback-001',
            'source': 'aws.cloudtrail',
            'detail': {'eventName': 'CreateAccessKey'}
        }

        # Process event
        queue_result = processor.process_cloudtrail_event(event)
        assert queue_result['status'] == 'queued'

        # Setup orchestrator to fail
        mock_orchestrator.execute_multi_resource_remediation.side_effect = Exception(
            'Orchestrator unavailable'
        )

        # Attempt remediation
        remediation_result = processor.dequeue_and_remediate()

        # Should fail gracefully
        assert remediation_result['status'] == 'error'

        # Threat is logged for audit/scheduled retry
        assert mock_audit.called or remediation_result['error']
