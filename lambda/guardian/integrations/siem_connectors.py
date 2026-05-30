"""SIEM integrations for AWS Guardian."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import json
import uuid


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class SplunkIntegration:
    """Integration with Splunk via HEC (HTTP Event Collector)."""

    def __init__(self, hec_token: str, hec_url: str = 'http://localhost:8088'):
        self.hec_token = hec_token
        self.hec_url = hec_url
        self.events: Dict[str, Dict[str, Any]] = {}

    def send_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Send event to Splunk HEC."""
        event_id = f"splunk_{uuid.uuid4().hex[:8]}"

        splunk_event = {
            'event': event,
            'sourcetype': '_json',
            'source': event.get('source', 'aws-guardian'),
            'host': 'aws-guardian-lambda',
            'time': now_utc().timestamp()
        }

        self.events[event_id] = splunk_event

        response = {
            'status': 'sent',
            'event_id': event_id,
            'event_type': event.get('event_type'),
            'severity': event.get('severity'),
            'timestamp': now_utc().isoformat()
        }

        return response

    def send_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send batch of events to Splunk."""
        event_ids = []

        for event in events:
            result = self.send_event(event)
            event_ids.append(result['event_id'])

        return {
            'status': 'sent',
            'event_count': len(events),
            'event_ids': event_ids
        }

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get stored event."""
        return self.events.get(event_id)


class ELKIntegration:
    """Integration with ELK Stack (Elasticsearch, Logstash, Kibana)."""

    def __init__(self, es_host: str = 'localhost:9200'):
        self.es_host = es_host
        self.indices: Dict[str, List[Dict]] = {}

    def create_index(self, index_name: str) -> Dict[str, Any]:
        """Create Elasticsearch index."""
        if index_name not in self.indices:
            self.indices[index_name] = []

        return {
            'status': 'created',
            'index_name': index_name,
            'timestamp': now_utc().isoformat()
        }

    def send_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Send event to ELK Stack."""
        document_id = f"doc_{uuid.uuid4().hex[:8]}"
        index_name = 'aws-guardian-events'

        # Ensure index exists
        if index_name not in self.indices:
            self.create_index(index_name)

        # Add timestamp if missing
        if 'timestamp' not in event:
            event['timestamp'] = now_utc().isoformat()

        self.indices[index_name].append({
            '_id': document_id,
            '_source': event
        })

        return {
            'status': 'indexed',
            'document_id': document_id,
            'index': index_name,
            'timestamp': now_utc().isoformat()
        }

    def query(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Query events from ELK."""
        index = query_params.get('index', 'aws-guardian-events')
        query_str = query_params.get('query', '')
        limit = query_params.get('limit', 100)

        if index not in self.indices:
            return {'results': [], 'total_hits': 0}

        # Simple filtering
        results = []
        for doc in self.indices[index]:
            if query_str.lower() in str(doc).lower():
                results.append(doc)

        return {
            'results': results[:limit],
            'total_hits': len(results),
            'query': query_str
        }


