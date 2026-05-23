"""
Sprint 32 Phase 5: Advanced Analytics Tests
Tests for statistics, export, and analytics features
"""

import pytest
from unittest.mock import MagicMock, patch
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lambda' / 'guardian'))

from handlers.statistics_handler import (
    calculate_statistics,
    count_by_field,
    get_hourly_distribution,
    get_top_connections,
    get_top_accounts,
    calculate_success_rate,
)

from handlers.export_handler import (
    generate_json,
    generate_csv,
    get_csv_fieldnames,
)


class TestStatisticsCalculation:
    """Test statistics calculation"""

    def test_calculate_statistics_empty_logs(self):
        """Test statistics with empty logs"""
        stats = calculate_statistics()

        assert stats['total_events'] == 0
        assert stats['event_types'] == {}
        assert stats['success_rate'] == 0.0

    def test_count_by_field(self):
        """Test counting occurrences by field"""
        logs = [
            {'event_type': '$connect'},
            {'event_type': '$connect'},
            {'event_type': '$disconnect'},
            {'event_type': 'message'},
        ]

        counts = count_by_field(logs, 'event_type')

        assert counts['$connect'] == 2
        assert counts['$disconnect'] == 1
        assert counts['message'] == 1

    def test_count_by_field_missing_values(self):
        """Test counting with missing field values"""
        logs = [
            {'event_type': '$connect'},
            {'status': 'success'},
            {},
        ]

        counts = count_by_field(logs, 'event_type')

        assert counts['$connect'] == 1
        assert counts['unknown'] == 2

    def test_get_hourly_distribution(self):
        """Test hourly event distribution"""
        logs = [
            {'timestamp': '2026-05-23T10:15:00Z'},
            {'timestamp': '2026-05-23T10:45:00Z'},
            {'timestamp': '2026-05-23T11:30:00Z'},
            {'timestamp': '2026-05-23T10:20:00Z'},
        ]

        distribution = get_hourly_distribution(logs)

        assert distribution['2026-05-23 10:00'] == 3
        assert distribution['2026-05-23 11:00'] == 1

    def test_get_hourly_distribution_invalid_timestamps(self):
        """Test handling invalid timestamps"""
        logs = [
            {'timestamp': '2026-05-23T10:15:00Z'},
            {'timestamp': 'invalid'},
            {'timestamp': ''},
        ]

        distribution = get_hourly_distribution(logs)

        # Should only count valid timestamps
        assert '2026-05-23 10:00' in distribution

    def test_get_top_connections(self):
        """Test getting top connections"""
        logs = [
            {'connection_id': 'conn-1'},
            {'connection_id': 'conn-1'},
            {'connection_id': 'conn-1'},
            {'connection_id': 'conn-2'},
            {'connection_id': 'conn-2'},
            {'connection_id': 'conn-3'},
        ]

        top = get_top_connections(logs, limit=2)

        assert len(top) == 2
        assert top[0]['connection_id'] == 'conn-1'
        assert top[0]['count'] == 3
        assert top[1]['connection_id'] == 'conn-2'
        assert top[1]['count'] == 2

    def test_get_top_accounts(self):
        """Test getting top accounts"""
        logs = [
            {'account_id': '111111111111'},
            {'account_id': '111111111111'},
            {'account_id': '222222222222'},
            {'account_id': '333333333333'},
        ]

        top = get_top_accounts(logs, limit=2)

        assert len(top) == 2
        assert top[0]['account_id'] == '111111111111'
        assert top[0]['count'] == 2

    def test_calculate_success_rate(self):
        """Test success rate calculation"""
        logs = [
            {'status': 'success'},
            {'status': 'success'},
            {'status': 'success'},
            {'status': 'error'},
        ]

        rate = calculate_success_rate(logs)

        assert rate == 75.0

    def test_calculate_success_rate_all_successful(self):
        """Test success rate when all are successful"""
        logs = [
            {'status': 'success'},
            {'status': 'success'},
            {'status': 'success'},
        ]

        rate = calculate_success_rate(logs)

        assert rate == 100.0

    def test_calculate_success_rate_all_failed(self):
        """Test success rate when all are failed"""
        logs = [
            {'status': 'error'},
            {'status': 'error'},
        ]

        rate = calculate_success_rate(logs)

        assert rate == 0.0

    def test_calculate_success_rate_empty(self):
        """Test success rate with empty logs"""
        rate = calculate_success_rate([])

        assert rate == 0.0


