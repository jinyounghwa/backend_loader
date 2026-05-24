"""Real-time CloudTrail Event Stream Handler"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CloudTrailStreamHandler:
    """Handle real-time CloudTrail events from SQS/DynamoDB Streams"""

    def __init__(self, dynamodb_table):
        """
        Args:
            dynamodb_table: DynamoDB table for event storage
        """
        self.table = dynamodb_table

    def process_cloudtrail_stream(self, records: List[Dict]) -> Dict:
        """
        Process CloudTrail events from stream in real-time

        Args:
            records: List of CloudTrail events from stream

        Returns:
            Processing result with detected threats
        """
        try:
            result = {
                'total_events': len(records),
                'threats_detected': 0,
                'alerts': [],
                'processing_time_ms': 0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            for record in records:
                try:
                    # Extract API calls from event
                    calls = self.extract_api_calls(record)

                    # Filter by risk level
                    high_risk = self.filter_by_risk_level(calls)

                    # If threats detected, trigger alert
                    if high_risk:
                        for threat in high_risk:
                            alert = self.trigger_immediate_alert(threat)
                            result['alerts'].append(alert)
                            result['threats_detected'] += 1

                except Exception as e:
                    logger.warning(f"Failed to process event: {str(e)}")

            logger.info(f"Processed stream: {result['total_events']} events, {result['threats_detected']} threats")
            return result

        except Exception as e:
            logger.error(f"Failed to process CloudTrail stream: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def extract_api_calls(self, event: Dict) -> List[Dict]:
        """
        Extract API calls from CloudTrail event

        Args:
            event: CloudTrail event record

        Returns:
            List of extracted API calls with metadata
        """
        try:
            calls = []

            event_name = event.get('eventName', 'Unknown')
            event_source = event.get('eventSource', '')
            principal = self._extract_principal_id(event)
            source_ip = event.get('sourceIPAddress', 'unknown')
            timestamp = event.get('eventTime', datetime.now(timezone.utc).isoformat())

            call = {
                'eventName': event_name,
                'eventSource': event_source,
                'principal': principal,
                'sourceIPAddress': source_ip,
                'timestamp': timestamp,
                'requestParameters': event.get('requestParameters', {}),
                'responseElements': event.get('responseElements', {})
            }

            calls.append(call)

            logger.debug(f"Extracted {len(calls)} API calls from event")
            return calls

        except Exception as e:
            logger.error(f"Failed to extract API calls: {str(e)}")
            return []

    def filter_by_risk_level(self, calls: List[Dict], threshold: int = 5) -> List[Dict]:
        """
        Filter API calls by risk level

        Args:
            calls: List of API calls
            threshold: Risk score threshold (0-10)

        Returns:
            High-risk API calls
        """
        try:
            high_risk = []

            for call in calls:
                # Calculate risk score for this call
                risk_score = self._calculate_call_risk_score(call)

                if risk_score >= threshold:
                    call['riskScore'] = risk_score
                    high_risk.append(call)

            logger.debug(f"Filtered {len(high_risk)} high-risk calls from {len(calls)}")
            return high_risk

        except Exception as e:
            logger.error(f"Failed to filter by risk level: {str(e)}")
            return []

    def correlate_suspicious_events(self, events: List[Dict]) -> List[Dict]:
        """
        Correlate suspicious events to detect attack patterns

        Args:
            events: List of suspicious events

        Returns:
            List of correlated threats
        """
        try:
            correlated = []

            # Group events by source IP
            by_ip = {}
            for event in events:
                ip = event.get('sourceIPAddress', 'unknown')
                if ip not in by_ip:
                    by_ip[ip] = []
                by_ip[ip].append(event)

            # Detect patterns
            for ip, ip_events in by_ip.items():
                if len(ip_events) >= 3:
                    threat = {
                        'threatType': 'brute_force_attempt',
                        'sourceIPAddress': ip,
                        'eventCount': len(ip_events),
                        'severity': min(10, len(ip_events) // 3 + 5),
                        'events': ip_events,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    correlated.append(threat)

            logger.info(f"Correlated {len(correlated)} suspicious patterns")
            return correlated

        except Exception as e:
            logger.error(f"Failed to correlate events: {str(e)}")
            return []

    def trigger_immediate_alert(self, threat: Dict) -> Dict:
        """
        Trigger immediate alert for detected threat

        Args:
            threat: Threat detected from stream

        Returns:
            Alert record
        """
        try:
            alert = {
                'alert_id': f"alert-{threat.get('eventId', 'unknown')}",
                'threatType': threat.get('threatType', 'unknown'),
                'severity': threat.get('severity', 5),
                'principal': threat.get('principal', 'unknown'),
                'resource': threat.get('resource', 'unknown'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'triggered',
                'message': self._format_threat_message(threat)
            }

            # Store alert in DynamoDB
            self.table.put_item(Item=alert)

            logger.warning(f"Alert triggered: {alert['alert_id']} - {threat.get('threatType')}")
            return alert

        except Exception as e:
            logger.error(f"Failed to trigger alert: {str(e)}")
            return {'error': str(e), 'status': 'failed'}

    def _extract_principal_id(self, event: Dict) -> str:
        """Helper: Extract principal from event"""
        user_identity = event.get('userIdentity', {})
        return user_identity.get('principalId', 'unknown')

    def _calculate_call_risk_score(self, call: Dict) -> int:
        """Helper: Calculate risk score for API call"""
        event_name = call.get('eventName', '')

        dangerous_actions = {
            'DeleteBucket': 9,
            'DeleteObject': 8,
            'PutBucketPolicy': 8,
            'PutUserPolicy': 8,
            'DeleteUser': 9,
            'DeleteRole': 9,
            'DeleteRolePolicy': 8,
            'AttachUserPolicy': 7,
            'AttachRolePolicy': 7,
            'CreateAccessKey': 6,
            'CreateUser': 5,
            'CreateRole': 5
        }

        return dangerous_actions.get(event_name, 1)

    def _format_threat_message(self, threat: Dict) -> str:
        """Helper: Format threat into alert message"""
        threat_type = threat.get('threatType', 'Unknown threat')
        severity = threat.get('severity', 5)
        principal = threat.get('principal', 'Unknown principal')

        return f"[SEVERITY {severity}/10] {threat_type} by {principal}"

    def _format_alert_message(self, alert: Dict) -> str:
        """Helper: Format alert for notification"""
        return f"Alert {alert.get('alert_id')}: {alert.get('message')}"
