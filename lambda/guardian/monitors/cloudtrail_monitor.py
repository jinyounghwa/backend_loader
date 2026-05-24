"""CloudTrail 이벤트 모니터"""

import logging
import uuid
from typing import Dict, List, Optional, Iterator
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class CloudTrailEventMonitor:
    """AWS CloudTrail 이벤트의 실시간 모니터링"""

    def __init__(self, cloudtrail_client, s3_client, dynamodb_table):
        """
        Args:
            cloudtrail_client: boto3 CloudTrail client
            s3_client: boto3 S3 client
            dynamodb_table: DynamoDB table for event storage
        """
        self.cloudtrail = cloudtrail_client
        self.s3 = s3_client
        self.table = dynamodb_table

    def stream_cloudtrail_events(self, account_id: str, event_names: List[str], hours: int = 24) -> List[Dict]:
        """
        CloudTrail 이벤트 스트림 조회

        Args:
            account_id: AWS Account ID
            event_names: 조회할 이벤트 이름 (RunInstances, TerminateInstances 등)
            hours: 조회 기간 (시간)

        Returns:
            CloudTrail 이벤트 목록
        """
        try:
            events = []
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            for event_name in event_names:
                response = self.cloudtrail.lookup_events(
                    LookupAttributes=[
                        {
                            'AttributeKey': 'EventName',
                            'AttributeValue': event_name
                        }
                    ],
                    StartTime=start_time,
                    MaxResults=50
                )

                for event in response.get('Events', []):
                    events.append({
                        'EventID': event.get('EventID'),
                        'EventName': event.get('EventName'),
                        'EventTime': event.get('EventTime'),
                        'Username': event.get('Username'),
                        'SourceIPAddress': event.get('SourceIPAddress'),
                        'Resources': event.get('Resources', [])
                    })

            logger.info(f"Streamed {len(events)} CloudTrail events for {account_id}")
            return events

        except Exception as e:
            logger.error(f"Failed to stream CloudTrail events: {str(e)}")
            return []

    def filter_events_by_criteria(self, events: List[Dict], criteria: Dict) -> List[Dict]:
        """
        특정 조건으로 이벤트 필터링

        Args:
            events: 이벤트 목록
            criteria: 필터링 조건
                - EventName: 이벤트 이름
                - Username: 사용자명
                - TimeRange: 시간 범위
                - SourceIP: 소스 IP

        Returns:
            필터링된 이벤트 목록
        """
        try:
            filtered = events

            # Filter by event name
            if 'EventName' in criteria:
                filtered = [e for e in filtered if e.get('EventName') == criteria['EventName']]

            # Filter by username
            if 'Username' in criteria:
                filtered = [e for e in filtered if e.get('Username') == criteria['Username']]

            # Filter by time range
            if 'TimeRange' in criteria:
                time_range = criteria['TimeRange']
                cutoff = datetime.now(timezone.utc) - timedelta(hours=time_range)
                filtered = [e for e in filtered if e.get('EventTime', datetime.now(timezone.utc)) >= cutoff]

            # Filter by source IP
            if 'SourceIP' in criteria:
                filtered = [e for e in filtered if e.get('SourceIPAddress') == criteria['SourceIP']]

            logger.info(f"Filtered {len(filtered)} events from {len(events)} total")
            return filtered

        except Exception as e:
            logger.error(f"Failed to filter events: {str(e)}")
            return []

    def detect_suspicious_activity(self, account_id: str, events: List[Dict]) -> List[Dict]:
        """
        의심스러운 활동 감지

        Args:
            account_id: AWS Account ID
            events: CloudTrail 이벤트 목록

        Returns:
            의심스러운 활동 목록
        """
        try:
            suspicious = []

            for event in events:
                risk_score = 0
                reasons = []

                # Check for root account usage
                if event.get('Username') == 'root':
                    risk_score += 30
                    reasons.append('Root account used')

                # Check for sensitive operations
                sensitive_ops = ['DeleteDBInstance', 'DeleteBucket', 'ModifyDBInstance', 'DeleteSecurityGroup']
                if event.get('EventName') in sensitive_ops:
                    risk_score += 25
                    reasons.append(f'Sensitive operation: {event.get("EventName")}')

                # Check for unusual source IP
                if event.get('SourceIPAddress', '').startswith('203.0.113') or event.get('SourceIPAddress', '').startswith('198.51.100'):
                    risk_score += 15
                    reasons.append(f'Unusual source IP: {event.get("SourceIPAddress")}')

                # Check for off-hours activity (assume off-hours: 22:00-06:00)
                event_time = event.get('EventTime')
                if isinstance(event_time, str):
                    event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))

                if event_time.hour >= 22 or event_time.hour < 6:
                    risk_score += 10
                    reasons.append('Off-hours activity detected')

                if risk_score > 20:
                    suspicious.append({
                        'EventID': event.get('EventID'),
                        'EventName': event.get('EventName'),
                        'Username': event.get('Username'),
                        'risk_score': risk_score,
                        'reasons': reasons
                    })

            logger.info(f"Detected {len(suspicious)} suspicious activities")
            return suspicious

        except Exception as e:
            logger.error(f"Failed to detect suspicious activity: {str(e)}")
            return []

    def correlate_events(self, account_id: str, events: List[Dict]) -> List[Dict]:
        """
        이벤트 상관관계 분석

        Args:
            account_id: AWS Account ID
            events: CloudTrail 이벤트 목록

        Returns:
            상관관계 분석 결과 (공격 시나리오 등)
        """
        try:
            correlations = []

            # Group events by username and resource
            user_resource_map = {}
            for event in events:
                key = (event.get('Username'), event.get('Resources', [{}])[0].get('ResourceName', ''))
                if key not in user_resource_map:
                    user_resource_map[key] = []
                user_resource_map[key].append(event)

            # Detect attack patterns
            for (username, resource), user_events in user_resource_map.items():
                if len(user_events) > 3:  # Multiple events on same resource
                    event_names = [e.get('EventName') for e in user_events]

                    # Check for suspicious sequence
                    if 'GetUser' in event_names and 'CreateAccessKey' in event_names:
                        correlations.append({
                            'account_id': account_id,
                            'attack_pattern': 'Privilege escalation attempt',
                            'username': username,
                            'resource': resource,
                            'severity': 'critical',
                            'events': event_names
                        })

            logger.info(f"Found {len(correlations)} event correlations")
            return correlations

        except Exception as e:
            logger.error(f"Failed to correlate events: {str(e)}")
            return []

    def trigger_alert(self, account_id: str, event: Dict, severity: str = 'medium') -> Dict:
        """
        의심 이벤트에 대한 실시간 알림 발행

        Args:
            account_id: AWS Account ID
            event: CloudTrail 이벤트
            severity: 심각도 (low, medium, high, critical)

        Returns:
            알림 정보
        """
        try:
            alert_id = str(uuid.uuid4())

            alert = {
                'alert_id': alert_id,
                'account_id': account_id,
                'event_id': event.get('EventID'),
                'event_name': event.get('EventName'),
                'username': event.get('Username'),
                'severity': severity,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_details': event
            }

            # Store alert
            self.table.put_item(Item=alert)

            logger.info(f"Triggered {severity} alert for {event.get('EventName')}")
            return alert

        except Exception as e:
            logger.error(f"Failed to trigger alert: {str(e)}")
            return {}

    def store_event(self, account_id: str, event: Dict) -> None:
        """
        CloudTrail 이벤트를 감사 로그로 저장

        Args:
            account_id: AWS Account ID
            event: CloudTrail 이벤트
        """
        try:
            audit_entry = {
                'account_id': account_id,
                'EventID': event.get('EventID'),
                'EventName': event.get('EventName'),
                'EventTime': event.get('EventTime', datetime.now(timezone.utc)).isoformat() if isinstance(event.get('EventTime'), datetime) else event.get('EventTime'),
                'Username': event.get('Username'),
                'SourceIPAddress': event.get('SourceIPAddress'),
                'Resources': event.get('Resources', []),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            self.table.put_item(Item=audit_entry)

            logger.info(f"Stored event {event.get('EventName')} to audit log")

        except Exception as e:
            logger.error(f"Failed to store event: {str(e)}")

    def get_event_history(self, account_id: str, days: int = 7) -> List[Dict]:
        """
        이벤트 감사 이력 조회

        Args:
            account_id: AWS Account ID
            days: 조회 기간 (일)

        Returns:
            이벤트 이력 목록
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            response = self.table.query(
                KeyConditionExpression='account_id = :acc',
                ExpressionAttributeValues={':acc': account_id}
            )

            items = response.get('Items', [])

            # Filter by date
            filtered = []
            for item in items:
                timestamp = datetime.fromisoformat(item.get('timestamp', ''))
                if timestamp >= cutoff:
                    filtered.append(item)

            logger.info(f"Retrieved {len(filtered)} event history records")
            return filtered

        except Exception as e:
            logger.error(f"Failed to retrieve event history: {str(e)}")
            return []
