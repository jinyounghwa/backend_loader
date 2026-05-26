import pytest
from datetime import datetime
import sys
sys.path.insert(0, '/Users/younghwa.jin/Documents/backend_loader/lambda')
from guardian.ml.response_mapper import ResponseMapper


class TestResponseMapping:
    """Test ML prediction → playbook mapping"""

    def setup_method(self):
        """Initialize ResponseMapper"""
        self.mapper = ResponseMapper()

    def test_prediction_to_playbook_mapping(self):
        """Test mapping threat prediction to recommended playbooks"""
        prediction = {
            'threat_type': 'Unknown Region',
            'confidence': 0.95,
            'severity': 8,
            'account_id': 'test-account',
            'timestamp': '2026-05-26T10:00:00Z'
        }

        result = self.mapper.map_prediction_to_playbook(prediction)

        assert result['threat_type'] == 'Unknown Region'
        assert result['prediction_confidence'] == 0.95
        assert result['threat_severity'] == 8
        assert len(result['recommended_playbooks']) > 0
        assert result['primary_playbook'] == 'pb-unknown-region-block'
        assert result['total_recommendations'] >= 1

    def test_cluster_based_mapping(self):
        """Test mapping threat cluster to bulk remediation playbook"""
        cluster = {
            'id': 'C1',
            'threats': ['t1', 't2', 't3'],
            'avg_severity': 7.5,
            'representative_threat_type': 'Data Exfiltration'
        }

        result = self.mapper.map_cluster_to_playbook(cluster)

        assert result['cluster_id'] == 'C1'
        assert result['representative_threat'] == 'Data Exfiltration'
        assert result['threat_count'] == 3
        assert result['avg_severity'] == 7.5
        # Severity 7.5 matches pb-exfil-investigate (threshold 7) but not pb-exfil-stop (threshold 9)
        assert result['recommended_playbook'] == 'pb-exfil-investigate'
        assert result['bulk_remediation'] is True

    def test_pattern_based_mapping(self):
        """Test mapping attack pattern to preventive playbooks"""
        pattern = {
            'id': 'P1',
            'sequence': ['Unknown Region', 'Unauthorized SSH'],
            'confidence': 0.85,
            'occurrences': 10
        }

        result = self.mapper.map_pattern_to_playbook(pattern)

        assert result['pattern_id'] == 'P1'
        assert result['pattern_sequence'] == ['Unknown Region', 'Unauthorized SSH']
        assert result['pattern_confidence'] == 0.85
        assert result['occurrences'] == 10
        assert len(result['preventive_playbooks']) > 0
        assert 'pb-unknown-region-block' in result['preventive_playbooks']
        assert result['early_intervention'] is True

    def test_confidence_score_filtering(self):
        """Test that playbooks are filtered by confidence/severity thresholds"""
        # Confidence 0.88, severity 7 - matches only lower threshold playbook
        filtered_prediction = {
            'threat_type': 'Data Exfiltration',
            'confidence': 0.88,  # Above 0.85 for pb-exfil-investigate but below 0.95 for pb-exfil-stop
            'severity': 7,       # Meets 7 threshold but below 9 for pb-exfil-stop
            'account_id': 'test-account',
            'timestamp': '2026-05-26T10:00:00Z'
        }

        result = self.mapper.map_prediction_to_playbook(filtered_prediction)

        # Should recommend pb-exfil-investigate (threshold 0.85, 7)
        assert any(pb['playbook_id'] == 'pb-exfil-investigate'
                   for pb in result['recommended_playbooks'])
        # Should NOT recommend pb-exfil-stop (threshold 0.95, 9)
        assert not any(pb['playbook_id'] == 'pb-exfil-stop'
                       for pb in result['recommended_playbooks'])

    def test_multi_playbook_recommendation(self):
        """Test that multiple playbooks are recommended when conditions match"""
        prediction = {
            'threat_type': 'Unauthorized SSH',
            'confidence': 0.92,
            'severity': 8,
            'account_id': 'test-account',
            'timestamp': '2026-05-26T10:00:00Z'
        }

        result = self.mapper.map_prediction_to_playbook(prediction)

        # Should recommend both pb-ssh-block and pb-ssh-isolate
        assert len(result['recommended_playbooks']) >= 2
        playbook_ids = [pb['playbook_id'] for pb in result['recommended_playbooks']]
        assert 'pb-ssh-block' in playbook_ids
        assert 'pb-ssh-isolate' in playbook_ids

        # pb-ssh-block should be primary (priority 1 > 2)
        assert result['primary_playbook'] == 'pb-ssh-block'

    def test_match_score_calculation(self):
        """Test match score calculation with confidence and severity"""
        prediction = {
            'threat_type': 'Permission Escalation',
            'confidence': 0.95,  # High confidence
            'severity': 9,       # High severity
            'account_id': 'test-account',
            'timestamp': '2026-05-26T10:00:00Z'
        }

        result = self.mapper.map_prediction_to_playbook(prediction)

        # Should have match score > 0.5 due to high confidence and severity
        assert result['recommended_playbooks'][0]['match_score'] > 0.5

    def test_playbook_details_retrieval(self):
        """Test retrieving full playbook details by ID"""
        playbook = self.mapper.get_playbook_details('pb-ssh-block')

        assert playbook is not None
        assert playbook['playbook_id'] == 'pb-ssh-block'
        assert playbook['type'] == 'security_group_update'
        assert playbook['severity_threshold'] == 6
        assert playbook['confidence_threshold'] == 0.80
        assert playbook['auto_execute'] is True

    def test_unknown_threat_type_handling(self):
        """Test handling of unknown threat types"""
        prediction = {
            'threat_type': 'Unknown Threat Type',
            'confidence': 0.90,
            'severity': 5,
            'account_id': 'test-account',
            'timestamp': '2026-05-26T10:00:00Z'
        }

        result = self.mapper.map_prediction_to_playbook(prediction)

        assert result['threat_type'] == 'Unknown Threat Type'
        assert result['recommended_playbooks'] == []
        assert result['primary_playbook'] is None
        assert result['total_recommendations'] == 0
