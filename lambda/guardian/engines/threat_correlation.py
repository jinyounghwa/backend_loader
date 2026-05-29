"""Threat Correlation Engine - Correlate threats across resources and accounts."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict


class ThreatCorrelationEngine:
    """Correlate and analyze threat patterns across resources."""

    def __init__(self, audit_logger):
        """Initialize threat correlation engine."""
        self.audit = audit_logger

    def correlate_by_signature(self, threats: List[Dict], signature_field: str = 'threat_signature') -> Dict:
        """
        Correlate threats by signature (same attacker/tools).

        Args:
            threats: List of threat records
            signature_field: Field name for threat signature

        Returns:
            {
                'signature_groups': {
                    'signature-hash': {
                        'signature': str,
                        'count': int,
                        'threats': [threat_id, ...],
                        'first_seen': datetime,
                        'last_seen': datetime,
                        'severity_range': {'min': int, 'max': int}
                    }
                },
                'top_signatures': [
                    {
                        'signature': str,
                        'count': int,
                        'threat_count': int
                    }
                ]
            }
        """
        signature_groups = defaultdict(lambda: {
            'count': 0,
            'threats': [],
            'timestamps': [],
            'severities': []
        })

        for threat in threats:
            sig = threat.get(signature_field, 'unknown')
            signature_groups[sig]['count'] += 1
            signature_groups[sig]['threats'].append(threat.get('threat_id'))
            signature_groups[sig]['timestamps'].append(threat.get('timestamp', ''))
            signature_groups[sig]['severities'].append(threat.get('severity', 5))
            signature_groups[sig]['signature'] = sig

        # Sort by count
        top_sigs = sorted(
            [
                {
                    'signature': data['signature'],
                    'count': data['count'],
                    'threat_count': len(data['threats'])
                }
                for data in signature_groups.values()
            ],
            key=lambda x: x['count'],
            reverse=True
        )

        return {
            'signature_groups': {
                sig: {
                    'signature': data['signature'],
                    'count': data['count'],
                    'threats': data['threats'],
                    'first_seen': min(data['timestamps']) if data['timestamps'] else None,
                    'last_seen': max(data['timestamps']) if data['timestamps'] else None,
                    'severity_range': {
                        'min': min(data['severities']) if data['severities'] else 0,
                        'max': max(data['severities']) if data['severities'] else 0
                    }
                }
                for sig, data in signature_groups.items()
            },
            'top_signatures': top_sigs,
            'total_signatures': len(signature_groups),
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def correlate_across_resources(self, threats: List[Dict]) -> Dict:
        """
        Correlate threats across multiple resources (EC2 → S3 → IAM chain).

        Args:
            threats: List of threat records with resource information

        Returns:
            {
                'resource_chains': [
                    {
                        'chain_id': str,
                        'resources': [
                            {'type': 'ec2', 'id': str},
                            {'type': 's3', 'id': str},
                            {'type': 'iam', 'id': str}
                        ],
                        'threat_count': int,
                        'severity': int,
                        'blast_radius': int
                    }
                ],
                'multi_resource_threats': int,
                'single_resource_threats': int
            }
        """
        resource_chains = defaultdict(lambda: {
            'resources': set(),
            'threats': [],
            'severities': []
        })

        for threat in threats:
            # Extract all involved resources
            resources = []
            if threat.get('instance_id'):
                resources.append(('ec2', threat['instance_id']))
            if threat.get('bucket_id'):
                resources.append(('s3', threat['bucket_id']))
            if threat.get('principal'):
                resources.append(('iam', threat['principal']))
            if threat.get('vpc_id'):
                resources.append(('network', threat['vpc_id']))

            # Create chain signature
            chain_sig = tuple(sorted(resources))
            resource_chains[chain_sig]['resources'].update(resources)
            resource_chains[chain_sig]['threats'].append(threat.get('threat_id'))
            resource_chains[chain_sig]['severities'].append(threat.get('severity', 5))

        # Format results
        chains = []
        multi_resource_count = 0
        single_resource_count = 0

        for i, (chain_sig, data) in enumerate(resource_chains.items()):
            resource_list = [
                {'type': res[0], 'id': res[1]}
                for res in data['resources']
            ]

            chain = {
                'chain_id': f"CHAIN-{i:04d}",
                'resources': resource_list,
                'threat_count': len(data['threats']),
                'severity': max(data['severities']) if data['severities'] else 0,
                'blast_radius': len(data['resources'])
            }
            chains.append(chain)

            if len(resource_list) > 1:
                multi_resource_count += len(data['threats'])
            else:
                single_resource_count += len(data['threats'])

        # Sort by threat count
        chains.sort(key=lambda x: x['threat_count'], reverse=True)

        return {
            'resource_chains': chains,
            'multi_resource_threats': multi_resource_count,
            'single_resource_threats': single_resource_count,
            'total_chains': len(chains),
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def analyze_timeline(self, threats: List[Dict], time_window_minutes: int = 60) -> Dict:
        """
        Analyze threat timeline and event sequences.

        Args:
            threats: List of threat records with timestamps
            time_window_minutes: Window size for temporal correlation

        Returns:
            {
                'event_sequences': [
                    {
                        'sequence_id': str,
                        'events': [
                            {'threat_id': str, 'timestamp': str, 'type': str, 'severity': int}
                        ],
                        'time_span_seconds': int,
                        'correlation_score': float
                    }
                ],
                'suspicious_bursts': [
                    {
                        'burst_id': str,
                        'threat_count': int,
                        'start_time': str,
                        'end_time': str,
                        'intensity': float
                    }
                ]
            }
        """
        # Sort threats by timestamp
        sorted_threats = sorted(
            threats,
            key=lambda x: x.get('timestamp', ''),
            reverse=False
        )

        # Find sequences
        sequences = []
        current_sequence = []
        window_start = None

        for threat in sorted_threats:
            threat_time = datetime.fromisoformat(threat.get('timestamp', datetime.now(timezone.utc).replace(tzinfo=None).isoformat()))

            if not current_sequence:
                current_sequence = [threat]
                window_start = threat_time
            else:
                time_diff = (threat_time - window_start).total_seconds() / 60

                if time_diff <= time_window_minutes:
                    current_sequence.append(threat)
                else:
                    # Save sequence and start new one
                    if len(current_sequence) > 1:
                        sequences.append(current_sequence)
                    current_sequence = [threat]
                    window_start = threat_time

        # Don't forget last sequence
        if len(current_sequence) > 1:
            sequences.append(current_sequence)

        # Format sequences
        formatted_sequences = []
        for i, seq in enumerate(sequences):
            events = [
                {
                    'threat_id': t.get('threat_id'),
                    'timestamp': t.get('timestamp'),
                    'type': t.get('threat_type', 'Unknown'),
                    'severity': t.get('severity', 0)
                }
                for t in seq
            ]

            first_time = datetime.fromisoformat(seq[0].get('timestamp', ''))
            last_time = datetime.fromisoformat(seq[-1].get('timestamp', ''))
            time_span = (last_time - first_time).total_seconds()

            # Correlation score based on event similarity
            avg_severity = sum(t.get('severity', 0) for t in seq) / len(seq)
            correlation_score = (len(seq) / 10.0) * (avg_severity / 10.0)  # 0-1 scale

            formatted_sequences.append({
                'sequence_id': f"SEQ-{i:04d}",
                'events': events,
                'time_span_seconds': int(time_span),
                'correlation_score': round(min(1.0, correlation_score), 2)
            })

        # Find suspicious bursts (high event density)
        bursts = []
        if sorted_threats:
            # Check every hour window
            current_window_start = datetime.fromisoformat(sorted_threats[0].get('timestamp', ''))
            burst_events = []

            for threat in sorted_threats:
                threat_time = datetime.fromisoformat(threat.get('timestamp', ''))
                if (threat_time - current_window_start).total_seconds() <= 3600:
                    burst_events.append(threat)
                else:
                    # Check if burst was suspicious
                    if len(burst_events) > 5:  # More than 5 events in 1 hour
                        burst_start = datetime.fromisoformat(burst_events[0].get('timestamp', ''))
                        burst_end = datetime.fromisoformat(burst_events[-1].get('timestamp', ''))
                        intensity = len(burst_events) / ((burst_end - burst_start).total_seconds() / 60 + 1)

                        bursts.append({
                            'burst_id': f"BURST-{len(bursts):04d}",
                            'threat_count': len(burst_events),
                            'start_time': burst_start.isoformat(),
                            'end_time': burst_end.isoformat(),
                            'intensity': round(intensity, 2)
                        })

                    current_window_start = threat_time
                    burst_events = [threat]

            # Check final window
            if len(burst_events) > 5:
                burst_start = datetime.fromisoformat(burst_events[0].get('timestamp', ''))
                burst_end = datetime.fromisoformat(burst_events[-1].get('timestamp', ''))
                intensity = len(burst_events) / ((burst_end - burst_start).total_seconds() / 60 + 1)

                bursts.append({
                    'burst_id': f"BURST-{len(bursts):04d}",
                    'threat_count': len(burst_events),
                    'start_time': burst_start.isoformat(),
                    'end_time': burst_end.isoformat(),
                    'intensity': round(intensity, 2)
                })

        return {
            'event_sequences': formatted_sequences,
            'suspicious_bursts': bursts,
            'total_sequences': len(formatted_sequences),
            'total_bursts': len(bursts),
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

    def assess_blast_radius(self, threat: Dict, resource_chain: Dict) -> Dict:
        """
        Assess how many resources are affected by a threat.

        Args:
            threat: Single threat record
            resource_chain: Resource chain from correlate_across_resources

        Returns:
            {
                'threat_id': str,
                'affected_resources': int,
                'affected_services': [str],
                'blast_radius_score': float (0-10),
                'risk_level': 'low|medium|high|critical',
                'estimated_impact': str,
                'recommendations': [str]
            }
        """
        resources = resource_chain.get('resources', [])
        affected_count = len(resources)
        severity = threat.get('severity', 5)

        # Determine blast radius score
        # Max 10 points: 5 for resource count, 5 for severity
        radius_score = min(10.0, (affected_count / 5.0) * 5 + (severity / 10.0) * 5)

        # Identify affected services
        affected_services = set()
        for resource in resources:
            service = resource.get('type', 'unknown')
            affected_services.add(service)

        # Determine risk level
        if radius_score >= 8 and severity >= 8:
            risk_level = 'critical'
        elif radius_score >= 6 or severity >= 8:
            risk_level = 'high'
        elif radius_score >= 4:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        # Impact estimate
        if affected_count >= 5:
            impact = f"Critical: {affected_count} resources affected across {len(affected_services)} services"
        elif affected_count >= 3:
            impact = f"Major: {affected_count} resources affected"
        elif affected_count >= 1:
            impact = f"Moderate: {affected_count} resource affected"
        else:
            impact = "Minor: Isolated threat"

        # Recommendations
        recommendations = []
        if affected_count >= 5:
            recommendations.append("Immediately isolate all affected resources")
            recommendations.append("Escalate to incident response team")
        if severity >= 8:
            recommendations.append("Consider full system scan for lateral movement")
        if 'iam' in affected_services:
            recommendations.append("Audit all IAM permissions and revoke suspicious access")
        if 's3' in affected_services:
            recommendations.append("Review S3 bucket policies and access logs")
        if 'ec2' in affected_services:
            recommendations.append("Terminate compromised instances")

        return {
            'threat_id': threat.get('threat_id'),
            'affected_resources': affected_count,
            'affected_services': sorted(list(affected_services)),
            'blast_radius_score': round(radius_score, 2),
            'risk_level': risk_level,
            'estimated_impact': impact,
            'recommendations': recommendations,
            'timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }
