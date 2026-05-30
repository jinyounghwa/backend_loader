"""Threat hunting automation tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestThreatHuntingEngine:
    """Test automated threat hunting."""

    def test_execute_hunting_playbook(self):
        """✅ Execute hunting playbook."""
        from guardian.hunting.threat_hunting import ThreatHuntingEngine

        hunting = ThreatHuntingEngine()

        results = hunting.execute_playbook({
            'playbook': 'ransomware_detection',
            'lookback_hours': 24
        })

        assert 'indicators' in results
        assert 'correlations' in results
        assert 'risk_score' in results

    def test_hunting_playbook_lateral_movement(self):
        """✅ Execute lateral movement hunting playbook."""
        from guardian.hunting.threat_hunting import ThreatHuntingEngine

        hunting = ThreatHuntingEngine()

        results = hunting.execute_playbook({
            'playbook': 'lateral_movement_detection',
            'lookback_hours': 48
        })

        assert 'threat_chains' in results or 'indicators' in results

    def test_hunting_playbook_data_exfiltration(self):
        """✅ Execute data exfiltration hunting playbook."""
        from guardian.hunting.threat_hunting import ThreatHuntingEngine

        hunting = ThreatHuntingEngine()

        results = hunting.execute_playbook({
            'playbook': 'data_exfiltration_detection',
            'lookback_hours': 24
        })

        assert 'suspicious_transfers' in results or 'indicators' in results

    def test_hunting_with_custom_rules(self):
        """✅ Hunt with custom detection rules."""
        from guardian.hunting.threat_hunting import ThreatHuntingEngine

        hunting = ThreatHuntingEngine()

        results = hunting.execute_playbook({
            'playbook': 'custom_rules',
            'custom_rules': [
                {'pattern': 'failed_login_spike', 'threshold': 10},
                {'pattern': 'privilege_escalation', 'threshold': 5}
            ],
            'lookback_hours': 24
        })

        assert 'indicators' in results


class TestIOCGenerator:
    """Test IOC (Indicator of Compromise) generation."""

    def test_generate_ioc_from_threat(self):
        """✅ Generate IOC from threat data."""
        from guardian.hunting.threat_hunting import IOCGenerator

        generator = IOCGenerator()

        ioc = generator.generate({
            'threat_id': 'threat-123',
            'threat_type': 'MALWARE',
            'file_hash': 'abc123def456',
            'domain': 'malicious.com',
            'ip_address': '192.0.2.1'
        })

        assert 'ioc_id' in ioc
        assert 'indicators' in ioc
        assert len(ioc['indicators']) > 0

    def test_ioc_enrichment(self):
        """✅ Enrich IOC with threat intelligence."""
        from guardian.hunting.threat_hunting import IOCGenerator

        generator = IOCGenerator()

        ioc = generator.generate({
            'threat_id': 'threat-123',
            'threat_type': 'MALWARE',
            'file_hash': 'abc123def456',
            'enrich': True
        })

        assert 'threat_intel' in ioc or 'reputation' in ioc

    def test_ioc_batch_generation(self):
        """✅ Generate IOCs in batch."""
        from guardian.hunting.threat_hunting import IOCGenerator

        generator = IOCGenerator()

        threats = [
            {'threat_id': 'threat-1', 'threat_type': 'MALWARE'},
            {'threat_id': 'threat-2', 'threat_type': 'PHISHING'},
            {'threat_id': 'threat-3', 'threat_type': 'APT'}
        ]

        iocs = generator.batch_generate(threats)

        assert len(iocs) == 3
        assert all('ioc_id' in ioc for ioc in iocs)

    def test_ioc_correlation(self):
        """✅ Correlate IOCs across sources."""
        from guardian.hunting.threat_hunting import IOCGenerator

        generator = IOCGenerator()

        correlation = generator.correlate_iocs({
            'ioc_ids': ['ioc-1', 'ioc-2', 'ioc-3'],
            'correlation_threshold': 0.7
        })

        assert 'correlated_groups' in correlation or 'correlations' in correlation


class TestHuntingPlaybook:
    """Test hunting playbooks."""

    def test_playbook_execution(self):
        """✅ Execute hunting playbook."""
        from guardian.hunting.threat_hunting import HuntingPlaybook

        playbook = HuntingPlaybook()

        result = playbook.execute({
            'name': 'ransomware_detection',
            'lookback_hours': 24
        })

        assert result['status'] == 'completed' or result['status'] == 'executed'
        assert 'findings' in result or 'results' in result

    def test_playbook_with_timeline(self):
        """✅ Playbook execution with timeline analysis."""
        from guardian.hunting.threat_hunting import HuntingPlaybook

        playbook = HuntingPlaybook()

        result = playbook.execute({
            'name': 'lateral_movement_detection',
            'analyze_timeline': True,
            'lookback_hours': 48
        })

        assert 'timeline' in result or 'chain' in result

    def test_playbook_risk_scoring(self):
        """✅ Playbook generates risk scores."""
        from guardian.hunting.threat_hunting import HuntingPlaybook

        playbook = HuntingPlaybook()

        result = playbook.execute({
            'name': 'ransomware_detection',
            'score_findings': True,
            'lookback_hours': 24
        })

        findings = result.get('findings', []) or result.get('results', [])
        assert any('risk_score' in f or 'score' in f for f in findings)

    def test_playbook_custom_parameters(self):
        """✅ Execute playbook with custom parameters."""
        from guardian.hunting.threat_hunting import HuntingPlaybook

        playbook = HuntingPlaybook()

        result = playbook.execute({
            'name': 'custom_playbook',
            'parameters': {
                'sensitivity': 'high',
                'min_confidence': 0.85,
                'include_historical': True
            },
            'lookback_hours': 72
        })

        assert result['status'] in ['completed', 'executed']


class TestHuntingReport:
    """Test hunting report generation."""

    def test_generate_hunting_report(self):
        """✅ Generate hunting report."""
        from guardian.hunting.threat_hunting import HuntingReport

        reporter = HuntingReport()

        report = reporter.generate({
            'hunt_id': 'hunt-123',
            'playbook': 'ransomware_detection',
            'findings_count': 5,
            'duration_hours': 24
        })

        assert 'report_id' in report
        assert 'findings' in report
        assert 'summary' in report or 'statistics' in report

    def test_report_with_timeline(self):
        """✅ Report includes timeline analysis."""
        from guardian.hunting.threat_hunting import HuntingReport

        reporter = HuntingReport()

        report = reporter.generate({
            'hunt_id': 'hunt-123',
            'playbook': 'lateral_movement_detection',
            'include_timeline': True
        })

        assert 'timeline' in report or 'event_sequence' in report

    def test_report_with_recommendations(self):
        """✅ Report includes remediation recommendations."""
        from guardian.hunting.threat_hunting import HuntingReport

        reporter = HuntingReport()

        report = reporter.generate({
            'hunt_id': 'hunt-123',
            'playbook': 'data_exfiltration_detection',
            'include_recommendations': True
        })

        assert 'recommendations' in report or 'remediation' in report

    def test_report_export(self):
        """✅ Export report in various formats."""
        from guardian.hunting.threat_hunting import HuntingReport

        reporter = HuntingReport()

        report = reporter.generate({
            'hunt_id': 'hunt-123',
            'export_format': 'json'
        })

        exported = reporter.export(report['report_id'], format='pdf')
        assert exported['status'] == 'exported' or 'export_url' in exported


class TestThreatHuntingIntegration:
    """End-to-end threat hunting workflows."""

    def test_full_hunting_workflow(self):
        """✅ Complete hunt: playbook → IOC → correlate → report."""
        from guardian.hunting.threat_hunting import (
            ThreatHuntingEngine,
            IOCGenerator,
            HuntingReport
        )

        hunting = ThreatHuntingEngine()
        generator = IOCGenerator()
        reporter = HuntingReport()

        # Step 1: Execute playbook
        hunt_results = hunting.execute_playbook({
            'playbook': 'ransomware_detection',
            'lookback_hours': 24
        })

        assert hunt_results['risk_score'] is not None

        # Step 2: Generate IOCs
        threat = {
            'threat_id': 'threat-123',
            'threat_type': 'RANSOMWARE',
            'file_hash': 'abc123'
        }

        ioc = generator.generate(threat)
        assert 'ioc_id' in ioc

        # Step 3: Generate report
        report = reporter.generate({
            'hunt_id': 'hunt-123',
            'playbook': 'ransomware_detection',
            'findings_count': 1
        })

        assert 'report_id' in report

    def test_multi_playbook_hunting(self):
        """✅ Execute multiple hunting playbooks in sequence."""
        from guardian.hunting.threat_hunting import ThreatHuntingEngine

        hunting = ThreatHuntingEngine()

        playbooks = [
            'ransomware_detection',
            'lateral_movement_detection',
            'data_exfiltration_detection'
        ]

        results = []
        for playbook in playbooks:
            result = hunting.execute_playbook({
                'playbook': playbook,
                'lookback_hours': 24
            })
            results.append(result)

        assert len(results) == 3
        assert all('risk_score' in r for r in results)

    def test_hunting_correlation_analysis(self):
        """✅ Correlate findings across multiple hunts."""
        from guardian.hunting.threat_hunting import ThreatHuntingEngine

        hunting = ThreatHuntingEngine()

        # Execute multiple hunts
        hunt1 = hunting.execute_playbook({
            'playbook': 'ransomware_detection',
            'lookback_hours': 24
        })

        hunt2 = hunting.execute_playbook({
            'playbook': 'lateral_movement_detection',
            'lookback_hours': 24
        })

        # Correlate findings
        correlation = hunting.correlate_findings({
            'findings': [hunt1, hunt2],
            'correlation_window_hours': 4
        })

        assert 'correlated_events' in correlation or 'correlations' in correlation

    def test_hunting_persistence_detection(self):
        """✅ Detect threat persistence mechanisms."""
        from guardian.hunting.threat_hunting import ThreatHuntingEngine

        hunting = ThreatHuntingEngine()

        results = hunting.execute_playbook({
            'playbook': 'persistence_detection',
            'lookback_hours': 72,
            'detect_mechanisms': [
                'scheduled_tasks',
                'registry_modifications',
                'cron_jobs'
            ]
        })

        assert 'persistence_indicators' in results or 'indicators' in results

    def test_hunting_command_execution_analysis(self):
        """✅ Analyze suspicious command execution."""
        from guardian.hunting.threat_hunting import ThreatHuntingEngine

        hunting = ThreatHuntingEngine()

        results = hunting.execute_playbook({
            'playbook': 'command_execution_analysis',
            'lookback_hours': 24,
            'analyze_commands': True
        })

        assert 'suspicious_commands' in results or 'indicators' in results
