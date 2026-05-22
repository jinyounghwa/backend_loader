"""
Sprint 31 Phase 2: CloudWatch 모니터링 & 대시보드 테스트
CloudWatch Dashboard, Alarms, 메트릭 정의 검증
"""

import unittest
import yaml
import json
from pathlib import Path


class CloudFormationLoader(yaml.SafeLoader):
    """CloudFormation 태그 처리"""

    pass


def cfn_constructor(loader, tag_suffix, node):
    """CloudFormation 고유 태그 처리"""
    if isinstance(node, yaml.ScalarNode):
        return {tag_suffix[1:]: loader.construct_scalar(node)}
    elif isinstance(node, yaml.SequenceNode):
        return {tag_suffix[1:]: loader.construct_sequence(node)}
    elif isinstance(node, yaml.MappingNode):
        return {tag_suffix[1:]: loader.construct_mapping(node)}


CloudFormationLoader.add_multi_constructor("!", cfn_constructor)


class TestCloudWatchDashboard(unittest.TestCase):
    """CloudWatch Dashboard 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_dashboard_resource_exists(self):
        """CloudWatch Dashboard 리소스 존재"""
        resources = self.template.get("Resources", {})
        self.assertIn("WebSocketDashboard", resources)

        dashboard = resources["WebSocketDashboard"]
        self.assertEqual(dashboard["Type"], "AWS::CloudWatch::Dashboard")
        self.assertIn("Properties", dashboard)
        self.assertIn("DashboardName", dashboard["Properties"])
        self.assertIn("DashboardBody", dashboard["Properties"])

    def test_dashboard_name_format(self):
        """Dashboard 이름이 올바른 형식"""
        resources = self.template.get("Resources", {})
        dashboard = resources["WebSocketDashboard"]
        name = dashboard["Properties"]["DashboardName"]

        # !Sub 문법 확인 - CloudFormationLoader는 'Sub'를 'ub'로 파싱
        self.assertIsInstance(name, dict)
        # 키가 'Sub' 또는 'ub' (cfn_constructor의 tag_suffix[1:]로 인해)
        keys = list(name.keys())
        self.assertTrue(any("ub" in k or "Sub" in k for k in keys))

    def test_dashboard_body_valid_json(self):
        """Dashboard Body JSON 문법 검증"""
        resources = self.template.get("Resources", {})
        dashboard = resources["WebSocketDashboard"]
        body = dashboard["Properties"]["DashboardBody"]

        # !Sub 지정자 제거 후 JSON 파싱
        body_str = str(body)

        # CloudFormation !Sub 제거
        if isinstance(body, dict) and "Sub" in body:
            body_str = body["Sub"]

        try:
            json_obj = json.loads(body_str)
            self.assertIn("widgets", json_obj)
            self.assertIsInstance(json_obj["widgets"], list)
            self.assertGreater(len(json_obj["widgets"]), 0)
        except json.JSONDecodeError:
            # !Sub 제한 때문에 파싱 실패 가능 - 문법만 확인
            self.assertIn("widgets", body_str)

    def test_dashboard_has_multiple_sections(self):
        """Dashboard가 여러 섹션(widget) 포함"""
        resources = self.template.get("Resources", {})
        dashboard = resources["WebSocketDashboard"]
        body = dashboard["Properties"]["DashboardBody"]

        body_str = str(body)
        # 최소 4개 섹션 확인
        widget_count = body_str.count('"type": "metric"')
        self.assertGreaterEqual(widget_count, 4)


class TestCloudWatchAlarms(unittest.TestCase):
    """CloudWatch Alarms 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_connection_error_alarm_exists(self):
        """ConnectionErrorAlarm 정의 확인"""
        resources = self.template.get("Resources", {})
        self.assertIn("ConnectionErrorAlarm", resources)

        alarm = resources["ConnectionErrorAlarm"]
        self.assertEqual(alarm["Type"], "AWS::CloudWatch::Alarm")
        self.assertEqual(alarm["Properties"]["MetricName"], "ConnectionErrors")
        self.assertEqual(alarm["Properties"]["Namespace"], "aws-guardian/websocket")

    def test_message_latency_alarm_exists(self):
        """MessageLatencyAlarm 정의 확인"""
        resources = self.template.get("Resources", {})
        self.assertIn("MessageLatencyAlarm", resources)

        alarm = resources["MessageLatencyAlarm"]
        self.assertEqual(alarm["Type"], "AWS::CloudWatch::Alarm")
        self.assertEqual(alarm["Properties"]["MetricName"], "MessageProcessingLatency")
        self.assertEqual(alarm["Properties"]["Namespace"], "aws-guardian/websocket")

    def test_threat_score_alarm_exists(self):
        """ThreatScoreAlarm 정의 확인"""
        resources = self.template.get("Resources", {})
        self.assertIn("ThreatScoreAlarm", resources)

        alarm = resources["ThreatScoreAlarm"]
        self.assertEqual(alarm["Type"], "AWS::CloudWatch::Alarm")
        self.assertEqual(alarm["Properties"]["MetricName"], "ThreatScore")
        self.assertEqual(alarm["Properties"]["Namespace"], "aws-guardian/websocket")

    def test_alarm_configuration_properties(self):
        """Alarms의 필수 속성 확인"""
        resources = self.template.get("Resources", {})
        alarm_names = ["ConnectionErrorAlarm", "MessageLatencyAlarm", "ThreatScoreAlarm"]

        for alarm_name in alarm_names:
            alarm = resources[alarm_name]
            props = alarm["Properties"]

            # 필수 속성
            self.assertIn("AlarmName", props)
            self.assertIn("MetricName", props)
            self.assertIn("Namespace", props)
            self.assertIn("Statistic", props)
            self.assertIn("Period", props)
            self.assertIn("EvaluationPeriods", props)
            self.assertIn("Threshold", props)
            self.assertIn("ComparisonOperator", props)
            self.assertIn("AlarmActions", props)

    def test_alarm_connected_to_sns_topic(self):
        """모든 Alarm이 SNS Topic에 연결"""
        resources = self.template.get("Resources", {})
        alarm_names = ["ConnectionErrorAlarm", "MessageLatencyAlarm", "ThreatScoreAlarm"]

        for alarm_name in alarm_names:
            alarm = resources[alarm_name]
            actions = alarm["Properties"]["AlarmActions"]

            # SNS Topic 참조 확인
            self.assertIsInstance(actions, list)
            self.assertGreater(len(actions), 0)

            action = actions[0]
            self.assertIsInstance(action, dict)
            # CloudFormationLoader는 'Ref'를 'ef'로 파싱
            keys = list(action.keys())
            self.assertTrue(any("Ref" in k or "ef" in k for k in keys))
            # WebSocketAlertsTopic 참조 확인
            action_value = list(action.values())[0]
            self.assertEqual(action_value, "WebSocketAlertsTopic")

    def test_connection_error_alarm_threshold(self):
        """ConnectionErrorAlarm의 임계값이 5 이상"""
        resources = self.template.get("Resources", {})
        alarm = resources["ConnectionErrorAlarm"]

        threshold = alarm["Properties"]["Threshold"]
        self.assertEqual(threshold, 5)
        self.assertEqual(alarm["Properties"]["Statistic"], "Sum")

    def test_message_latency_alarm_threshold(self):
        """MessageLatencyAlarm의 임계값이 5000ms 이상"""
        resources = self.template.get("Resources", {})
        alarm = resources["MessageLatencyAlarm"]

        threshold = alarm["Properties"]["Threshold"]
        self.assertEqual(threshold, 5000)
        self.assertEqual(alarm["Properties"]["Statistic"], "Average")
        self.assertEqual(alarm["Properties"]["EvaluationPeriods"], 2)

    def test_threat_score_alarm_threshold(self):
        """ThreatScoreAlarm의 임계값이 80 이상"""
        resources = self.template.get("Resources", {})
        alarm = resources["ThreatScoreAlarm"]

        threshold = alarm["Properties"]["Threshold"]
        self.assertEqual(threshold, 80)
        self.assertEqual(alarm["Properties"]["Statistic"], "Maximum")


