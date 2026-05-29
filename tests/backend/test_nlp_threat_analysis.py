"""Sprint 69 Phase 1: NLP-Based Threat Analysis (15 tests)"""

import pytest
from datetime import datetime


class TestThreatTextGeneration:
    """Test threat text generation."""

    def test_threat_text_from_ec2_unauthorized_region(self):
        """✅ Generate threat text from EC2 unauthorized region."""
        from guardian.ml.nlp_analyzer import ThreatTextGenerator

        generator = ThreatTextGenerator()
        threat = {
            'type': 'EC2_UNAUTHORIZED_REGION',
            'region': 'eu-west-1'
        }

        text = generator.generate(threat)

        assert 'Unauthorized EC2' in text
        assert 'eu-west-1' in text

    def test_threat_text_from_s3_public_bucket(self):
        """✅ Generate threat text from S3 public bucket."""
        from guardian.ml.nlp_analyzer import ThreatTextGenerator

        generator = ThreatTextGenerator()
        threat = {
            'type': 'S3_PUBLIC_BUCKET',
            'bucket_name': 'my-sensitive-data'
        }

        text = generator.generate(threat)

        assert 'Public S3' in text
        assert 'my-sensitive-data' in text

    def test_threat_text_enrichment_with_metadata(self):
        """✅ Enrich threat text with metadata."""
        from guardian.ml.nlp_analyzer import ThreatTextGenerator

        generator = ThreatTextGenerator()
        threat = {
            'type': 'HIGH_COST',
            'amount': 500,
            'threshold': 100,
            'instance_id': 'i-12345',
            'severity': 8
        }

        text = generator.generate(threat)
        enriched = generator.enrich_description(text, threat)

        assert '$500' in enriched
        assert 'i-12345' in enriched
        assert 'Severity: 8/10' in enriched


class TestRootCauseAnalysis:
    """Test root cause analysis."""

    def test_root_cause_ec2_region_deployment(self):
        """✅ Analyze root cause of EC2 region issue."""
        from guardian.ml.nlp_analyzer import RootCauseAnalyzer

        analyzer = RootCauseAnalyzer()
        threat = {
            'type': 'EC2_UNAUTHORIZED_REGION',
            'region': 'eu-west-1',
            'changed_by': 'developer@company.com'
        }

        result = analyzer.analyze(threat)

        assert 'root_cause' in result
        assert result['confidence'] >= 0.5
        assert result['confidence'] <= 1.0

    def test_root_cause_s3_public_bucket(self):
        """✅ Analyze root cause of S3 public bucket."""
        from guardian.ml.nlp_analyzer import RootCauseAnalyzer

        analyzer = RootCauseAnalyzer()
        threat = {
            'type': 'S3_PUBLIC_BUCKET',
            'bucket_name': 'data-backup',
            'time_since_change': 3600  # 1 hour
        }

        result = analyzer.analyze(threat)

        assert result['root_cause'] in ['acl_misconfiguration', 'policy_overpermissive']
        assert result['confidence'] > 0.5

    def test_root_cause_high_cost_spike(self):
        """✅ Analyze root cause of cost spike."""
        from guardian.ml.nlp_analyzer import RootCauseAnalyzer

        analyzer = RootCauseAnalyzer()
        threat = {
            'type': 'HIGH_COST',
            'amount': 1000,
            'threshold': 100
        }

        result = analyzer.analyze(threat)

        assert result['cause_name'] is not None
        assert result['confidence'] > 0.4

    def test_confidence_increases_with_evidence(self):
        """✅ Confidence increases when more evidence is available."""
        from guardian.ml.nlp_analyzer import RootCauseAnalyzer

        analyzer = RootCauseAnalyzer()

        threat_minimal = {'type': 'EC2_UNAUTHORIZED_REGION'}
        threat_detailed = {
            'type': 'EC2_UNAUTHORIZED_REGION',
            'changed_by': 'user@company.com',
            'time_since_change': 3600
        }

        result_minimal = analyzer.analyze(threat_minimal)
        result_detailed = analyzer.analyze(threat_detailed)

        assert result_detailed['confidence'] > result_minimal['confidence']


