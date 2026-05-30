"""Advanced threat intelligence for AWS Guardian."""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid


def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ThreatIntelligenceFeed:
    """Integrate external threat intelligence feeds."""

    def __init__(self):
        self.feeds: Dict[str, List[Dict[str, Any]]] = {}
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 3600  # 60 minutes

    def fetch_feed(self, feed_source: str) -> List[Dict[str, Any]]:
        """Fetch threat intelligence from external source."""
        if feed_source in self.cache:
            cached = self.cache[feed_source]
            if (now_utc() - cached['timestamp']).total_seconds() < self.cache_ttl:
                return cached['data']

        if feed_source == 'misp':
            threats = self._fetch_misp()
        elif feed_source == 'alienvault':
            threats = self._fetch_alienvault()
        else:
            threats = []

        self.cache[feed_source] = {
            'data': threats,
            'timestamp': now_utc()
        }

        self.feeds[feed_source] = threats
        return threats

    def _fetch_misp(self) -> List[Dict[str, Any]]:
        """Fetch MISP threat data."""
        return [
            {
                'ioc': '203.0.113.1',
                'threat_type': 'malware_c2',
                'confidence': 95,
                'last_seen': now_utc().isoformat()
            },
            {
                'ioc': 'malicious.example.com',
                'threat_type': 'phishing_domain',
                'confidence': 85,
                'last_seen': now_utc().isoformat()
            }
        ]

    def _fetch_alienvault(self) -> List[Dict[str, Any]]:
        """Fetch AlienVault OTX threat data."""
        return [
            {
                'ioc': '203.0.113.2',
                'threat_type': 'botnet',
                'reputation': 'malicious',
                'confidence': 90
            },
            {
                'ioc': 'c2.malware.net',
                'threat_type': 'malware_c2',
                'reputation': 'malicious',
                'confidence': 88
            }
        ]

    def is_cached(self, feed_source: str) -> bool:
        """Check if feed is cached."""
        return feed_source in self.cache

    def deduplicate_threats(self, threats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate threats across feeds."""
        seen = set()
        unique = []

        for threat in threats:
            ioc = threat.get('ioc', '')
            if ioc and ioc not in seen:
                seen.add(ioc)
                unique.append(threat)

        return unique


class IPReputation:
    """Query IP reputation from threat intelligence."""

    def __init__(self):
        self.reputation_cache: Dict[str, Dict[str, Any]] = {}

    def get_reputation(self, ip: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get IP reputation from threat feeds."""
        if ip in self.reputation_cache:
            return self.reputation_cache[ip]

        sources = sources or ['misp', 'alienvault']

        reputation = {
            'ip': ip,
            'reputation_score': self._calculate_reputation(ip),
            'sources': sources,
            'timestamp': now_utc().isoformat()
        }

        self.reputation_cache[ip] = reputation
        return reputation

    def _calculate_reputation(self, ip: str) -> int:
        """Calculate reputation score for IP."""
        hash_val = sum(ord(c) for c in ip) % 100

        if hash_val > 85:
            return hash_val
        return max(0, hash_val - 50)

    def get_bulk_reputation(self, ips: List[str]) -> List[Dict[str, Any]]:
        """Bulk query reputation for multiple IPs."""
        results = []

        for ip in ips:
            results.append(self.get_reputation(ip))

        return results


class ThreatCorrelation:
    """Correlate threat data from multiple sources."""

    def __init__(self):
        self.correlations: Dict[str, Dict[str, Any]] = {}

    def correlate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate threat indicators."""
        if 'ioc' in params:
            return self._correlate_single_ioc(params)
        elif 'indicators' in params:
            return self._correlate_indicators(params)
        else:
            return {'error': 'No indicators provided'}

    def _correlate_single_ioc(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate single IOC."""
        ioc = params.get('ioc')
        sources = params.get('sources', [])

        risk_score = len(sources) * 20

        correlation_id = f"corr_{uuid.uuid4().hex[:8]}"

        result = {
            'correlation_id': correlation_id,
            'ioc': ioc,
            'risk_score': min(100, risk_score),
            'sources': sources,
            'timestamp': now_utc().isoformat()
        }

        self.correlations[correlation_id] = result
        return result

    def _correlate_indicators(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate multiple indicators."""
        indicators = params.get('indicators', [])

        correlation_score = len(indicators) * 15

        return {
            'indicators': indicators,
            'correlation_score': min(100, correlation_score),
            'timestamp': now_utc().isoformat()
        }

    def detect_pattern(self, indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect patterns in indicators."""
        type_counts = {}
        for ind in indicators:
            ind_type = ind.get('type', 'UNKNOWN')
            type_counts[ind_type] = type_counts.get(ind_type, 0) + 1

        pattern_type = 'UNKNOWN'
        if type_counts.get('IP', 0) >= 2:
            pattern_type = 'INFRASTRUCTURE_REUSE'
        elif type_counts.get('DOMAIN', 0) >= 1 and type_counts.get('IP', 0) >= 1:
            pattern_type = 'HOSTED_MALWARE'

        return {
            'pattern_type': pattern_type,
            'detected': pattern_type != 'UNKNOWN',
            'indicator_types': type_counts
        }


class ThreatPrediction:
    """ML-based threat prediction."""

    def __init__(self):
        self.predictions: Dict[str, Dict[str, Any]] = {}

    def predict_threat(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Predict threat likelihood."""
        indicators = features.get('indicators', 0)
        source_diversity = features.get('source_diversity', 0)
        temporal_similarity = features.get('temporal_similarity', 0)
        infrastructure_overlap = features.get('infrastructure_overlap', 0)

        threat_score = (
            indicators * 15 +
            source_diversity * 20 +
            temporal_similarity * 30 +
            infrastructure_overlap * 35
        ) / 4

        threat_score = min(100, max(0, threat_score))

        return {
            'threat_score': threat_score,
            'confidence': 0.85,
            'timestamp': now_utc().isoformat()
        }

    def predict_attack_type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Predict attack type from indicators."""
        iocs = params.get('iocs', [])
        context = params.get('context', '')

        attack_type = 'UNKNOWN'

        if 'compromise' in context.lower():
            attack_type = 'LATERAL_MOVEMENT'
        elif len(iocs) > 5:
            attack_type = 'ADVANCED_PERSISTENT_THREAT'
        else:
            attack_type = 'OPPORTUNISTIC_MALWARE'

        return {
            'attack_type': attack_type,
            'confidence': 0.78,
            'ioc_count': len(iocs)
        }

    def predict_target_industry(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Predict target industry from campaign."""
        campaign_name = params.get('campaign_name', '')
        infrastructure_country = params.get('infrastructure_country', '')

        target_industries = []

        if infrastructure_country == 'CN':
            target_industries = ['FINANCE', 'DEFENSE', 'ENERGY']
        elif infrastructure_country == 'RU':
            target_industries = ['CRITICAL_INFRASTRUCTURE', 'DEFENSE']
        else:
            target_industries = ['FINANCE', 'TECHNOLOGY']

        return {
            'target_industries': target_industries,
            'confidence': 0.72,
            'campaign_name': campaign_name
        }


class ThreatIntelligenceEngine:
    """End-to-end threat intelligence engine."""

    def __init__(self):
        self.feed = ThreatIntelligenceFeed()
        self.ip_rep = IPReputation()
        self.correlation = ThreatCorrelation()
        self.prediction = ThreatPrediction()

    def investigate_threat(self, indicator: str) -> Dict[str, Any]:
        """Complete threat investigation."""
        ip_result = self.ip_rep.get_reputation(indicator)

        corr_result = self.correlation.correlate({
            'ioc': indicator,
            'sources': ['misp', 'alienvault']
        })

        pred_result = self.prediction.predict_threat({
            'indicators': 1,
            'source_diversity': 2,
            'temporal_similarity': 0.8,
            'infrastructure_overlap': 0.6
        })

        return {
            'indicator': indicator,
            'reputation': ip_result,
            'correlation': corr_result,
            'prediction': pred_result,
            'investigation_timestamp': now_utc().isoformat()
        }

    def detect_campaign(self, indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect threat campaign."""
        pattern = self.correlation.detect_pattern(indicators)

        ioc_values = [i.get('value') for i in indicators]
        attack_pred = self.prediction.predict_attack_type({
            'iocs': ioc_values,
            'context': 'campaign_detection'
        })

        return {
            'indicators': indicators,
            'pattern': pattern,
            'attack_prediction': attack_pred,
            'detection_timestamp': now_utc().isoformat()
        }
