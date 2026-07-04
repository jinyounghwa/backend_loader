import pytest
from datetime import datetime
import sys
from guardian.ml.auto_trigger_engine import AutoTriggerEngine, ExecutionQueue


class TestAutoTriggerEngine:
    """Auto-trigger 엔진 테스트"""

    def setup_method(self):
        """AutoTriggerEngine 초기화"""
        self.engine = AutoTriggerEngine()

    def test_auto_execute_flag_filtering(self):
        """auto_execute 플래그 필터링"""
        playbooks = [
            {'playbook_id': 'pb-001', 'auto_execute': True},
            {'playbook_id': 'pb-002', 'auto_execute': False},
            {'playbook_id': 'pb-003', 'auto_execute': True},
            {'playbook_id': 'pb-004'},  # auto_execute 없음 = False
        ]

        # 각 playbook에 대해 should_auto_execute 확인
        assert self.engine.should_auto_execute(playbooks[0]) is True
        assert self.engine.should_auto_execute(playbooks[1]) is False
        assert self.engine.should_auto_execute(playbooks[2]) is True
        assert self.engine.should_auto_execute(playbooks[3]) is False

    def test_confidence_severity_threshold_trigger(self):
        """신뢰도/심각도 임계값 기반 자동 실행 판단"""
        playbook = {
            'playbook_id': 'pb-exfil-stop',
            'auto_execute': True,
            'confidence_threshold': 0.85,
            'severity_threshold': 7
        }

        # Case 1: 둘 다 임계값 충족
        prediction_ok = {
            'threat_type': 'Data Exfiltration',
            'confidence': 0.90,
            'severity': 8,
            'account_id': 'test',
            'timestamp': '2026-05-26T10:00:00Z'
        }
        assert self.engine.should_trigger_immediately(playbook, prediction_ok) is True

        # Case 2: 신뢰도가 임계값 미만
        prediction_low_conf = {
            'threat_type': 'Data Exfiltration',
            'confidence': 0.80,  # 0.85 미만
            'severity': 8,
            'account_id': 'test',
            'timestamp': '2026-05-26T10:00:00Z'
        }
        assert self.engine.should_trigger_immediately(playbook, prediction_low_conf) is False

        # Case 3: 심각도가 임계값 미만
        prediction_low_sev = {
            'threat_type': 'Data Exfiltration',
            'confidence': 0.90,
            'severity': 6,  # 7 미만
            'account_id': 'test',
            'timestamp': '2026-05-26T10:00:00Z'
        }
        assert self.engine.should_trigger_immediately(playbook, prediction_low_sev) is False

        # Case 4: auto_execute=False인 경우
        playbook_manual = {
            'playbook_id': 'pb-iam-revoke',
            'auto_execute': False,
            'confidence_threshold': 0.85,
            'severity_threshold': 7
        }
        assert self.engine.should_trigger_immediately(playbook_manual, prediction_ok) is False

    def test_manual_approval_separation(self):
        """auto_execute 플래그로 자동/수동 분류"""
        recommended_playbooks = [
            {
                'playbook_id': 'pb-ssh-block',
                'name': 'Block SSH',
                'auto_execute': True,
                'priority': 1
            },
            {
                'playbook_id': 'pb-ssh-isolate',
                'name': 'Isolate Instance',
                'auto_execute': False,
                'priority': 2
            },
            {
                'playbook_id': 'pb-unknown-region-block',
                'name': 'Block Unknown Region',
                'auto_execute': True,
                'priority': 1
            },
            {
                'playbook_id': 'pb-iam-revoke',
                'name': 'Revoke IAM',
                'auto_execute': False,
                'priority': 1
            }
        ]

        auto_list, manual_list = self.engine.separate_playbooks(recommended_playbooks)

        # 자동 실행 Playbook 확인
        assert len(auto_list) == 2
        assert auto_list[0]['playbook_id'] == 'pb-ssh-block'
        assert auto_list[1]['playbook_id'] == 'pb-unknown-region-block'

        # 수동 승인 Playbook 확인
        assert len(manual_list) == 2
        assert manual_list[0]['playbook_id'] == 'pb-ssh-isolate'
        assert manual_list[1]['playbook_id'] == 'pb-iam-revoke'

    def test_priority_queue_ordering(self):
        """우선순위별 실행 큐 정렬"""
        auto_playbooks = [
            {
                'playbook_id': 'pb-002',
                'priority': 2,
                'match_score': 0.75,
                'auto_execute': True
            },
            {
                'playbook_id': 'pb-001-a',
                'priority': 1,
                'match_score': 0.90,
                'auto_execute': True
            },
            {
                'playbook_id': 'pb-003',
                'priority': 3,
                'match_score': 0.65,
                'auto_execute': True
            },
            {
                'playbook_id': 'pb-001-b',
                'priority': 1,
                'match_score': 0.80,
                'auto_execute': True
            }
        ]

        queue = self.engine.create_execution_queue(auto_playbooks)

        # 큐 크기 확인
        assert queue.size() == 4

        # 우선순위 순서 확인: 1, 1, 2, 3
        # 같은 priority 내에서는 match_score 내림차순
        pb1 = queue.dequeue()
        assert pb1['playbook_id'] == 'pb-001-a'  # priority 1, score 0.90
        assert pb1['priority'] == 1

        pb2 = queue.dequeue()
        assert pb2['playbook_id'] == 'pb-001-b'  # priority 1, score 0.80
        assert pb2['priority'] == 1

        pb3 = queue.dequeue()
        assert pb3['playbook_id'] == 'pb-002'  # priority 2
        assert pb3['priority'] == 2

        pb4 = queue.dequeue()
        assert pb4['playbook_id'] == 'pb-003'  # priority 3
        assert pb4['priority'] == 3

        # 큐가 비어있는지 확인
        assert queue.is_empty() is True
        assert queue.dequeue() is None

    def test_throttle_duplicate_execution(self):
        """5초 내 중복 실행 방지 (스로틀링)"""
        playbook_id = 'pb-ssh-block'

        # 첫 번째 실행: 가능해야 함
        assert self.engine.can_execute_now(playbook_id) is True

        # 즉시 두 번째 실행 시도: 스로틀링되어야 함 (5초 미만)
        assert self.engine.can_execute_now(playbook_id) is False
        assert self.engine.can_execute_now(playbook_id) is False

        # 스로틀링 상태 초기화 (테스트용)
        self.engine.reset_throttle(playbook_id)

        # 초기화 후 다시 실행 가능해야 함
        assert self.engine.can_execute_now(playbook_id) is True


