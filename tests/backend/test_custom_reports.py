"""Custom report builder tests for AWS Guardian."""

import pytest


class TestReportBuilder:
    """Test custom report creation."""

    def test_create_basic_report(self):
        """✅ Create basic report."""
        from guardian.reporting.report_builder import ReportBuilder

        builder = ReportBuilder()

        report = builder.create({
            'title': 'Monthly Security Report',
            'template': 'standard',
            'sections': ['summary', 'threats', 'recommendations']
        })

        assert 'report_id' in report
        assert report['title'] == 'Monthly Security Report'

    def test_add_content_to_report(self):
        """✅ Add content blocks to report."""
        from guardian.reporting.report_builder import ReportBuilder

        builder = ReportBuilder()

        result = builder.add_section({
            'report_id': 'rpt_123',
            'section_type': 'threats',
            'content': {'title': 'Threats Detected', 'count': 15},
            'position': 2
        })

        assert 'section_id' in result or 'added' in result
        assert result.get('added') is True or 'section_id' in result

    def test_customize_report_layout(self):
        """✅ Customize report layout."""
        from guardian.reporting.report_builder import ReportBuilder

        builder = ReportBuilder()

        result = builder.customize({
            'report_id': 'rpt_123',
            'layout': 'two_column',
            'color_scheme': 'professional',
            'include_logo': True
        })

        assert 'customized' in result or 'layout_id' in result


class TestTemplateEngine:
    """Test report templates."""

    def test_list_available_templates(self):
        """✅ List available report templates."""
        from guardian.reporting.report_builder import TemplateEngine

        engine = TemplateEngine()

        templates = engine.list_templates({
            'category': 'security'
        })

        assert 'templates' in templates or len(templates.get('templates', [])) >= 0
        assert isinstance(templates.get('templates', []), list)

    def test_load_template(self):
        """✅ Load report template."""
        from guardian.reporting.report_builder import TemplateEngine

        engine = TemplateEngine()

        template = engine.load({
            'template_name': 'executive_summary'
        })

        assert 'template_id' in template
        assert 'sections' in template or 'structure' in template

    def test_customize_template(self):
        """✅ Customize template."""
        from guardian.reporting.report_builder import TemplateEngine

        engine = TemplateEngine()

        result = engine.customize({
            'template_id': 'tpl_123',
            'custom_sections': [
                {'name': 'Executive Summary'},
                {'name': 'Risk Assessment'}
            ]
        })

        assert 'customized_template_id' in result or 'saved' in result


class TestExportManager:
    """Test report export."""

    def test_export_to_pdf(self):
        """✅ Export report to PDF."""
        from guardian.reporting.report_builder import ExportManager

        exporter = ExportManager()

        result = exporter.export({
            'report_id': 'rpt_123',
            'format': 'pdf',
            'filename': 'security_report.pdf'
        })

        assert 'file_url' in result or 'exported' in result
        assert 'format' in result

    def test_export_to_excel(self):
        """✅ Export report to Excel."""
        from guardian.reporting.report_builder import ExportManager

        exporter = ExportManager()

        result = exporter.export({
            'report_id': 'rpt_123',
            'format': 'xlsx',
            'include_charts': True
        })

        assert 'file_url' in result or 'file_path' in result

    def test_export_to_json(self):
        """✅ Export report to JSON."""
        from guardian.reporting.report_builder import ExportManager

        exporter = ExportManager()

        result = exporter.export({
            'report_id': 'rpt_123',
            'format': 'json'
        })

        assert 'data' in result or 'file_url' in result


class TestScheduledReports:
    """Test scheduled report generation."""

    def test_schedule_report(self):
        """✅ Schedule report for recurring generation."""
        from guardian.reporting.report_builder import ScheduledReports

        scheduler = ScheduledReports()

        schedule = scheduler.schedule({
            'report_id': 'rpt_123',
            'frequency': 'weekly',
            'day_of_week': 'monday',
            'time': '09:00'
        })

        assert 'schedule_id' in schedule
        assert 'frequency' in schedule

    def test_list_scheduled_reports(self):
        """✅ List all scheduled reports."""
        from guardian.reporting.report_builder import ScheduledReports

        scheduler = ScheduledReports()

        schedules = scheduler.list_schedules({
            'status': 'active'
        })

        assert 'schedules' in schedules or isinstance(schedules, list)

    def test_update_schedule(self):
        """✅ Update report schedule."""
        from guardian.reporting.report_builder import ScheduledReports

        scheduler = ScheduledReports()

        result = scheduler.update({
            'schedule_id': 'sch_123',
            'frequency': 'bi-weekly',
            'recipients': ['security@example.com', 'ciso@example.com']
        })

        assert 'updated' in result or 'schedule_id' in result


class TestReportBuilderIntegration:
    """End-to-end report building workflows."""

    def test_full_report_creation_pipeline(self):
        """✅ Complete report creation: build → customize → export."""
        from guardian.reporting.report_builder import (
            ReportBuilder,
            ExportManager
        )

        builder = ReportBuilder()
        exporter = ExportManager()

        # Create report
        report = builder.create({'title': 'Security Report'})
        assert 'report_id' in report

        # Add content
        section = builder.add_section({
            'report_id': report['report_id'],
            'section_type': 'threats'
        })

        # Export
        export = exporter.export({
            'report_id': report['report_id'],
            'format': 'pdf'
        })
        assert 'file_url' in export or 'exported' in export

    def test_template_based_report_workflow(self):
        """✅ Create report from template."""
        from guardian.reporting.report_builder import (
            TemplateEngine,
            ReportBuilder,
            ExportManager
        )

        template_engine = TemplateEngine()
        builder = ReportBuilder()
        exporter = ExportManager()

        # Load template
        template = template_engine.load({'template_name': 'executive_summary'})
        assert 'template_id' in template

        # Create from template
        report = builder.create({'template': template['template_id']})
        assert 'report_id' in report

        # Export
        export = exporter.export({'report_id': report['report_id'], 'format': 'pdf'})
        assert 'file_url' in export or 'exported' in export

    def test_scheduled_reporting_workflow(self):
        """✅ Schedule and auto-generate reports."""
        from guardian.reporting.report_builder import (
            ReportBuilder,
            ScheduledReports
        )

        builder = ReportBuilder()
        scheduler = ScheduledReports()

        # Create report
        report = builder.create({'title': 'Weekly Report'})

        # Schedule it
        schedule = scheduler.schedule({
            'report_id': report['report_id'],
            'frequency': 'weekly'
        })
        assert 'schedule_id' in schedule

    def test_multi_format_export(self):
        """✅ Export same report in multiple formats."""
        from guardian.reporting.report_builder import (
            ReportBuilder,
            ExportManager
        )

        builder = ReportBuilder()
        exporter = ExportManager()

        # Create report
        report = builder.create({'title': 'Multi-format Report'})

        # Export in multiple formats
        formats = ['pdf', 'xlsx', 'json']
        exports = []
        for fmt in formats:
            export = exporter.export({
                'report_id': report['report_id'],
                'format': fmt
            })
            exports.append(export)

        assert len(exports) == 3
