"""Intelligent reporting tests for AWS Guardian."""

import pytest
from datetime import datetime


class TestIntelligentReporter:
    """Test AI-based intelligent reporting."""

    def test_generate_intelligent_report(self):
        """✅ Generate intelligent report with AI summary."""
        from guardian.reporters.intelligent_reporter import IntelligentReporter

        reporter = IntelligentReporter()

        report = reporter.generate({
            'hunt_id': 'hunt-123',
            'include_summary': True,
            'include_predictions': True,
            'include_recommendations': True
        })

        assert 'ai_summary' in report
        assert 'predictions' in report
        assert 'smart_recommendations' in report

    def test_report_with_executive_summary(self):
        """✅ Generate executive summary."""
        from guardian.reporters.intelligent_reporter import IntelligentReporter

        reporter = IntelligentReporter()

        summary = reporter.generate_executive_summary({
            'hunt_id': 'hunt-123',
            'findings_count': 5,
            'severity': 'CRITICAL'
        })

        assert 'summary' in summary or 'executive_summary' in summary
        assert len(summary.get('summary', '')) > 30

    def test_prediction_generation(self):
        """✅ Generate threat/cost predictions."""
        from guardian.reporters.intelligent_reporter import IntelligentReporter

        reporter = IntelligentReporter()

        predictions = reporter.generate_predictions({
            'lookback_days': 90,
            'forecast_days': 30,
            'prediction_types': ['threat', 'cost']
        })

        assert 'threat_predictions' in predictions
        assert 'cost_predictions' in predictions

    def test_smart_recommendations(self):
        """✅ Generate context-aware recommendations."""
        from guardian.reporters.intelligent_reporter import IntelligentReporter

        reporter = IntelligentReporter()

        recommendations = reporter.generate_recommendations({
            'hunt_id': 'hunt-123',
            'findings': [{'type': 'MALWARE', 'severity': 'CRITICAL'}],
            'context': 'production'
        })

        assert 'recommendations' in recommendations
        assert len(recommendations['recommendations']) > 0

    def test_report_prioritization(self):
        """✅ Prioritize findings by risk."""
        from guardian.reporters.intelligent_reporter import IntelligentReporter

        reporter = IntelligentReporter()

        prioritized = reporter.prioritize_findings({
            'findings': [
                {'type': 'CONFIG_CHANGE', 'severity': 'LOW'},
                {'type': 'MALWARE', 'severity': 'CRITICAL'},
                {'type': 'UNAUTHORIZED_ACCESS', 'severity': 'HIGH'}
            ]
        })

        assert prioritized['findings'][0]['severity'] == 'CRITICAL'


class TestReportSummarizer:
    """Test automatic report summarization."""

    def test_natural_language_summary(self):
        """✅ Generate natural language summary."""
        from guardian.reporters.intelligent_reporter import ReportSummarizer

        summarizer = ReportSummarizer()

        summary = summarizer.summarize({
            'report_content': 'Multiple threats detected across EC2 instances...',
            'detail_level': 'medium'
        })

        assert 'summary_text' in summary
        assert len(summary['summary_text']) > 20

    def test_summary_by_severity(self):
        """✅ Summarize findings by severity level."""
        from guardian.reporters.intelligent_reporter import ReportSummarizer

        summarizer = ReportSummarizer()

        summary = summarizer.summarize_by_severity({
            'findings': [
                {'severity': 'CRITICAL', 'count': 2},
                {'severity': 'HIGH', 'count': 5},
                {'severity': 'MEDIUM', 'count': 10}
            ]
        })

        assert 'summary' in summary or 'by_severity' in summary

    def test_summary_compression(self):
        """✅ Compress report while preserving key information."""
        from guardian.reporters.intelligent_reporter import ReportSummarizer

        summarizer = ReportSummarizer()

        compressed = summarizer.compress({
            'original_size_pages': 50,
            'target_size_pages': 5,
            'preserve_findings': True
        })

        assert 'compressed_size_pages' in compressed
        assert compressed['compressed_size_pages'] <= 5


class TestPredictiveAnalytics:
    """Test predictive analytics in reporting."""

    def test_threat_prediction(self):
        """✅ Predict future threat likelihood."""
        from guardian.reporters.intelligent_reporter import PredictiveAnalytics

        analytics = PredictiveAnalytics()

        prediction = analytics.predict_threats({
            'lookback_days': 90,
            'forecast_days': 30
        })

        assert 'threat_probability' in prediction
        assert 0 <= prediction['threat_probability'] <= 1

    def test_cost_prediction(self):
        """✅ Predict cost trends."""
        from guardian.reporters.intelligent_reporter import PredictiveAnalytics

        analytics = PredictiveAnalytics()

        prediction = analytics.predict_costs({
            'historical_data': [100, 110, 120, 130, 140],
            'forecast_periods': 5
        })

        assert 'predicted_costs' in prediction
        assert len(prediction['predicted_costs']) >= 1

    def test_anomaly_prediction(self):
        """✅ Predict anomalies before they occur."""
        from guardian.reporters.intelligent_reporter import PredictiveAnalytics

        analytics = PredictiveAnalytics()

        prediction = analytics.predict_anomalies({
            'metric': 'api_errors',
            'lookback_hours': 168
        })

        assert 'anomaly_probability' in prediction
        assert 'predicted_magnitude' in prediction

    def test_seasonal_adjustment(self):
        """✅ Apply seasonal adjustments to predictions."""
        from guardian.reporters.intelligent_reporter import PredictiveAnalytics

        analytics = PredictiveAnalytics()

        adjusted = analytics.apply_seasonality({
            'base_forecast': [100, 110, 120],
            'season': 'holiday'
        })

        assert 'adjusted_forecast' in adjusted
        assert len(adjusted['adjusted_forecast']) == 3


