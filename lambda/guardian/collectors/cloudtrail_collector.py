import logging
import uuid
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class CloudTrailCollector:
    """CloudTrail 스트림에서 AWS 이벤트 수집 및 처리"""

    SUPPORTED_EVENTS = {
        'RunInstances': 'HIGH',
        'PutObject': 'MEDIUM',
        'CreateAccessKey': 'HIGH',
        'ModifySecurityGroup': 'MEDIUM',
        'PutBucketPolicy': 'MEDIUM',
        'CreateUser': 'MEDIUM',
        'AttachUserPolicy': 'MEDIUM',
        'CreateDBInstance': 'MEDIUM'
    }

    def __init__(self):
        """CloudTrail 수집기 초기화"""
        self.collections = {}
        self.seen_events = set()
        self.event_buffer = defaultdict(list)

    def start_collection(self, region: str, event_names: List[str]) -> str:
        """
        CloudTrail 수집 시작

        Args:
            region: AWS 리전
            event_names: 수집할 이벤트 타입 목록

        Returns:
            collector_id
        """
        collector_id = str(uuid.uuid4())
        self.collections[collector_id] = {
            'region': region,
            'event_names': event_names,
            'started_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'total_events': 0,
            'processed_events': 0,
            'duplicates': 0,
            'errors': 0
        }
        logger.info(f"Collection started: {collector_id} in region {region}")
        return collector_id

    def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        CloudTrail 이벤트 처리

        Args:
            event: CloudTrail 이벤트

        Returns:
            {
                'event_id': str,
                'event_type': str,
                'source_ips': [str],
                'principals': [str],
                'resources': [str],
                'timestamp': str,
                'error_code': str (optional)
            }
        """
        event_id = event.get('eventID', str(uuid.uuid4()))

        # 중복 확인
        if event_id in self.seen_events:
            return {
                'event_id': event_id,
                'is_duplicate': True,
                'event_type': event.get('eventName', 'Unknown')
            }

        self.seen_events.add(event_id)

        event_type = event.get('eventName', 'Unknown')
        source_ips = []
        principals = []
        resources = []

        # Source IP 추출
        if 'sourceIPAddress' in event:
            source_ips.append(event['sourceIPAddress'])

        # Principal 추출
        user_identity = event.get('userIdentity', {})
        if user_identity.get('arn'):
            principals.append(user_identity['arn'])
        if user_identity.get('principalId'):
            principals.append(user_identity['principalId'])

        # Resource 추출
        if 'resources' in event:
            for resource in event['resources']:
                resources.append(resource.get('ARN', resource.get('name', '')))

        # Error code 추출
        error_code = event.get('errorCode')

        result = {
            'event_id': event_id,
            'event_type': event_type,
            'source_ips': source_ips,
            'principals': principals,
            'resources': resources,
            'timestamp': event.get('eventTime', datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
        }

        if error_code:
            result['error_code'] = error_code

        logger.info(f"Event processed: {event_id} ({event_type})")
        return result

    def filter_events(self, event_type: str, filters: Dict) -> List[Dict]:
        """
        CloudTrail 이벤트 필터링

        Args:
            event_type: 필터링할 이벤트 타입
            filters: 추가 필터 조건

        Returns:
            필터링된 이벤트 목록
        """
        matching_events = []

        for event_id, events in self.event_buffer.items():
            for event in events:
                # 이벤트 타입 필터
                if event.get('event_type') != event_type:
                    continue

                # 추가 필터 적용
                match = True
                if 'principal' in filters:
                    if filters['principal'] not in event.get('principals', []):
                        match = False
                if 'source_ip' in filters:
                    if filters['source_ip'] not in event.get('source_ips', []):
                        match = False
                if 'resource' in filters:
                    if filters['resource'] not in event.get('resources', []):
                        match = False

                if match:
                    matching_events.append(event)

        logger.info(f"Filtered {len(matching_events)} events of type {event_type}")
        return matching_events

    def get_collection_stats(self, collector_id: str) -> Dict:
        """
        수집 통계 조회

        Args:
            collector_id: 수집기 ID

        Returns:
            {
                'collector_id': str,
                'region': str,
                'started_at': str,
                'total_events': int,
                'processed_events': int,
                'duplicates': int,
                'errors': int,
                'deduplication_rate': float,
                'success_rate': float
            }
        """
        if collector_id not in self.collections:
            return {
                'collector_id': collector_id,
                'error': 'Collector not found'
            }

        stats = self.collections[collector_id]
        total = stats['total_events']
        success = stats['processed_events']

        dedup_rate = stats['duplicates'] / total if total > 0 else 0.0
        success_rate = success / total if total > 0 else 0.0

        return {
            'collector_id': collector_id,
            'region': stats['region'],
            'started_at': stats['started_at'],
            'total_events': total,
            'processed_events': success,
            'duplicates': stats['duplicates'],
            'errors': stats['errors'],
            'deduplication_rate': round(dedup_rate, 3),
            'success_rate': round(success_rate, 3)
        }

    def add_to_buffer(self, collector_id: str, event: Dict) -> None:
        """
        이벤트를 버퍼에 추가

        Args:
            collector_id: 수집기 ID
            event: 처리된 이벤트
        """
        if collector_id in self.collections:
            self.event_buffer[collector_id].append(event)
            self.collections[collector_id]['total_events'] += 1
            self.collections[collector_id]['processed_events'] += 1

    def record_duplicate(self, collector_id: str) -> None:
        """중복 이벤트 기록"""
        if collector_id in self.collections:
            self.collections[collector_id]['duplicates'] += 1

    def record_error(self, collector_id: str) -> None:
        """에러 기록"""
        if collector_id in self.collections:
            self.collections[collector_id]['errors'] += 1

    def batch_process(self, collector_id: str, events: List[Dict]) -> Dict:
        """
        배치 처리

        Args:
            collector_id: 수집기 ID
            events: 처리할 이벤트 목록

        Returns:
            {
                'processed': int,
                'duplicates': int,
                'errors': int,
                'duration_ms': float
            }
        """
        start_time = time.time()
        processed = 0
        duplicates = 0
        errors = 0

        for event in events:
            try:
                result = self.process_event(event)
                if result.get('is_duplicate'):
                    self.record_duplicate(collector_id)
                    duplicates += 1
                else:
                    self.add_to_buffer(collector_id, result)
                    processed += 1
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                self.record_error(collector_id)
                errors += 1

        duration_ms = (time.time() - start_time) * 1000

        return {
            'processed': processed,
            'duplicates': duplicates,
            'errors': errors,
            'duration_ms': round(duration_ms, 2)
        }