class TestSentimentAnalysis:
    """Test threat sentiment and severity analysis."""

    def test_critical_threat_sentiment(self):
        """✅ Detect critical threat sentiment."""
        from guardian.ml.nlp_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer()
        threat_text = 'Critical data breach detected - account compromised'

        result = analyzer.analyze_severity(threat_text)

        assert result['severity'] == 'critical'
        assert result['score'] >= 8
        assert result['sentiment'] == 'negative'

    def test_medium_threat_sentiment(self):
        """✅ Detect medium threat sentiment."""
        from guardian.ml.nlp_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer()
        threat_text = 'Medium priority: instance detected in wrong region'

        result = analyzer.analyze_severity(threat_text)

        assert result['severity'] == 'medium'
        assert result['score'] == 5
        assert result['sentiment'] == 'negative'  # All threats are negative sentiment

    def test_low_threat_sentiment(self):
        """✅ Detect low threat sentiment."""
        from guardian.ml.nlp_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer()
        threat_text = 'Low priority warning: informational finding'

        result = analyzer.analyze_severity(threat_text)

        assert result['severity'] == 'low'
        assert result['score'] <= 3


class TestThreatIntelligence:
    """Test threat intelligence integration."""

    def test_lookup_ssh_bruteforce_threat(self):
        """✅ Look up SSH brute force threat intelligence."""
        from guardian.integrations.threat_intelligence import ThreatIntelligenceAPI

        api = ThreatIntelligenceAPI()
        intel = api.lookup_threat('ssh_bruteforce')

        assert intel is not None
        assert intel['type'] == 'brute_force'
        assert intel['risk_score'] == 8

    def test_lookup_sql_injection_threat(self):
        """✅ Look up SQL injection threat intelligence."""
        from guardian.integrations.threat_intelligence import ThreatIntelligenceAPI

        api = ThreatIntelligenceAPI()
        intel = api.lookup_threat('sql_injection')

        assert intel is not None
        assert intel['risk_score'] == 9
        assert 'mitigation' in intel

    def test_threat_correlation_detection(self):
        """✅ Detect correlated threats (potential campaign)."""
        from guardian.integrations.threat_intelligence import ThreatCorrelationEngine

        correlator = ThreatCorrelationEngine()

        threats = [
            {'type': 'ssh_bruteforce', 'source': 'attacker@evil.com'},
            {'type': 'ssh_bruteforce', 'source': 'attacker@evil.com'},
            {'type': 'ssh_bruteforce', 'source': 'attacker@evil.com'}
        ]

        for threat in threats:
            correlator.add_threat(threat)

        result = correlator.correlate_threats(threats)

        assert result['correlation_found'] is True
        assert result['threat_type'] == 'ssh_bruteforce'
        assert result['threat_count'] == 3

    def test_false_positive_detection(self):
        """✅ Detect false positive threats."""
        from guardian.integrations.threat_intelligence import ThreatValidation

        validator = ThreatValidation()
        threat = {
            'type': 'security_group_open',
            'description': 'Test environment - staging demo configuration'
        }

        result = validator.validate_threat(threat)

        assert result['is_false_positive'] is True
        assert result['validation_status'] == 'false_positive'


class TestNLPPerformance:
    """Test NLP performance metrics."""

    def test_text_generation_latency(self):
        """✅ Text generation completes in <100ms."""
        from guardian.ml.nlp_analyzer import ThreatTextGenerator
        import time

        generator = ThreatTextGenerator()
        threat = {'type': 'HIGH_COST', 'amount': 500, 'threshold': 100}

        start = time.time()
        text = generator.generate(threat)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 100
        assert text is not None

    def test_root_cause_analysis_latency(self):
        """✅ Root cause analysis completes in <100ms."""
        from guardian.ml.nlp_analyzer import RootCauseAnalyzer
        import time

        analyzer = RootCauseAnalyzer()
        threat = {'type': 'EC2_UNAUTHORIZED_REGION', 'region': 'eu-west-1'}

        start = time.time()
        result = analyzer.analyze(threat)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 100
        assert result is not None
