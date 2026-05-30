"""Sprint 71 Phase 2: Real-time Threat Response Automation (17 tests)"""

import pytest


class TestThreatResponder:
    """Test automatic threat response."""

    def test_respond_to_critical_threat(self):
        """✅ Auto-respond to critical threat."""
        from guardian.responders.threat_responder import ThreatResponder

        responder = ThreatResponder()
        threat = {
            'id': 'threat-1',
            'type': 'MALWARE',
            'severity': 'CRITICAL',
            'resource_id': 'i-12345678',
            'timestamp': '2026-05-30T10:00:00Z'
        }

        response = responder.respond_to_threat(threat)

        assert response['action'] == 'ISOLATE'
        assert response['resource_id'] == 'i-12345678'

    def test_respond_to_high_threat(self):
        """✅ Auto-respond to high severity threat."""
        from guardian.responders.threat_responder import ThreatResponder

        responder = ThreatResponder()
        threat = {
            'id': 'threat-2',
            'type': 'UNAUTHORIZED_ACCESS',
            'severity': 'HIGH',
            'resource_id': 'sg-87654321',
            'timestamp': '2026-05-30T11:00:00Z'
        }

        response = responder.respond_to_threat(threat)

        assert response['action'] in ['ISOLATE', 'BLOCK']
        assert response['resource_id'] == 'sg-87654321'

    def test_respond_to_medium_threat(self):
        """✅ Alert on medium severity threat."""
        from guardian.responders.threat_responder import ThreatResponder

        responder = ThreatResponder()
        threat = {
            'id': 'threat-3',
            'type': 'RECON',
            'severity': 'MEDIUM',
            'timestamp': '2026-05-30T12:00:00Z'
        }

        response = responder.respond_to_threat(threat)

        assert response['action'] == 'ALERT'


class TestResponseExecutor:
    """Test response action execution."""

    def test_execute_isolate_action(self):
        """✅ Execute EC2 isolation."""
        from guardian.responders.threat_responder import ResponseExecutor

        executor = ResponseExecutor()
        result = executor.execute_action({
            'action': 'ISOLATE',
            'resource_id': 'i-12345678',
            'resource_type': 'EC2_INSTANCE'
        })

        assert result['status'] == 'executed'
        assert result['action'] == 'ISOLATE'

    def test_execute_block_action(self):
        """✅ Execute security group block."""
        from guardian.responders.threat_responder import ResponseExecutor

        executor = ResponseExecutor()
        result = executor.execute_action({
            'action': 'BLOCK',
            'resource_id': 'sg-87654321',
            'resource_type': 'SECURITY_GROUP'
        })

        assert result['status'] == 'executed'
        assert result['action'] == 'BLOCK'

    def test_execute_alert_action(self):
        """✅ Execute alert action."""
        from guardian.responders.threat_responder import ResponseExecutor

        executor = ResponseExecutor()
        result = executor.execute_action({
            'action': 'ALERT',
            'channels': ['sns', 'email']
        })

        assert result['status'] == 'executed'
        assert result['action'] == 'ALERT'


class TestResponseTracker:
    """Test response tracking and history."""

    def test_track_response_execution(self):
        """✅ Track response execution."""
        from guardian.responders.threat_responder import ResponseTracker

        tracker = ResponseTracker()
        tracker.track_response({
            'threat_id': 'threat-1',
            'action': 'ISOLATE',
            'status': 'executed',
            'timestamp': '2026-05-30T10:00:00Z'
        })

        history = tracker.get_response_history('threat-1')
        assert len(history) == 1

    def test_track_response_reversal(self):
        """✅ Track response reversal/undo."""
        from guardian.responders.threat_responder import ResponseTracker

        tracker = ResponseTracker()
        tracker.track_response({
            'threat_id': 'threat-1',
            'action': 'ISOLATE',
            'status': 'executed'
        })

        tracker.track_response({
            'threat_id': 'threat-1',
            'action': 'ISOLATE',
            'status': 'reversed'
        })

        history = tracker.get_response_history('threat-1')
        assert history[-1]['status'] == 'reversed'

    def test_get_response_audit_log(self):
        """✅ Get audit log of responses."""
        from guardian.responders.threat_responder import ResponseTracker

        tracker = ResponseTracker()
        tracker.track_response({'threat_id': 'threat-1', 'action': 'ISOLATE'})
        tracker.track_response({'threat_id': 'threat-2', 'action': 'BLOCK'})

        audit_log = tracker.get_audit_log()
        assert len(audit_log) == 2


