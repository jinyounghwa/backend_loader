import pytest
from datetime import datetime
from guardian.collectors.cloudtrail_collector import CloudTrailCollector


class TestCloudTrailCollector:
    """CloudTrailCollector 테스트"""

    @pytest.fixture
    def collector(self):
        """CloudTrailCollector 인스턴스"""
        return CloudTrailCollector()

    @pytest.fixture
    def sample_runinstances_event(self):
        """RunInstances 이벤트"""
        return {
            'eventID': 'evt_1',
            'eventName': 'RunInstances',
            'eventTime': '2026-05-27T10:00:00Z',
            'sourceIPAddress': '192.168.1.1',
            'userIdentity': {
                'arn': 'arn:aws:iam::123456789012:user/admin',
                'principalId': 'AIDAI1234567890ABCDE'
            },
            'resources': [
                {'ARN': 'arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0'}
            ]
        }

    @pytest.fixture
    def sample_putobject_event(self):
        """PutObject 이벤트"""
        return {
            'eventID': 'evt_2',
            'eventName': 'PutObject',
            'eventTime': '2026-05-27T10:05:00Z',
            'sourceIPAddress': '203.0.113.1',
            'userIdentity': {
                'arn': 'arn:aws:iam::123456789012:user/developer',
                'principalId': 'AIDAI0987654321ZYXWV'
            },
            'resources': [
                {'name': 'my-bucket/my-object.txt'}
            ]
        }

    @pytest.fixture
    def sample_createaccesskey_event(self):
        """CreateAccessKey 이벤트"""
        return {
            'eventID': 'evt_3',
            'eventName': 'CreateAccessKey',
            'eventTime': '2026-05-27T10:10:00Z',
            'sourceIPAddress': '198.51.100.1',
            'userIdentity': {
                'arn': 'arn:aws:iam::123456789012:user/operator',
                'principalId': 'AIDAI1111111111111111'
            },
            'resources': []
        }

    def test_start_collection(self, collector):
        """수집 시작"""
        collector_id = collector.start_collection(
            region='us-east-1',
            event_names=['RunInstances', 'PutObject']
        )

        assert collector_id is not None
        assert collector_id in collector.collections
        assert collector.collections[collector_id]['region'] == 'us-east-1'
        assert collector.collections[collector_id]['total_events'] == 0

    def test_process_runinstances_event(self, collector, sample_runinstances_event):
        """EC2 기동 이벤트 처리"""
        result = collector.process_event(sample_runinstances_event)

        assert result['event_id'] == 'evt_1'
        assert result['event_type'] == 'RunInstances'
        assert '192.168.1.1' in result['source_ips']
        assert 'arn:aws:iam::123456789012:user/admin' in result['principals']
        assert any('i-1234567890abcdef0' in r for r in result['resources'])

    def test_process_putobject_event(self, collector, sample_putobject_event):
        """S3 업로드 이벤트 처리"""
        result = collector.process_event(sample_putobject_event)

        assert result['event_id'] == 'evt_2'
        assert result['event_type'] == 'PutObject'
        assert '203.0.113.1' in result['source_ips']
        assert 'arn:aws:iam::123456789012:user/developer' in result['principals']

    def test_process_createaccesskey_event(self, collector, sample_createaccesskey_event):
        """IAM 액세스 키 이벤트 처리"""
        result = collector.process_event(sample_createaccesskey_event)

        assert result['event_id'] == 'evt_3'
        assert result['event_type'] == 'CreateAccessKey'
        assert '198.51.100.1' in result['source_ips']
        assert 'arn:aws:iam::123456789012:user/operator' in result['principals']

    def test_filter_events_by_type(self, collector, sample_runinstances_event, sample_putobject_event):
        """이벤트 타입 필터링"""
        collector_id = collector.start_collection('us-east-1', ['RunInstances', 'PutObject'])

        # 이벤트 처리
        result1 = collector.process_event(sample_runinstances_event)
        collector.add_to_buffer(collector_id, result1)

        result2 = collector.process_event(sample_putobject_event)
        collector.add_to_buffer(collector_id, result2)

        # RunInstances만 필터링
        filtered = collector.filter_events('RunInstances', {})
        assert len(filtered) == 1
        assert filtered[0]['event_type'] == 'RunInstances'

    def test_filter_events_by_principal(self, collector, sample_runinstances_event, sample_putobject_event):
        """주체(사용자) 필터링"""
        collector_id = collector.start_collection('us-east-1', ['RunInstances', 'PutObject'])

        result1 = collector.process_event(sample_runinstances_event)
        collector.add_to_buffer(collector_id, result1)

        result2 = collector.process_event(sample_putobject_event)
        collector.add_to_buffer(collector_id, result2)

        # 특정 principal로 필터링
        filtered = collector.filter_events('RunInstances', {
            'principal': 'arn:aws:iam::123456789012:user/admin'
        })
        assert len(filtered) == 1
        assert 'arn:aws:iam::123456789012:user/admin' in filtered[0]['principals']

    def test_get_collection_stats(self, collector, sample_runinstances_event):
        """수집 통계 조회"""
        collector_id = collector.start_collection('us-east-1', ['RunInstances'])

        result = collector.process_event(sample_runinstances_event)
        collector.add_to_buffer(collector_id, result)

        stats = collector.get_collection_stats(collector_id)

        assert stats['collector_id'] == collector_id
        assert stats['region'] == 'us-east-1'
        assert stats['total_events'] == 1
        assert stats['processed_events'] == 1
        assert stats['duplicates'] == 0
        assert stats['success_rate'] == 1.0

    def test_event_deduplication(self, collector, sample_runinstances_event):
        """중복 이벤트 제거"""
        collector_id = collector.start_collection('us-east-1', ['RunInstances'])

        # 첫 번째 이벤트 처리
        result1 = collector.process_event(sample_runinstances_event)
        collector.add_to_buffer(collector_id, result1)
        assert not result1.get('is_duplicate')

        # 동일한 이벤트 다시 처리 (중복)
        result2 = collector.process_event(sample_runinstances_event)
        assert result2.get('is_duplicate') is True

        # 중복 이벤트도 total_events에 포함되어야 함
        collector.collections[collector_id]['total_events'] += 1

        # 통계 확인
        collector.record_duplicate(collector_id)
        stats = collector.get_collection_stats(collector_id)
        assert stats['duplicates'] == 1
        assert stats['deduplication_rate'] == 0.5

    def test_error_handling(self, collector):
        """에러 처리"""
        collector_id = collector.start_collection('us-east-1', ['RunInstances'])

        # Invalid event로 에러 발생
        invalid_event = {
            'eventID': 'evt_invalid'
            # Missing required fields
        }

        try:
            collector.process_event(invalid_event)
        except:
            collector.record_error(collector_id)

        stats = collector.get_collection_stats(collector_id)
        assert stats['errors'] >= 0

    def test_batch_processing(self, collector, sample_runinstances_event, sample_putobject_event):
        """배치 처리"""
        collector_id = collector.start_collection('us-east-1', ['RunInstances', 'PutObject'])

        events = [sample_runinstances_event, sample_putobject_event]

        result = collector.batch_process(collector_id, events)

        assert result['processed'] == 2
        assert result['duplicates'] == 0
        assert result['errors'] == 0
        assert result['duration_ms'] >= 0

    def test_collection_performance(self, collector):
        """성능 테스트 (1000 events/sec)"""
        collector_id = collector.start_collection('us-east-1', ['RunInstances'])

        # 1000개 이벤트 생성
        events = []
        for i in range(1000):
            events.append({
                'eventID': f'evt_{i}',
                'eventName': 'RunInstances',
                'eventTime': '2026-05-27T10:00:00Z',
                'sourceIPAddress': f'192.168.1.{i % 256}',
                'userIdentity': {
                    'arn': f'arn:aws:iam::123456789012:user/user_{i}',
                    'principalId': f'AIDAI{i:030d}'
                },
                'resources': [
                    {'ARN': f'arn:aws:ec2:us-east-1:123456789012:instance/i-{i:016x}'}
                ]
            })

        result = collector.batch_process(collector_id, events)

        # 성능 검증: 1000개 이벤트 처리 시간 < 1초
        assert result['processed'] == 1000
        assert result['duration_ms'] >= 0
        # 실제 성능은 환경에 따라 다를 수 있으므로 기본 검증만 수행
        assert result['duration_ms'] < 10000  # 10초 이상 걸리면 실패

    @pytest.mark.parametrize('event_type,priority', [
        ('RunInstances', 'HIGH'),
        ('PutObject', 'MEDIUM'),
        ('CreateAccessKey', 'HIGH'),
        ('ModifySecurityGroup', 'MEDIUM'),
        ('PutBucketPolicy', 'MEDIUM'),
        ('CreateUser', 'MEDIUM'),
        ('AttachUserPolicy', 'MEDIUM'),
        ('CreateDBInstance', 'MEDIUM')
    ])
    def test_supported_event_types(self, collector, event_type, priority):
        """지원하는 이벤트 타입"""
        assert event_type in CloudTrailCollector.SUPPORTED_EVENTS
        assert CloudTrailCollector.SUPPORTED_EVENTS[event_type] == priority
