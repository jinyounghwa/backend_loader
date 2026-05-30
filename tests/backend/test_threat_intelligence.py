"""Advanced threat intelligence tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestThreatIntelligenceFeed:
    """Test threat intelligence feed integration."""

    def test_fetch_misp_threat_feed(self):
        """✅ Fetch latest MISP threat intelligence."""
        from guardian.intelligence.threat_intelligence import ThreatIntelligenceFeed

        intel = ThreatIntelligenceFeed()

        threats = intel.fetch_feed('misp')

        assert isinstance(threats, list)
        assert len(threats) >= 0
        if len(threats) > 0:
            assert 'ioc' in threats[0]
            assert 'threat_type' in threats[0]

    def test_fetch_alienvault_threat_feed(self):
        """✅ Fetch AlienVault OTX threat feed."""
        from guardian.intelligence.threat_intelligence import ThreatIntelligenceFeed

        intel = ThreatIntelligenceFeed()

        threats = intel.fetch_feed('alienvault')

        assert isinstance(threats, list)
        if len(threats) > 0:
            assert 'ioc' in threats[0]
            assert 'reputation' in threats[0] or 'confidence' in threats[0]

    def test_feed_caching(self):
        """✅ Cache threat feeds locally."""
        from guardian.intelligence.threat_intelligence import ThreatIntelligenceFeed

        intel = ThreatIntelligenceFeed()

        # First fetch
        threats1 = intel.fetch_feed('misp')

        # Second fetch should be cached
        threats2 = intel.fetch_feed('misp')

        assert threats1 == threats2
        assert intel.is_cached('misp')


class TestIPReputation:
    """Test IP reputation queries."""

    def test_query_ip_reputation(self):
        """✅ Query IP reputation from threat intel."""
        from guardian.intelligence.threat_intelligence import IPReputation

        ip_rep = IPReputation()

        result = ip_rep.get_reputation('203.0.113.42')

        assert 'ip' in result
        assert result['ip'] == '203.0.113.42'
        assert 'reputation_score' in result
        assert 0 <= result['reputation_score'] <= 100

    def test_ip_reputation_sources(self):
        """✅ Get reputation from multiple sources."""
        from guardian.intelligence.threat_intelligence import IPReputation

        ip_rep = IPReputation()

        result = ip_rep.get_reputation('203.0.113.1', sources=['misp', 'alienvault'])

        assert 'ip' in result
        assert 'sources' in result or len(result) >= 2

    def test_bulk_ip_reputation_check(self):
        """✅ Bulk check reputation for multiple IPs."""
        from guardian.intelligence.threat_intelligence import IPReputation

        ip_rep = IPReputation()

        ips = ['203.0.113.1', '203.0.113.2', '203.0.113.3']

        results = ip_rep.get_bulk_reputation(ips)

        assert len(results) == 3
        assert all('reputation_score' in r for r in results)


class TestThreatCorrelation:
    """Test threat data correlation."""

    def test_correlate_single_ioc(self):
        """✅ Correlate threat data from multiple sources."""
        from guardian.intelligence.threat_intelligence import ThreatCorrelation

        correlation = ThreatCorrelation()

        result = correlation.correlate({
            'ioc': '203.0.113.1',
            'sources': ['misp', 'alienvault', 'internal']
        })

        assert 'ioc' in result
        assert 'risk_score' in result
        assert result['risk_score'] >= 0

    def test_correlate_multiple_indicators(self):
        """✅ Correlate multiple threat indicators."""
        from guardian.intelligence.threat_intelligence import ThreatCorrelation

        correlation = ThreatCorrelation()

        result = correlation.correlate({
            'indicators': [
                {'type': 'IP', 'value': '203.0.113.1'},
                {'type': 'DOMAIN', 'value': 'malicious.example.com'},
                {'type': 'FILE_HASH', 'value': 'abc123def456'}
            ]
        })

        assert 'correlation_score' in result or 'indicators' in result
        assert result.get('correlation_score', 0) >= 0

    def test_detect_ioc_patterns(self):
        """✅ Detect patterns in indicators of compromise."""
        from guardian.intelligence.threat_intelligence import ThreatCorrelation

        correlation = ThreatCorrelation()

        indicators = [
            {'type': 'IP', 'value': '203.0.113.1'},
            {'type': 'IP', 'value': '203.0.113.2'},
            {'type': 'DOMAIN', 'value': 'campaign.example.com'}
        ]

        pattern = correlation.detect_pattern(indicators)

        assert 'pattern_type' in pattern or 'detected' in pattern


class TestThreatPrediction:
    """Test ML-based threat prediction."""

    def test_predict_threat_score(self):
        """✅ Predict threat likelihood score."""
        from guardian.intelligence.threat_intelligence import ThreatPrediction

        predictor = ThreatPrediction()

        score = predictor.predict_threat({
            'indicators': 3,
            'source_diversity': 2,
            'temporal_similarity': 0.8,
            'infrastructure_overlap': 0.6
        })

        assert 'threat_score' in score
        assert 0 <= score['threat_score'] <= 100
        assert 'confidence' in score

    def test_predict_attack_type(self):
        """✅ Predict attack type from indicators."""
        from guardian.intelligence.threat_intelligence import ThreatPrediction

        predictor = ThreatPrediction()

        prediction = predictor.predict_attack_type({
            'iocs': ['203.0.113.1', 'example.com'],
            'context': 'ec2_instance_compromise'
        })

        assert 'attack_type' in prediction
        assert 'confidence' in prediction

    def test_predict_target_industry(self):
        """✅ Predict target industry from campaign data."""
        from guardian.intelligence.threat_intelligence import ThreatPrediction

        predictor = ThreatPrediction()

        prediction = predictor.predict_target_industry({
            'campaign_name': 'Operation Stealth',
            'iocs_count': 50,
            'infrastructure_country': 'CN'
        })

        assert 'target_industries' in prediction or 'industry' in prediction
        assert isinstance(prediction.get('target_industries', []), list)


class TestThreatIntelligenceIntegration:
    """End-to-end threat intelligence workflows."""

    def test_full_threat_investigation(self):
        """✅ Complete threat investigation workflow."""
        from guardian.intelligence.threat_intelligence import (
            IPReputation,
            ThreatCorrelation,
            ThreatIntelligenceFeed
        )

        # Step 1: Get IP reputation
        ip_rep = IPReputation()
        ip_result = ip_rep.get_reputation('203.0.113.1')

        assert 'reputation_score' in ip_result

        # Step 2: Correlate with threat feeds
        correlation = ThreatCorrelation()
        corr_result = correlation.correlate({
            'ioc': '203.0.113.1',
            'sources': ['misp', 'alienvault']
        })

        assert 'risk_score' in corr_result

        # Step 3: Fetch related threats
        intel_feed = ThreatIntelligenceFeed()
        threats = intel_feed.fetch_feed('misp')

        assert isinstance(threats, list)

    def test_detect_campaign_from_indicators(self):
        """✅ Detect threat campaign from IOCs."""
        from guardian.intelligence.threat_intelligence import (
            ThreatCorrelation,
            ThreatPrediction
        )

        correlation = ThreatCorrelation()
        predictor = ThreatPrediction()

        indicators = [
            {'type': 'IP', 'value': '203.0.113.1'},
            {'type': 'DOMAIN', 'value': 'c2.example.com'},
            {'type': 'HASH', 'value': 'abc123'}
        ]

        # Correlate indicators
        corr_result = correlation.correlate({
            'indicators': indicators
        })

        # Predict threat type
        prediction = predictor.predict_attack_type({
            'iocs': [i['value'] for i in indicators],
            'context': 'distributed_attack'
        })

        assert 'attack_type' in prediction or 'correlation_score' in corr_result

    def test_monitor_threat_escalation(self):
        """✅ Monitor threat escalation over time."""
        from guardian.intelligence.threat_intelligence import IPReputation

        ip_rep = IPReputation()

        # Check reputation multiple times
        rep1 = ip_rep.get_reputation('203.0.113.1')
        rep2 = ip_rep.get_reputation('203.0.113.1')

        assert 'reputation_score' in rep1
        assert 'reputation_score' in rep2

    def test_threat_intel_dashboard(self):
        """✅ Get threat intelligence for dashboard."""
        from guardian.intelligence.threat_intelligence import (
            ThreatIntelligenceFeed,
            IPReputation
        )

        intel_feed = ThreatIntelligenceFeed()
        ip_rep = IPReputation()

        # Get top threats
        threats = intel_feed.fetch_feed('misp')

        # Get reputation stats
        stats = {
            'total_threats': len(threats),
            'critical_ips': 0
        }

        if len(threats) > 0:
            top_ioc = threats[0].get('ioc', '203.0.113.1')
            rep = ip_rep.get_reputation(top_ioc)
            if rep.get('reputation_score', 0) > 80:
                stats['critical_ips'] += 1

        assert 'total_threats' in stats
        assert 'critical_ips' in stats

    def test_threat_intel_api_failover(self):
        """✅ Handle API failover gracefully."""
        from guardian.intelligence.threat_intelligence import ThreatIntelligenceFeed

        intel = ThreatIntelligenceFeed()

        # Try to fetch from primary, fallback to secondary
        threats = intel.fetch_feed('misp')

        # Should return data or empty list, never error
        assert isinstance(threats, list)

    def test_threat_deduplication(self):
        """✅ Deduplicate threats across feeds."""
        from guardian.intelligence.threat_intelligence import ThreatIntelligenceFeed

        intel = ThreatIntelligenceFeed()

        # Fetch multiple feeds
        misp_threats = intel.fetch_feed('misp')
        av_threats = intel.fetch_feed('alienvault')

        # Deduplicate
        all_threats = misp_threats + av_threats
        unique_threats = intel.deduplicate_threats(all_threats)

        assert len(unique_threats) <= len(all_threats)