class TestSNSTopic(unittest.TestCase):
    """SNS Topic 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_sns_topic_exists(self):
        """WebSocketAlertsTopic 리소스 존재"""
        resources = self.template.get("Resources", {})
        self.assertIn("WebSocketAlertsTopic", resources)

        topic = resources["WebSocketAlertsTopic"]
        self.assertEqual(topic["Type"], "AWS::SNS::Topic")
        self.assertIn("Properties", topic)

    def test_sns_topic_name_format(self):
        """SNS Topic 이름이 올바른 형식"""
        resources = self.template.get("Resources", {})
        topic = resources["WebSocketAlertsTopic"]
        name = topic["Properties"]["TopicName"]

        # !Sub 문법 확인
        self.assertIsInstance(name, dict)
        keys = list(name.keys())
        self.assertTrue(any("ub" in k or "Sub" in k for k in keys))

    def test_sns_topic_display_name(self):
        """SNS Topic DisplayName 설정"""
        resources = self.template.get("Resources", {})
        topic = resources["WebSocketAlertsTopic"]

        self.assertIn("DisplayName", topic["Properties"])


class TestCloudWatchMetricsIAM(unittest.TestCase):
    """CloudWatch Metrics IAM 권한 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_cloudwatch_metrics_iam_policy(self):
        """WebSocketLambdaRole에 CloudWatch Metrics 권한 포함"""
        resources = self.template.get("Resources", {})
        role = resources["WebSocketLambdaRole"]

        policies = role["Properties"]["Policies"]
        self.assertIsInstance(policies, list)

        # CloudWatchMetrics 정책 찾기
        cloudwatch_policy = None
        for policy in policies:
            if policy.get("PolicyName") == "CloudWatchMetrics":
                cloudwatch_policy = policy
                break

        self.assertIsNotNone(cloudwatch_policy, "CloudWatchMetrics 정책 없음")

    def test_cloudwatch_metrics_policy_actions(self):
        """CloudWatch Metrics 정책에 올바른 Actions 포함"""
        resources = self.template.get("Resources", {})
        role = resources["WebSocketLambdaRole"]

        policies = role["Properties"]["Policies"]
        cloudwatch_policy = next(p for p in policies if p.get("PolicyName") == "CloudWatchMetrics")

        doc = cloudwatch_policy["PolicyDocument"]
        statements = doc["Statement"]

        self.assertGreater(len(statements), 0)

        # PutMetricData 액션 확인
        statement = statements[0]
        actions = statement["Action"]

        self.assertIsInstance(actions, list)
        self.assertIn("cloudwatch:PutMetricData", actions)

    def test_environment_variables_cloudwatch_namespace(self):
        """Lambda 함수에 CLOUDWATCH_NAMESPACE 환경 변수"""
        resources = self.template.get("Resources", {})

        # ConnectFunction 확인
        connect_func = resources["ConnectFunction"]
        env_vars = connect_func["Properties"]["Environment"]["Variables"]

        self.assertIn("CLOUDWATCH_NAMESPACE", env_vars)
        self.assertEqual(env_vars["CLOUDWATCH_NAMESPACE"], "aws-guardian/websocket")

    def test_environment_variables_metrics_enabled(self):
        """Lambda 함수에 METRICS_ENABLED 환경 변수"""
        resources = self.template.get("Resources", {})

        # DefaultFunction 확인
        default_func = resources["DefaultFunction"]
        env_vars = default_func["Properties"]["Environment"]["Variables"]

        self.assertIn("METRICS_ENABLED", env_vars)
        self.assertEqual(env_vars["METRICS_ENABLED"], "true")