class TestExecutionQueue:
    """ExecutionQueue 테스트"""

    def setup_method(self):
        """ExecutionQueue 초기화"""
        self.queue = ExecutionQueue()

    def test_queue_enqueue_dequeue(self):
        """큐에 추가 및 제거"""
        playbook1 = {'playbook_id': 'pb-001', 'priority': 1, 'match_score': 0.9}
        playbook2 = {'playbook_id': 'pb-002', 'priority': 2, 'match_score': 0.8}

        # 큐에 추가
        self.queue.enqueue(playbook1)
        assert self.queue.size() == 1

        self.queue.enqueue(playbook2)
        assert self.queue.size() == 2

        # 우선순위 순서로 제거
        retrieved1 = self.queue.dequeue()
        assert retrieved1['playbook_id'] == 'pb-001'
        assert self.queue.size() == 1

        retrieved2 = self.queue.dequeue()
        assert retrieved2['playbook_id'] == 'pb-002'
        assert self.queue.size() == 0

        # 빈 큐에서 제거 시도
        assert self.queue.dequeue() is None

    def test_queue_peek(self):
        """큐 내용 조회 (제거 없음)"""
        playbook = {'playbook_id': 'pb-001', 'priority': 1, 'match_score': 0.9}

        self.queue.enqueue(playbook)

        # peek은 제거하지 않음
        peeked = self.queue.peek()
        assert peeked['playbook_id'] == 'pb-001'
        assert self.queue.size() == 1

        # 다시 peek하면 동일한 항목
        peeked2 = self.queue.peek()
        assert peeked2['playbook_id'] == 'pb-001'

    def test_queue_is_empty(self):
        """큐 비어있음 확인"""
        assert self.queue.is_empty() is True

        playbook = {'playbook_id': 'pb-001', 'priority': 1, 'match_score': 0.9}
        self.queue.enqueue(playbook)
        assert self.queue.is_empty() is False

        self.queue.dequeue()
        assert self.queue.is_empty() is True

    def test_queue_priority_sorting(self):
        """우선순위 정렬 확인"""
        # 순서대로 추가: 3, 1, 2 (정렬 후: 1, 2, 3)
        self.queue.enqueue({'playbook_id': 'pb-003', 'priority': 3, 'match_score': 0.7})
        self.queue.enqueue({'playbook_id': 'pb-001', 'priority': 1, 'match_score': 0.9})
        self.queue.enqueue({'playbook_id': 'pb-002', 'priority': 2, 'match_score': 0.8})

        # 우선순위 순서로 제거됨
        assert self.queue.dequeue()['playbook_id'] == 'pb-001'
        assert self.queue.dequeue()['playbook_id'] == 'pb-002'
        assert self.queue.dequeue()['playbook_id'] == 'pb-003'