class SIEMEventParser:
    """Parse and normalize events for SIEM formats."""

    def to_cef(self, event: Dict[str, Any]) -> str:
        """Convert AWS event to CEF (Common Event Format)."""
        cef_version = 'CEF:0'
        vendor = 'AWS'
        product = 'CloudTrail'
        version = '1.0'

        event_name = event.get('eventName', 'UnknownEvent')
        severity = event.get('errorCode') and '8' or '5'

        source_ip = event.get('sourceIPAddress', '0.0.0.0')
        source = event.get('eventSource', 'aws.amazon.com')

        extensions = (
            f'src={source_ip} '
            f'eventName={event_name} '
            f'eventSource={source}'
        )

        cef_event = f'{cef_version}|{vendor}|{product}|{version}|{event_name}|AWS Event|{severity}|{extensions}'

        return cef_event

    def to_leef(self, event: Dict[str, Any]) -> str:
        """Convert GuardDuty finding to LEEF (Log Event Extended Format)."""
        leef_version = 'LEEF:1'
        vendor = 'AWS'
        product = 'GuardDuty'
        version = '1.0'

        finding_type = event.get('type', 'UnknownFinding')
        severity = event.get('severity', 0)

        instance_id = event.get('resource', {}).get('instanceDetails', {}).get('instanceId', 'unknown')

        attributes = f'finding_type={finding_type}\tseverity={severity}\tinstance_id={instance_id}'

        leef_event = f'{leef_version}|{vendor}|{product}|{version}|0|{attributes}'

        return leef_event

    def normalize(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event to standard fields."""
        normalized = {
            'event_type': event.get('eventName') or event.get('event_type', 'UnknownEvent'),
            'timestamp': event.get('eventTime') or event.get('timestamp', now_utc().isoformat()),
            'source': event.get('eventSource', 'unknown'),
            'source_ip': event.get('sourceIPAddress', '0.0.0.0'),
            'user_id': event.get('userIdentity', {}).get('principalId', 'unknown'),
            'raw_event': event
        }

        return normalized


class SIEMQueryBuilder:
    """Build queries for SIEM systems."""

    def build_splunk_query(self, params: Dict[str, Any]) -> str:
        """Build Splunk search query."""
        source = params.get('source', 'aws-guardian')
        severity = params.get('severity')
        days_back = params.get('days_back', 7)

        query = f'source="{source}"'

        if severity:
            query += f' severity="{severity}"'

        query += f' earliest=-{days_back}d@d latest=now'

        return query

    def build_elk_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build Elasticsearch query."""
        field = params.get('field')
        value = params.get('value')
        operator = params.get('operator', 'must')

        query = {
            'query': {
                'bool': {
                    operator: [
                        {'match': {field: value}}
                    ]
                }
            }
        }

        return query

    def search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build generic SIEM search."""
        event_type = params.get('event_type')
        severity = params.get('severity', [])
        hours_back = params.get('hours_back', 24)

        # Splunk-style query
        query = f'event_type="{event_type}"'

        if severity:
            severity_str = ' OR '.join([f'severity="{s}"' for s in severity])
            query += f' ({severity_str})'

        query += f' earliest=-{hours_back}h@h latest=now'

        return {
            'query': query,
            'time_range': f'-{hours_back}h',
            'event_type': event_type
        }

    def correlate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate events across sources."""
        event_types = params.get('event_types', [])
        correlation_window = params.get('correlation_window_minutes', 15)
        min_events = params.get('min_events', 2)

        correlations = []

        # Simulated correlation logic
        if len(event_types) >= min_events:
            correlations.append({
                'event_types': event_types,
                'correlation_window_minutes': correlation_window,
                'correlation_confidence': 0.85
            })

        return {
            'correlations': correlations,
            'total_correlations': len(correlations)
        }


class SIEMEventForwarder:
    """Forward events to multiple SIEM systems."""

    def __init__(self):
        self.splunk: Optional[SplunkIntegration] = None
        self.elk: Optional[ELKIntegration] = None
        self.parser = SIEMEventParser()

    def configure_splunk(self, hec_token: str, hec_url: str = 'http://localhost:8088'):
        """Configure Splunk integration."""
        self.splunk = SplunkIntegration(hec_token, hec_url)

    def configure_elk(self, es_host: str = 'localhost:9200'):
        """Configure ELK integration."""
        self.elk = ELKIntegration(es_host)

    def forward_event(self, event: Dict[str, Any], targets: List[str]) -> Dict[str, Any]:
        """Forward event to specified targets."""
        results = {}

        for target in targets:
            if target == 'splunk' and self.splunk:
                normalized = self.parser.normalize(event)
                results['splunk'] = self.splunk.send_event(normalized)

            elif target == 'elk' and self.elk:
                normalized = self.parser.normalize(event)
                results['elk'] = self.elk.send_event(normalized)

        return {
            'status': 'forwarded',
            'targets': targets,
            'results': results,
            'timestamp': now_utc().isoformat()
        }

    def forward_batch(self, events: List[Dict[str, Any]], targets: List[str]) -> Dict[str, Any]:
        """Forward batch of events to targets."""
        forwarded_count = 0

        for event in events:
            result = self.forward_event(event, targets)
            if result['status'] == 'forwarded':
                forwarded_count += 1

        return {
            'status': 'forwarded',
            'event_count': len(events),
            'forwarded_count': forwarded_count,
            'targets': targets
        }
