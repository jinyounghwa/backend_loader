"""Tests for real-time event correlation (Phase 4 of Sprint 76)."""
import pytest
from datetime import datetime, timezone


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TestEventCorrelationEngine:
    """Test event correlation engine."""

    def test_correlate_events_basic(self):
        """✅ Correlate events from multiple sources."""
        from guardian.correlation.realtime_correlation import EventCorrelationEngine

        engine = EventCorrelationEngine()
        result = engine.correlate_events({
            'events': [
                {'id': 'evt1', 'type': 'ec2_stop', 'source': 'ec2', 'timestamp': now_utc().isoformat()},
                {'id': 'evt2', 'type': 'security_alert', 'source': 'guardduty', 'timestamp': now_utc().isoformat()},
                {'id': 'evt3', 'type': 'api_call', 'source': 'cloudtrail', 'timestamp': now_utc().isoformat()}
            ],
            'window_seconds': 60
        })

        assert 'correlations' in result
        assert 'event_count' in result
        assert result['event_count'] == 3

    def test_detect_correlated_events(self):
        """✅ Detect correlated event clusters."""
        from guardian.correlation.realtime_correlation import EventCorrelationEngine

        engine = EventCorrelationEngine()
        result = engine.correlate_events({
            'events': [
                {'id': 'evt1', 'type': 'unauthorized_access', 'source': 'guardduty', 'entity': 'i-123'},
                {'id': 'evt2', 'type': 'ec2_stop', 'source': 'ec2', 'entity': 'i-123'},
                {'id': 'evt3', 'type': 'security_group_modified', 'source': 'cloudtrail', 'entity': 'sg-456'}
            ],
            'threshold': 0.7
        })

        assert 'correlated_pairs' in result or 'clusters' in result

    def test_handle_event_stream(self):
        """✅ Process continuous event stream."""
        from guardian.correlation.realtime_correlation import EventCorrelationEngine

        engine = EventCorrelationEngine()
        
        # Add events incrementally
        for i in range(5):
            result = engine.correlate_events({
                'events': [{'id': f'evt{i}', 'type': 'alert', 'source': 'source1'}],
                'stream_mode': True
            })
            assert 'status' in result


class TestTimeWindowCorrelation:
    """Test time window-based correlation."""

    def test_sliding_window_correlation(self):
        """✅ Correlate events in sliding time window."""
        from guardian.correlation.realtime_correlation import TimeWindowCorrelation

        correlator = TimeWindowCorrelation()
        events = [
            {'id': f'evt{i}', 'timestamp': i, 'type': 'alert'} for i in range(10)
        ]
        
        result = correlator.correlate_in_window({
            'events': events,
            'window_size': 5,
            'window_step': 1
        })

        assert 'windows' in result
        assert len(result['windows']) > 0

    def test_time_based_grouping(self):
        """✅ Group events by time windows."""
        from guardian.correlation.realtime_correlation import TimeWindowCorrelation

        correlator = TimeWindowCorrelation()
        result = correlator.group_by_time_window({
            'events': [
                {'id': 'evt1', 'timestamp': 1000},
                {'id': 'evt2', 'timestamp': 1100},
                {'id': 'evt3', 'timestamp': 2000},
                {'id': 'evt4', 'timestamp': 2100}
            ],
            'window_seconds': 500
        })

        assert 'groups' in result
        assert len(result['groups']) >= 2

    def test_anomalous_event_clustering(self):
        """✅ Cluster anomalous events."""
        from guardian.correlation.realtime_correlation import TimeWindowCorrelation

        correlator = TimeWindowCorrelation()
        result = correlator.cluster_events({
            'events': [
                {'id': 'evt1', 'anomaly_score': 0.2},
                {'id': 'evt2', 'anomaly_score': 0.9},
                {'id': 'evt3', 'anomaly_score': 0.85},
                {'id': 'evt4', 'anomaly_score': 0.1}
            ],
            'min_anomaly_score': 0.7
        })

        assert 'anomalous_clusters' in result or 'clusters' in result