class TestSmartRecommendations:
    """Test context-aware recommendation engine."""

    def test_actionable_recommendations(self):
        """✅ Generate actionable recommendations."""
        from guardian.reporters.intelligent_reporter import SmartRecommendations

        recommender = SmartRecommendations()

        recommendations = recommender.generate({
            'findings': [{'type': 'MALWARE', 'severity': 'CRITICAL'}],
            'context': 'production'
        })

        assert 'recommendations' in recommendations
        for rec in recommendations['recommendations']:
            assert 'action' in rec
            assert 'priority' in rec

    def test_priority_scoring(self):
        """✅ Score recommendations by priority."""
        from guardian.reporters.intelligent_reporter import SmartRecommendations

        recommender = SmartRecommendations()

        scored = recommender.score_recommendations({
            'recommendations': [
                {'action': 'patch_system'},
                {'action': 'update_config'},
                {'action': 'review_logs'}
            ]
        })

        assert 'scored_recommendations' in scored
        # Verify first is highest priority
        priorities = [r.get('priority', 0) for r in scored['scored_recommendations']]
        assert priorities == sorted(priorities, reverse=True)

    def test_cost_benefit_analysis(self):
        """✅ Analyze cost vs benefit of recommendations."""
        from guardian.reporters.intelligent_reporter import SmartRecommendations

        recommender = SmartRecommendations()

        analysis = recommender.cost_benefit_analysis({
            'recommendation': 'deploy_security_tool',
            'implementation_cost': 5000,
            'monthly_savings': 1000
        })

        assert 'roi_months' in analysis
        assert 'net_benefit' in analysis

    def test_dependency_aware_recommendations(self):
        """✅ Handle recommendation dependencies."""
        from guardian.reporters.intelligent_reporter import SmartRecommendations

        recommender = SmartRecommendations()

        recommendations = recommender.generate_with_dependencies({
            'findings': [
                {'type': 'MALWARE'},
                {'type': 'UNAUTHORIZED_ACCESS'}
            ]
        })

        assert 'execution_order' in recommendations or 'dependencies' in recommendations


class TestIntelligentReportingIntegration:
    """End-to-end intelligent reporting workflows."""

    def test_full_reporting_pipeline(self):
        """✅ Complete pipeline: report → summarize → predict → recommend."""
        from guardian.reporters.intelligent_reporter import (
            IntelligentReporter,
            ReportSummarizer,
            PredictiveAnalytics,
            SmartRecommendations
        )

        reporter = IntelligentReporter()
        summarizer = ReportSummarizer()
        analytics = PredictiveAnalytics()
        recommender = SmartRecommendations()

        # Step 1: Generate report
        report = reporter.generate({
            'hunt_id': 'hunt-123',
            'include_summary': True
        })

        assert 'ai_summary' in report

        # Step 2: Summarize
        summary = summarizer.summarize({
            'report_content': report.get('ai_summary', '')
        })

        assert 'summary_text' in summary

        # Step 3: Predict
        predictions = analytics.predict_threats({
            'lookback_days': 90
        })

        assert 'threat_probability' in predictions

        # Step 4: Recommend
        recommendations = recommender.generate({
            'findings': []
        })

        assert 'recommendations' in recommendations

    def test_executive_dashboard_report(self):
        """✅ Generate executive dashboard report."""
        from guardian.reporters.intelligent_reporter import IntelligentReporter

        reporter = IntelligentReporter()

        dashboard = reporter.generate_dashboard_report({
            'metrics': ['threats', 'costs', 'compliance'],
            'time_period': 'monthly',
            'audience': 'executive'
        })

        assert 'metrics_summary' in dashboard
        assert 'key_insights' in dashboard or 'insights' in dashboard
        assert 'top_recommendations' in dashboard or 'recommendations' in dashboard

    def test_multi_tenant_reporting(self):
        """✅ Generate reports for multiple accounts/teams."""
        from guardian.reporters.intelligent_reporter import IntelligentReporter

        reporter = IntelligentReporter()

        reports = reporter.generate_multi_tenant({
            'accounts': ['prod', 'staging', 'dev'],
            'include_comparisons': True
        })

        assert len([k for k in reports if k in ['prod', 'staging', 'dev']]) == 3
        assert 'comparisons' in reports or 'comparison' in reports

    def test_automated_report_distribution(self):
        """✅ Automate report distribution."""
        from guardian.reporters.intelligent_reporter import IntelligentReporter

        reporter = IntelligentReporter()

        distribution = reporter.distribute_report({
            'report_id': 'report-123',
            'recipients': ['security@example.com', 'ciso@example.com'],
            'format': 'pdf'
        })

        assert distribution['status'] == 'distributed'
        assert len(distribution['sent_to']) == 2