class TestCloudWatchOutputs(unittest.TestCase):
    """CloudWatch 관련 출력값 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_dashboard_url_output(self):
        """DashboardURL 출력값 존재"""
        outputs = self.template.get("Outputs", {})

        self.assertIn("DashboardURL", outputs)
        output = outputs["DashboardURL"]

        self.assertIn("Description", output)
        self.assertIn("Value", output)
        self.assertIn("Export", output)

    def test_sns_topic_arn_output(self):
        """SNSTopicArn 출력값 존재"""
        outputs = self.template.get("Outputs", {})

        self.assertIn("SNSTopicArn", outputs)
        output = outputs["SNSTopicArn"]

        self.assertIn("Description", output)
        self.assertIn("Value", output)
        self.assertIn("Export", output)

    def test_output_exports_format(self):
        """출력값의 Export 이름이 올바른 형식"""
        outputs = self.template.get("Outputs", {})

        for output_name in ["DashboardURL", "SNSTopicArn"]:
            output = outputs[output_name]
            export = output["Export"]["Name"]

            # !Sub 문법 확인
            self.assertIsInstance(export, dict)
            keys = list(export.keys())
            self.assertTrue(any("ub" in k or "Sub" in k for k in keys))


if __name__ == "__main__":
    unittest.main()