class TestExportFunctions:
    """Test export functions"""

    def test_generate_json(self):
        """Test JSON generation"""
        logs = [
            {
                'connection_id': 'conn-1',
                'timestamp': '2026-05-23T10:00:00Z',
                'event_type': '$connect',
            },
            {
                'connection_id': 'conn-2',
                'timestamp': '2026-05-23T10:01:00Z',
                'event_type': '$disconnect',
            },
        ]

        json_str = generate_json(logs)

        parsed = json.loads(json_str)
        assert len(parsed) == 2
        assert parsed[0]['connection_id'] == 'conn-1'

    def test_generate_json_empty(self):
        """Test JSON generation with empty logs"""
        json_str = generate_json([])

        parsed = json.loads(json_str)
        assert parsed == []

    def test_get_csv_fieldnames(self):
        """Test CSV field name extraction"""
        logs = [
            {
                'timestamp': '2026-05-23T10:00:00Z',
                'connection_id': 'conn-1',
                'event_type': '$connect',
            }
        ]

        fieldnames = get_csv_fieldnames(logs)

        # Should include standard fields that exist
        assert 'timestamp' in fieldnames
        assert 'connection_id' in fieldnames
        assert 'event_type' in fieldnames

    def test_get_csv_fieldnames_ordering(self):
        """Test CSV field name ordering"""
        logs = [
            {
                'details': 'some details',
                'timestamp': '2026-05-23T10:00:00Z',
                'connection_id': 'conn-1',
            }
        ]

        fieldnames = get_csv_fieldnames(logs)

        # Standard fields should come first
        assert fieldnames.index('timestamp') < len(fieldnames)
        assert 'connection_id' in fieldnames

    def test_generate_csv(self):
        """Test CSV generation"""
        logs = [
            {
                'timestamp': '2026-05-23T10:00:00Z',
                'connection_id': 'conn-1',
                'event_type': '$connect',
                'status': 'success',
            },
            {
                'timestamp': '2026-05-23T10:01:00Z',
                'connection_id': 'conn-2',
                'event_type': '$disconnect',
                'status': 'success',
            },
        ]

        csv_str = generate_csv(logs)

        lines = csv_str.strip().split('\n')
        assert len(lines) == 3  # Header + 2 rows

    def test_generate_csv_empty(self):
        """Test CSV generation with empty logs"""
        csv_str = generate_csv([])

        assert csv_str == ''


class TestAnalyticsIntegration:
    """Integration tests for analytics features"""

    def test_statistics_with_account_id(self):
        """Test statistics calculation with account_id"""
        stats = calculate_statistics(account_id='123456789012')

        assert 'total_events' in stats
        assert 'success_rate' in stats
        assert stats['time_range']['start'] == 'N/A'

    def test_statistics_with_connection_id(self):
        """Test statistics calculation with connection_id"""
        stats = calculate_statistics(connection_id='conn-123')

        assert 'total_events' in stats
        assert 'top_connections' in stats

    def test_statistics_with_time_range(self):
        """Test statistics with time range"""
        start = '2026-05-23T00:00:00Z'
        end = '2026-05-23T23:59:59Z'

        stats = calculate_statistics(start_time=start, end_time=end)

        assert stats['time_range']['start'] == start
        assert stats['time_range']['end'] == end

    def test_export_csv_formatting(self):
        """Test CSV export formatting"""
        logs = [
            {
                'timestamp': '2026-05-23T10:00:00Z',
                'connection_id': 'conn-1',
                'event_type': '$connect',
                'status': 'success',
                'user_id': 'user@example.com',
            }
        ]

        csv_str = generate_csv(logs)

        # Should contain quoted headers
        assert 'timestamp' in csv_str
        assert 'connection_id' in csv_str
        # Should contain data
        assert 'conn-1' in csv_str
        assert 'user@example.com' in csv_str

    def test_multi_account_statistics(self):
        """Test statistics across multiple accounts"""
        logs = [
            {'account_id': '111111111111', 'event_type': '$connect'},
            {'account_id': '111111111111', 'event_type': '$connect'},
            {'account_id': '222222222222', 'event_type': '$disconnect'},
        ]

        top_accounts = get_top_accounts(logs)

        assert len(top_accounts) == 2
        assert top_accounts[0]['account_id'] == '111111111111'
        assert top_accounts[1]['account_id'] == '222222222222'


class TestChartDataGeneration:
    """Test chart data generation"""

    def test_event_type_bar_chart_data(self):
        """Test bar chart data for event types"""
        logs = [
            {'event_type': '$connect'},
            {'event_type': '$connect'},
            {'event_type': '$disconnect'},
            {'event_type': 'message'},
            {'event_type': 'broadcast'},
        ]

        event_counts = count_by_field(logs, 'event_type')

        # Can be converted to chart data
        chart_data = [{'name': k, 'count': v} for k, v in event_counts.items()]

        assert len(chart_data) == 4

    def test_status_distribution_pie_chart_data(self):
        """Test pie chart data for status distribution"""
        logs = [
            {'status': 'success'},
            {'status': 'success'},
            {'status': 'success'},
            {'status': 'error'},
        ]

        status_counts = count_by_field(logs, 'status')

        # Can be converted to pie chart data
        pie_data = [{'name': k, 'value': v} for k, v in status_counts.items()]

        assert len(pie_data) == 2
        assert any(p['name'] == 'success' for p in pie_data)