class TestResponsePolicy:
    """Test response policy evaluation."""

    def test_evaluate_critical_policy(self):
        """✅ Evaluate critical threat policy."""
        from guardian.responders.response_policy import ResponsePolicy

        policy = ResponsePolicy()
        policy.add_rule({
            'severity': 'CRITICAL',
            'action': 'ISOLATE',
            'delay_seconds': 0
        })

        result = policy.evaluate_threat({'severity': 'CRITICAL'})

        assert result['action'] == 'ISOLATE'
        assert result['delay_seconds'] == 0

    def test_evaluate_high_policy(self):
        """✅ Evaluate high threat policy."""
        from guardian.responders.response_policy import ResponsePolicy

        policy = ResponsePolicy()
        policy.add_rule({
            'severity': 'HIGH',
            'action': 'BLOCK',
            'delay_seconds': 5
        })

        result = policy.evaluate_threat({'severity': 'HIGH'})

        assert result['action'] == 'BLOCK'
        assert result['delay_seconds'] == 5

    def test_evaluate_medium_policy(self):
        """✅ Evaluate medium threat policy."""
        from guardian.responders.response_policy import ResponsePolicy

        policy = ResponsePolicy()
        policy.add_rule({
            'severity': 'MEDIUM',
            'action': 'ALERT',
            'delay_seconds': 30
        })

        result = policy.evaluate_threat({'severity': 'MEDIUM'})

        assert result['action'] == 'ALERT'


class TestPolicyEvaluator:
    """Test policy evaluation logic."""

    def test_policy_matches_threat_type(self):
        """✅ Match policy by threat type."""
        from guardian.responders.response_policy import PolicyEvaluator

        evaluator = PolicyEvaluator()
        evaluator.add_policy({
            'threat_type': 'MALWARE',
            'action': 'ISOLATE'
        })

        result = evaluator.matches({'threat_type': 'MALWARE'})

        assert result is True

    def test_policy_matches_resource_type(self):
        """✅ Match policy by resource type."""
        from guardian.responders.response_policy import PolicyEvaluator

        evaluator = PolicyEvaluator()
        evaluator.add_policy({
            'resource_type': 'EC2_INSTANCE',
            'action': 'ISOLATE'
        })

        result = evaluator.matches({'resource_type': 'EC2_INSTANCE'})

        assert result is True

    def test_policy_priority(self):
        """✅ Apply policies in priority order."""
        from guardian.responders.response_policy import PolicyEvaluator

        evaluator = PolicyEvaluator()
        evaluator.add_policy({'priority': 1, 'action': 'ALERT'})
        evaluator.add_policy({'priority': 2, 'action': 'BLOCK'})
        evaluator.add_policy({'priority': 3, 'action': 'ISOLATE'})

        threat = {}
        action = evaluator.get_action(threat)

        assert action == 'ALERT'  # Highest priority


class TestResponseAutomationIntegration:
    """Test end-to-end response automation."""

    def test_detect_and_respond_workflow(self):
        """✅ Full threat detection and response workflow."""
        from guardian.responders.threat_responder import ThreatResponder, ResponseTracker

        responder = ThreatResponder()
        tracker = ResponseTracker()

        threat = {
            'id': 'threat-critical',
            'type': 'MALWARE',
            'severity': 'CRITICAL',
            'resource_id': 'i-infected'
        }

        # Respond to threat
        response = responder.respond_to_threat(threat)

        # Track response
        tracker.track_response({
            'threat_id': threat['id'],
            'action': response['action'],
            'status': 'executed'
        })

        # Verify history
        history = tracker.get_response_history('threat-critical')
        assert len(history) > 0
        assert history[0]['action'] == 'ISOLATE'

    def test_delayed_response_execution(self):
        """✅ Execute delayed responses."""
        from guardian.responders.threat_responder import ResponseExecutor

        executor = ResponseExecutor()
        result = executor.execute_delayed_action(
            action={'action': 'ISOLATE', 'resource_id': 'i-123'},
            delay_seconds=5
        )

        assert result['scheduled'] is True
        assert result['delay_seconds'] == 5

    def test_response_cancellation(self):
        """✅ Cancel pending response."""
        from guardian.responders.threat_responder import ResponseExecutor

        executor = ResponseExecutor()

        # Schedule response
        scheduled = executor.execute_delayed_action(
            action={'action': 'ISOLATE'},
            delay_seconds=10
        )

        # Cancel it
        cancelled = executor.cancel_scheduled_action(scheduled['id'])

        assert cancelled['status'] == 'cancelled'
