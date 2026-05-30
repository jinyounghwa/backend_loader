"""SIEM integration tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestSplunkIntegration:
    """Test Splunk event integration."""

    def test_send_threat_to_splunk(self):
        """✅ Send threat event to Splunk."""
        from guardian.integrations.siem_connectors import SplunkIntegration

        splunk = SplunkIntegration(hec_token='test-token-123')

        result = splunk.send_event({
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL',
            'source': 'aws-guardian',
            'threat_id': 'threat-001'
        })

        assert result['status'] == 'sent'
        assert 'event_id' in result

    def test_send_cost_alert_to_splunk(self):
        """✅ Send cost anomaly alert to Splunk."""
        from guardian.integrations.siem_connectors import SplunkIntegration

        splunk = SplunkIntegration(hec_token='test-token-123')

        result = splunk.send_event({
            'event_type': 'COST_ANOMALY',
            'severity': 'HIGH',
            'daily_cost': 250.50,
            'threshold': 100.00
        })

        assert result['status'] == 'sent'
        assert result['event_type'] == 'COST_ANOMALY'

    def test_splunk_batch_events(self):
        """✅ Send batch events to Splunk."""
        from guardian.integrations.siem_connectors import SplunkIntegration

        splunk = SplunkIntegration(hec_token='test-token-123')

        events = [
            {'event_type': 'THREAT_DETECTED', 'severity': 'CRITICAL'},
            {'event_type': 'COST_ANOMALY', 'severity': 'HIGH'},
            {'event_type': 'CONFIG_CHANGE', 'severity': 'MEDIUM'}
        ]

        result = splunk.send_batch(events)

        assert result['status'] == 'sent'
        assert result['event_count'] == 3


class TestELKIntegration:
    """Test ELK Stack integration."""

    def test_elk_index_creation(self):
        """✅ Create ELK index for events."""
        from guardian.integrations.siem_connectors import ELKIntegration

        elk = ELKIntegration(es_host='localhost:9200')

        index = elk.create_index('aws-guardian-events')

        assert index['status'] == 'created'
        assert index['index_name'] == 'aws-guardian-events'

    def test_send_event_to_elk(self):
        """✅ Send event to ELK."""
        from guardian.integrations.siem_connectors import ELKIntegration
        from datetime import timezone

        elk = ELKIntegration(es_host='localhost:9200')

        result = elk.send_event({
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        assert result['status'] == 'indexed'
        assert 'document_id' in result

    def test_elk_query_events(self):
        """✅ Query events from ELK."""
        from guardian.integrations.siem_connectors import ELKIntegration

        elk = ELKIntegration(es_host='localhost:9200')

        query_result = elk.query({
            'index': 'aws-guardian-events',
            'query': 'severity:CRITICAL',
            'limit': 100
        })

        assert 'results' in query_result
        assert 'total_hits' in query_result


class TestSIEMEventParser:
    """Test event normalization for SIEM."""

    def test_parse_aws_event_to_cef(self):
        """✅ Parse AWS event to CEF format."""
        from guardian.integrations.siem_connectors import SIEMEventParser

        parser = SIEMEventParser()

        aws_event = {
            'eventName': 'StopInstances',
            'eventSource': 'ec2.amazonaws.com',
            'requestParameters': {
                'instancesSet': {'items': [{'instanceId': 'i-12345'}]}
            },
            'sourceIPAddress': '203.0.113.42'
        }

        cef_event = parser.to_cef(aws_event)

        assert 'CEF:0' in cef_event
        assert 'StopInstances' in cef_event
        assert 'ec2.amazonaws.com' in cef_event

    def test_parse_guardduty_finding(self):
        """✅ Parse GuardDuty finding to LEEF format."""
        from guardian.integrations.siem_connectors import SIEMEventParser

        parser = SIEMEventParser()

        guardduty_finding = {
            'type': 'Trojan.EC2/BitCoinTool.B!DNS',
            'severity': 8.0,
            'resource': {
                'instanceDetails': {
                    'instanceId': 'i-12345',
                    'networkInterfaces': [{'privateIpAddresses': [{'ipAddress': '10.0.0.1'}]}]
                }
            }
        }

        leef_event = parser.to_leef(guardduty_finding)

        assert 'LEEF:1' in leef_event
        assert 'BitCoinTool' in leef_event

    def test_normalize_event_fields(self):
        """✅ Normalize event fields to standard format."""
        from guardian.integrations.siem_connectors import SIEMEventParser

        parser = SIEMEventParser()

        event = {
            'eventName': 'DeleteSecurityGroup',
            'eventTime': '2026-05-30T10:00:00Z',
            'sourceIPAddress': '203.0.113.1',
            'userIdentity': {'principalId': 'user-123'}
        }

        normalized = parser.normalize(event)

        assert 'event_type' in normalized
        assert 'timestamp' in normalized
        assert 'source_ip' in normalized
        assert 'user_id' in normalized


class TestSIEMQueryBuilder:
    """Test SIEM query building."""

    def test_build_splunk_query(self):
        """✅ Build Splunk search query."""
        from guardian.integrations.siem_connectors import SIEMQueryBuilder

        builder = SIEMQueryBuilder()

        query = builder.build_splunk_query({
            'source': 'aws-guardian',
            'severity': 'CRITICAL',
            'days_back': 7
        })

        assert 'source=' in query
        assert 'severity=' in query
        assert 'earliest=' in query

    def test_build_elk_query(self):
        """✅ Build Elasticsearch query."""
        from guardian.integrations.siem_connectors import SIEMQueryBuilder

        builder = SIEMQueryBuilder()

        query = builder.build_elk_query({
            'field': 'severity',
            'value': 'CRITICAL',
            'operator': 'must'
        })

        assert 'query' in query
        assert 'bool' in query['query'] or 'match' in query

    def test_query_threat_events(self):
        """✅ Query threat events across timeline."""
        from guardian.integrations.siem_connectors import SIEMQueryBuilder

        builder = SIEMQueryBuilder()

        result = builder.search({
            'event_type': 'THREAT_DETECTED',
            'severity': ['CRITICAL', 'HIGH'],
            'hours_back': 24
        })

        assert 'query' in result
        assert 'time_range' in result


class TestSIEMIntegration:
    """End-to-end SIEM integration workflows."""

    def test_forward_threat_to_splunk(self):
        """✅ Forward threat event to Splunk."""
        from guardian.integrations.siem_connectors import (
            SplunkIntegration,
            SIEMEventParser
        )

        parser = SIEMEventParser()
        splunk = SplunkIntegration(hec_token='test-token')

        threat_event = {
            'eventName': 'UnauthorizedAPICall',
            'eventTime': '2026-05-30T10:00:00Z',
            'sourceIPAddress': '203.0.113.1'
        }

        # Parse event
        normalized = parser.normalize(threat_event)

        # Send to Splunk
        result = splunk.send_event(normalized)

        assert result['status'] == 'sent'

    def test_forward_guardduty_to_elk(self):
        """✅ Forward GuardDuty finding to ELK."""
        from guardian.integrations.siem_connectors import (
            ELKIntegration,
            SIEMEventParser
        )

        parser = SIEMEventParser()
        elk = ELKIntegration(es_host='localhost:9200')

        guardduty_finding = {
            'type': 'Trojan.EC2/BitCoinTool.B!DNS',
            'severity': 8.0,
            'resource': {'instanceDetails': {'instanceId': 'i-12345'}}
        }

        # Parse to LEEF
        leef_event = parser.to_leef(guardduty_finding)

        # Index in ELK
        result = elk.send_event({'raw_event': leef_event})

        assert result['status'] == 'indexed'

    def test_multi_siem_forwarding(self):
        """✅ Forward events to multiple SIEMs."""
        from guardian.integrations.siem_connectors import (
            SplunkIntegration,
            ELKIntegration
        )

        splunk = SplunkIntegration(hec_token='token1')
        elk = ELKIntegration(es_host='localhost:9200')

        event = {
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL'
        }

        splunk_result = splunk.send_event(event)
        elk_result = elk.send_event(event)

        assert splunk_result['status'] == 'sent'
        assert elk_result['status'] == 'indexed'

    def test_siem_event_correlation(self):
        """✅ Correlate events across SIEM sources."""
        from guardian.integrations.siem_connectors import SIEMQueryBuilder

        builder = SIEMQueryBuilder()

        # Search for correlated events
        result = builder.correlate({
            'event_types': ['THREAT_DETECTED', 'UNAUTHORIZED_ACCESS'],
            'correlation_window_minutes': 15,
            'min_events': 2
        })

        assert 'correlations' in result or 'results' in result

    def test_siem_alert_on_critical_threat(self):
        """✅ Trigger alert when critical threat detected."""
        from guardian.integrations.siem_connectors import SplunkIntegration

        splunk = SplunkIntegration(hec_token='token')

        event = {
            'event_type': 'THREAT_DETECTED',
            'severity': 'CRITICAL',
            'threat_name': 'Malware'
        }

        result = splunk.send_event(event)

        assert result['status'] == 'sent'
        assert result['severity'] == 'CRITICAL'
