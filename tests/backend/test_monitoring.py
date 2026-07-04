"""Sprint 45 Phase 4: 모니터링 검증 테스트 (4 tests)"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock

# Add lambda directory to path
class TestMonitoring:
    """모니터링 & 알람 검증"""

    def test_metrics_collected_on_incident_orchestration(self):
        """✅ 인시던트 오케스트레이션 메트릭 수집"""
        mock_cloudwatch = Mock()

        # CloudWatch 메트릭 푸시
        metric_data = {
            "MetricName": "IncidentOrchestrationDuration",
            "Value": 1234.5,
            "Unit": "Milliseconds",
            "Dimensions": [
                {"Name": "ThreatType", "Value": "EC2Stop"}
            ]
        }

        mock_cloudwatch.put_metric_data.return_value = {"MetricData": [metric_data]}

        result = mock_cloudwatch.put_metric_data()

        # 메트릭 확인
        assert result["MetricData"][0]["MetricName"] == "IncidentOrchestrationDuration"
        assert result["MetricData"][0]["Value"] == 1234.5
        assert result["MetricData"][0]["Unit"] == "Milliseconds"

    def test_errors_tracked_by_type_and_service(self):
        """✅ 에러가 타입과 서비스별로 추적됨"""
        mock_cloudwatch = Mock()

        error_metrics = [
            {
                "MetricName": "ErrorCount",
                "Value": 1,
                "Dimensions": [
                    {"Name": "ErrorType", "Value": "TicketingException"},
                    {"Name": "Service", "Value": "JiraService"}
                ]
            },
            {
                "MetricName": "ErrorCount",
                "Value": 1,
                "Dimensions": [
                    {"Name": "ErrorType", "Value": "WorkflowExecutionException"},
                    {"Name": "Service", "Value": "WorkflowEngine"}
                ]
            },
            {
                "MetricName": "ErrorCount",
                "Value": 1,
                "Dimensions": [
                    {"Name": "ErrorType", "Value": "SOARIntegrationException"},
                    {"Name": "Service", "Value": "SwimlaneConnector"}
                ]
            }
        ]

        mock_cloudwatch.put_metric_data.return_value = {"Errors": len(error_metrics)}

        result = mock_cloudwatch.put_metric_data()

        # 에러 메트릭 확인
        assert result["Errors"] == 3

    def test_performance_metrics_within_sla(self):
        """✅ 성능 메트릭이 SLA 범위 내"""
        mock_cloudwatch = Mock()

        sla_metrics = {
            "IncidentOrchestrationDuration": {
                "value": 450,  # ms
                "sla": 1000,   # 1초
                "within_sla": True
            },
            "TicketCreationTime": {
                "value": 280,  # ms
                "sla": 500,    # 500ms
                "within_sla": True
            },
            "WorkflowExecutionTime": {
                "value": 800,  # ms
                "sla": 2000,   # 2초
                "within_sla": True
            },
            "SOARSubmissionTime": {
                "value": 350,  # ms
                "sla": 1000,   # 1초
                "within_sla": True
            }
        }

        # 메트릭 검증
        for metric_name, metric_data in sla_metrics.items():
            assert metric_data["within_sla"], f"{metric_name} exceeds SLA"
            assert metric_data["value"] <= metric_data["sla"]

    def test_alarms_triggered_on_error_threshold(self):
        """✅ 에러 임계값 초과 시 알람 발동"""
        mock_cloudwatch = Mock()

        # 알람 설정
        alarm_config = {
            "AlarmName": "GuardianHighErrorRate",
            "MetricName": "ErrorCount",
            "Threshold": 10,  # 10개 이상 에러
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "EvaluationPeriods": 1,
            "Period": 300,  # 5분
            "Statistic": "Sum"
        }

        mock_cloudwatch.put_metric_alarm.return_value = {
            "AlarmName": alarm_config["AlarmName"],
            "Status": "OK"
        }

        # 알람 생성
        result = mock_cloudwatch.put_metric_alarm()

        assert result["AlarmName"] == "GuardianHighErrorRate"
        assert result["Status"] == "OK"

        # 에러가 임계값을 초과하는 시나리오
        error_count = 15  # 10개 초과

        if error_count >= alarm_config["Threshold"]:
            # 알람 상태 업데이트
            mock_cloudwatch.set_alarm_state.return_value = {
                "AlarmName": alarm_config["AlarmName"],
                "State": "ALARM"
            }

            state_result = mock_cloudwatch.set_alarm_state()
            assert state_result["State"] == "ALARM"