class TestCausalAnalysis:
    """Test causal relationship analysis."""

    def test_detect_causal_chain(self):
        """✅ Detect cause-effect chains."""
        from guardian.correlation.realtime_correlation import CausalAnalysis

        analyzer = CausalAnalysis()
        result = analyzer.find_causal_chain({
            'events': [
                {'id': 'evt1', 'type': 'unauthorized_login', 'timestamp': 1000},
                {'id': 'evt2', 'type': 'data_exfiltration', 'timestamp': 1010},
                {'id': 'evt3', 'type': 'user_disabled', 'timestamp': 1020}
            ]
        })

        assert 'chains' in result or 'causal_paths' in result

    def test_root_cause_analysis(self):
        """✅ Identify root cause of incident."""
        from guardian.correlation.realtime_correlation import CausalAnalysis

        analyzer = CausalAnalysis()
        result = analyzer.identify_root_cause({
            'incident_events': [
                {'id': 'evt1', 'type': 'misconfiguration'},
                {'id': 'evt2', 'type': 'unauthorized_access'},
                {'id': 'evt3', 'type': 'data_leak'}
            ]
        })

        assert 'root_cause' in result
        assert 'confidence' in result

    def test_event_dependency_graph(self):
        """✅ Build event dependency graph."""
        from guardian.correlation.realtime_correlation import CausalAnalysis

        analyzer = CausalAnalysis()
        result = analyzer.build_dependency_graph({
            'events': [
                {'id': 'evt1', 'type': 'event_a'},
                {'id': 'evt2', 'type': 'event_b'},
                {'id': 'evt3', 'type': 'event_c'}
            ]
        })

        assert 'graph' in result or 'nodes' in result


class TestCorrelationReport:
    """Test correlation reporting."""

    def test_generate_correlation_report(self):
        """✅ Generate correlation analysis report."""
        from guardian.correlation.realtime_correlation import CorrelationReport

        reporter = CorrelationReport()
        result = reporter.generate_report({
            'events': [
                {'id': 'evt1', 'type': 'alert', 'source': 'guardduty'},
                {'id': 'evt2', 'type': 'alert', 'source': 'ec2'}
            ],
            'correlations': [{'evt1': 'evt2', 'score': 0.85}]
        })

        assert 'report' in result or 'summary' in result
        assert 'timestamp' in result

    def test_correlation_statistics(self):
        """✅ Calculate correlation statistics."""
        from guardian.correlation.realtime_correlation import CorrelationReport

        reporter = CorrelationReport()
        result = reporter.calculate_statistics({
            'total_events': 100,
            'correlated_events': 45,
            'correlation_clusters': 12
        })

        assert 'correlation_density' in result
        assert 'average_cluster_size' in result

    def test_export_correlation_data(self):
        """✅ Export correlation data."""
        from guardian.correlation.realtime_correlation import CorrelationReport

        reporter = CorrelationReport()
        result = reporter.export_data({
            'format': 'json',
            'include_graph': True,
            'include_chains': True
        })

        assert 'export_id' in result or 'status' in result


class TestRealtimeCorrelationIntegration:
    """Integration tests for real-time correlation."""

    def test_end_to_end_correlation_pipeline(self):
        """✅ Full correlation pipeline."""
        from guardian.correlation.realtime_correlation import (
            EventCorrelationEngine,
            TimeWindowCorrelation,
            CausalAnalysis,
            CorrelationReport
        )

        engine = EventCorrelationEngine()
        window_corr = TimeWindowCorrelation()
        causal = CausalAnalysis()
        reporter = CorrelationReport()

        # Step 1: Correlate events
        events = [
            {'id': 'evt1', 'type': 'unauthorized_access', 'timestamp': 1000},
            {'id': 'evt2', 'type': 'data_access', 'timestamp': 1005},
            {'id': 'evt3', 'type': 'data_exfil', 'timestamp': 1010}
        ]
        
        correlations = engine.correlate_events({'events': events})
        assert 'correlations' in correlations

    def test_multi_source_event_correlation(self):
        """✅ Correlate events from multiple AWS services."""
        from guardian.correlation.realtime_correlation import EventCorrelationEngine

        engine = EventCorrelationEngine()
        result = engine.correlate_events({
            'events': [
                {'id': 'evt1', 'source': 'guardduty', 'type': 'finding'},
                {'id': 'evt2', 'source': 'cloudtrail', 'type': 'api_call'},
                {'id': 'evt3', 'source': 'ec2', 'type': 'state_change'}
            ],
            'window_seconds': 60
        })

        assert result['event_count'] == 3

    def test_incident_timeline_reconstruction(self):
        """✅ Reconstruct incident timeline from correlated events."""
        from guardian.correlation.realtime_correlation import CausalAnalysis

        analyzer = CausalAnalysis()
        result = analyzer.find_causal_chain({
            'events': [
                {'id': 'evt1', 'type': 'initial_access', 'timestamp': 1000},
                {'id': 'evt2', 'type': 'privilege_escalation', 'timestamp': 1005},
                {'id': 'evt3', 'type': 'lateral_movement', 'timestamp': 1010},
                {'id': 'evt4', 'type': 'data_exfiltration', 'timestamp': 1015}
            ]
        })

        assert 'chains' in result or 'causal_paths' in result
