"""Threat Callback Handler - Webhook endpoint for real-time threat detection."""

from typing import Dict, Optional
from datetime import datetime, timezone
import hmac
import hashlib
import json
import os


class ThreatCallbackHandler:
    """Handle incoming webhook callbacks for real-time threat response."""

    def __init__(self, realtime_processor, audit_logger, webhook_secret: Optional[str] = None):
        """Initialize threat callback handler.

        The webhook secret must be supplied explicitly or via the
        GUARDIAN_WEBHOOK_SECRET environment variable; without it every
        incoming webhook is rejected (fail closed).
        """
        self.processor = realtime_processor
        self.audit = audit_logger
        self.webhook_secret = webhook_secret or os.getenv("GUARDIAN_WEBHOOK_SECRET", "")
        self.callback_history = {}

    def handle_webhook(self, body: str, headers: Dict) -> Dict:
        """
        Handle incoming webhook POST request.

        Args:
            body: Request body (JSON string)
            headers: HTTP headers including X-Webhook-Signature

        Returns:
            {
                'status': 'success|failed|invalid_signature',
                'threat_id': str,
                'estimated_remediation_time_seconds': int,
                'message': str
            }
        """
        result = {
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        try:
            # Validate signature
            signature = headers.get('X-Webhook-Signature', '')
            if not self._verify_signature(body, signature):
                result['status'] = 'invalid_signature'
                result['message'] = 'Webhook signature validation failed'
                return result

            # Parse payload
            payload = json.loads(body) if isinstance(body, str) else body

            # Validate threat structure
            threat = payload.get('threat', {})
            if not threat.get('threat_id'):
                result['status'] = 'invalid'
                result['message'] = 'Missing threat_id in payload'
                return result

            # Process webhook through real-time processor
            queue_result = self.processor.process_webhook_trigger(payload)

            result['status'] = 'success'
            result['threat_id'] = queue_result.get('threat_id')
            result['estimated_remediation_time_seconds'] = queue_result.get(
                'estimated_remediation_time_seconds', 60
            )
            result['message'] = f"Threat {threat.get('threat_id')} queued for remediation"

            # Log webhook callback
            self.audit.log_callback(threat.get('threat_id'), result)

            # Store in callback history
            self.callback_history[threat.get('threat_id')] = {
                'timestamp': result['timestamp'],
                'status': result['status'],
                'source': payload.get('source', 'external')
            }

        except json.JSONDecodeError:
            result['status'] = 'failed'
            result['message'] = 'Invalid JSON payload'
        except Exception as e:
            result['status'] = 'failed'
            result['message'] = str(e)

        return result

    def validate_threat_signature(self, threat_id: str, signature: str) -> bool:
        """
        Validate threat detection signature from external service.

        Args:
            threat_id: Threat identifier
            signature: Signature from external service

        Returns:
            True if signature is valid, False otherwise
        """
        # Create expected signature
        expected_sig = hmac.new(
            self.webhook_secret.encode(),
            threat_id.encode(),
            hashlib.sha256
        ).hexdigest()

        # Compare with provided signature
        return hmac.compare_digest(expected_sig, signature)

    def immediately_invoke_remediation(self, threat: Dict) -> Dict:
        """
        Immediately invoke RemediationOrchestrator for critical threats.

        Args:
            threat: Threat details

        Returns:
            {
                'status': 'remediation_initiated|queued',
                'orchestration_id': str,
                'estimated_time_seconds': int
            }
        """
        result = {
            'threat_id': threat.get('threat_id'),
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        try:
            # For critical threats (severity >= 9), execute immediately
            if threat.get('severity', 5) >= 9:
                remediation_result = self.processor.orchestrator.execute_multi_resource_remediation(threat)
                result['status'] = 'remediation_initiated'
                result['orchestration_id'] = remediation_result.get('orchestration_id')
                result['estimated_time_seconds'] = 60
            else:
                # Queue for processing
                queue_result = self.processor.process_webhook_trigger({'threat': threat})
                result['status'] = 'queued'
                result['estimated_time_seconds'] = queue_result.get(
                    'estimated_remediation_time_seconds', 60
                )

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def get_callback_status(self, threat_id: str) -> Dict:
        """Get status of a threat callback."""
        if threat_id not in self.callback_history:
            return {
                'status': 'not_found',
                'threat_id': threat_id
            }

        history = self.callback_history[threat_id]
        return {
            'threat_id': threat_id,
            'status': history.get('status'),
            'timestamp': history.get('timestamp'),
            'source': history.get('source')
        }

    def _verify_signature(self, body: str, signature: str) -> bool:
        """Verify webhook signature using HMAC-SHA256."""
        if not self.webhook_secret or not signature:
            return False

        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            body.encode() if isinstance(body, str) else body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def _generate_signature(self, body: str) -> str:
        """Generate signature for testing."""
        return hmac.new(
            self.webhook_secret.encode(),
            body.encode() if isinstance(body, str) else body,
            hashlib.sha256
        ).hexdigest()
