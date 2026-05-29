import json
import boto3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from decimal import Decimal
import uuid


class PatternRecognitionService:
    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.threats_table = self.dynamodb.Table('guardian-threats')
        self.patterns = {}

    def identify_patterns(self, threats: List[Dict], min_support: float = 0.3) -> Dict:
        """
        Apriori 알고리즘으로 위협 시퀀스 패턴 감지

        Args:
            threats: 시간순 정렬된 위협 목록
            min_support: 최소 지지도 (0-1)

        Returns:
            {
                'patterns': [...],
                'total_patterns': int,
                'timestamp': str
            }
        """
        if not threats or len(threats) < 2:
            return {
                'patterns': [],
                'total_patterns': 0,
                'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            }

        # 위협 시퀀스 생성
        sorted_threats = sorted(threats, key=lambda t: t.get('timestamp', ''))
        threat_sequence = [t.get('threat_type', 'unknown') for t in sorted_threats]

        # 2-itemsets 찾기 (연속된 위협 쌍)
        pairs = self._find_frequent_pairs(threat_sequence, min_support)

        # 3-itemsets 찾기
        triplets = self._find_frequent_triplets(threat_sequence, pairs, min_support)

        all_itemsets = pairs + triplets

        patterns = []
        for itemset in all_itemsets:
            pattern = self._build_pattern(itemset, threat_sequence, threats)
            if pattern:
                patterns.append(pattern)

        patterns.sort(key=lambda p: p['lift'], reverse=True)

        return {
            'patterns': patterns,
            'total_patterns': len(patterns),
            'threat_count': len(threat_sequence),
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def match_pattern(self, threat_sequence: List[str], patterns: List[Dict]) -> Dict:
        """현재 위협 시퀀스가 기존 패턴과 매칭되는지 확인"""
        matched_patterns = []

        for pattern in patterns:
            pattern_sequence = pattern.get('sequence', [])
            confidence = self._calculate_sequence_confidence(threat_sequence, pattern_sequence)

            if confidence > 0.7:
                matched_patterns.append({
                    'pattern_id': pattern.get('id'),
                    'pattern_sequence': pattern_sequence,
                    'confidence': float(confidence),
                    'match_position': self._find_match_position(threat_sequence, pattern_sequence)
                })

        matched_patterns.sort(key=lambda p: p['confidence'], reverse=True)

        return {
            'current_sequence': threat_sequence,
            'matched_patterns': matched_patterns,
            'pattern_count': len(matched_patterns),
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def get_pattern_stats(self, pattern_id: str, threats: List[Dict]) -> Dict:
        """패턴 통계"""
        matching_threats = [t for t in threats if t.get('pattern_id') == pattern_id]

        if not matching_threats:
            return {
                'pattern_id': pattern_id,
                'occurrence_count': 0,
                'avg_severity': 0.0
            }

        severity_scores = [t.get('severity', 0) for t in matching_threats]
        avg_severity = sum(severity_scores) / len(severity_scores) if severity_scores else 0.0

        return {
            'pattern_id': pattern_id,
            'occurrence_count': len(matching_threats),
            'avg_severity': float(avg_severity),
            'first_seen': min(matching_threats, key=lambda t: t.get('timestamp', '')).get('timestamp', ''),
            'last_seen': max(matching_threats, key=lambda t: t.get('timestamp', '')).get('timestamp', ''),
            'remediation_rate': self._calculate_remediation_rate(matching_threats)
        }

    def _find_frequent_pairs(self, threat_sequence: List[str], min_support: float) -> List[Tuple]:
        """2-itemsets 찾기"""
        pair_counts = {}
        total_windows = len(threat_sequence) - 1

        for i in range(total_windows):
            pair = (threat_sequence[i], threat_sequence[i + 1])
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

        frequent_pairs = []
        for pair, count in pair_counts.items():
            support = count / total_windows
            if support >= min_support:
                frequent_pairs.append(pair)

        return frequent_pairs

    def _find_frequent_triplets(self, threat_sequence: List[str], pairs: List[Tuple],
                                min_support: float) -> List[Tuple]:
        """3-itemsets 찾기"""
        triplet_counts = {}
        total_windows = len(threat_sequence) - 2

        if total_windows <= 0:
            return []

        for i in range(total_windows):
            triplet = (threat_sequence[i], threat_sequence[i + 1], threat_sequence[i + 2])
            triplet_counts[triplet] = triplet_counts.get(triplet, 0) + 1

        frequent_triplets = []
        for triplet, count in triplet_counts.items():
            support = count / total_windows
            if support >= min_support:
                frequent_triplets.append(triplet)

        return frequent_triplets

    def _build_pattern(self, itemset: Tuple, threat_sequence: List[str],
                      threats: List[Dict]) -> Optional[Dict]:
        """패턴 객체 구성"""
        itemset_list = list(itemset)
        occurrences = self._count_itemset_occurrences(itemset, threat_sequence)
        total_windows = len(threat_sequence) - (len(itemset) - 1)

        if total_windows <= 0:
            return None

        support = occurrences / total_windows

        # Confidence 계산: P(itemset[1:] | itemset[:-1])
        prefix = tuple(itemset_list[:-1])
        suffix = tuple(itemset_list[-1:])

        prefix_count = self._count_itemset_occurrences(prefix, threat_sequence)
        confidence = occurrences / prefix_count if prefix_count > 0 else 0.0

        # Lift 계산
        suffix_count = self._count_itemset_occurrences(suffix, threat_sequence)
        expected_confidence = (suffix_count / total_windows) if total_windows > 0 else 0.0
        lift = confidence / expected_confidence if expected_confidence > 0 else 0.0

        # 평균 심각도 계산
        matching_threats = self._find_threats_matching_sequence(itemset, threats)
        avg_severity = sum(t.get('severity', 0) for t in matching_threats) / len(matching_threats) if matching_threats else 0.0

        return {
            'id': str(uuid.uuid4()),
            'sequence': itemset_list,
            'support': float(support),
            'confidence': float(confidence),
            'lift': float(lift),
            'occurrences': occurrences,
            'avg_severity': float(avg_severity),
            'created_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def _count_itemset_occurrences(self, itemset: Tuple, threat_sequence: List[str]) -> int:
        """itemset이 threat_sequence에서 나타나는 횟수"""
        if len(itemset) == 1:
            return threat_sequence.count(itemset[0])

        itemset_list = list(itemset)
        window_size = len(itemset_list)
        count = 0

        for i in range(len(threat_sequence) - window_size + 1):
            window = threat_sequence[i:i + window_size]
            if window == itemset_list:
                count += 1

        return count

    def _calculate_sequence_confidence(self, current_seq: List[str], pattern_seq: List[str]) -> float:
        """현재 시퀀스가 패턴 시퀀스와 얼마나 일치하는지 (0-1)"""
        if not pattern_seq:
            return 0.0

        pattern_len = len(pattern_seq)
        if pattern_len > len(current_seq):
            return 0.0

        # 슬라이딩 윈도우로 최고 일치도 찾기
        max_match = 0.0

        for i in range(len(current_seq) - pattern_len + 1):
            window = current_seq[i:i + pattern_len]
            matches = sum(1 for a, b in zip(window, pattern_seq) if a == b)
            match_rate = matches / pattern_len
            max_match = max(max_match, match_rate)

        return float(max_match)

    def _find_match_position(self, current_seq: List[str], pattern_seq: List[str]) -> int:
        """패턴이 매칭되는 시작 위치 (-1이면 매칭 안 됨)"""
        pattern_len = len(pattern_seq)

        for i in range(len(current_seq) - pattern_len + 1):
            window = current_seq[i:i + pattern_len]
            if window == pattern_seq:
                return i

        return -1

    def _find_threats_matching_sequence(self, itemset: Tuple, threats: List[Dict]) -> List[Dict]:
        """itemset과 일치하는 위협들 찾기"""
        itemset_list = list(itemset)
        threat_types = [t.get('threat_type', 'unknown') for t in threats]

        matching_threats = []
        window_size = len(itemset_list)

        for i in range(len(threat_types) - window_size + 1):
            window = threat_types[i:i + window_size]
            if window == itemset_list:
                matching_threats.extend(threats[i:i + window_size])

        return matching_threats

    def _calculate_remediation_rate(self, threats: List[Dict]) -> float:
        """위협 대응 성공률"""
        if not threats:
            return 0.0

        remediated = sum(1 for t in threats if t.get('remediated', False))
        return float(remediated / len(threats))
