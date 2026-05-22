"""
Sprint 32 Phase 1: Audit Logs Query API 테스트
HTTP API Gateway, Lambda 함수, 권한 검증
"""

import unittest
from pathlib import Path

import yaml


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


class TestAuditApiGateway(unittest.TestCase):
    """HTTP API Gateway 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_audit_api_gateway_exists(self):
        """AuditApiGateway 리소스 존재"""
        resources = self.template.get("Resources", {})
        self.assertIn("AuditApiGateway", resources)

        api = resources["AuditApiGateway"]
        self.assertEqual(api["Type"], "AWS::ApiGatewayV2::Api")
        self.assertEqual(api["Properties"]["ProtocolType"], "HTTP")

    def test_audit_api_gateway_name(self):
        """API Gateway 이름이 올바른 형식"""
        resources = self.template.get("Resources", {})
        api = resources["AuditApiGateway"]
        name = api["Properties"]["Name"]

        # !Sub 문법 확인
        self.assertIsInstance(name, dict)
        keys = list(name.keys())
        self.assertTrue(any("ub" in k or "Sub" in k for k in keys))

    def test_audit_api_stage(self):
        """API Stage 자동 배포 설정"""
        resources = self.template.get("Resources", {})
        self.assertIn("AuditApiStage", resources)

        stage = resources["AuditApiStage"]
        self.assertEqual(stage["Type"], "AWS::ApiGatewayV2::Stage")
        self.assertTrue(stage["Properties"]["AutoDeploy"])


class TestAuditApiRoute(unittest.TestCase):
    """API Route 및 Integration 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_audit_api_integration_exists(self):
        """AuditApiIntegration 리소스 존재"""
        resources = self.template.get("Resources", {})
        self.assertIn("AuditApiIntegration", resources)

        integration = resources["AuditApiIntegration"]
        self.assertEqual(integration["Type"], "AWS::ApiGatewayV2::Integration")
        self.assertEqual(integration["Properties"]["IntegrationType"], "AWS_PROXY")

    def test_audit_api_route_exists(self):
        """GET /audit-logs 라우트 정의"""
        resources = self.template.get("Resources", {})
        self.assertIn("AuditApiRoute", resources)

        route = resources["AuditApiRoute"]
        self.assertEqual(route["Type"], "AWS::ApiGatewayV2::Route")
        self.assertEqual(route["Properties"]["RouteKey"], "GET /audit-logs")

    def test_audit_api_route_to_integration(self):
        """라우트가 통합에 연결"""
        resources = self.template.get("Resources", {})
        route = resources["AuditApiRoute"]

        target = route["Properties"]["Target"]
        # Target은 !Sub로 파싱됨
        if isinstance(target, dict):
            target_str = str(target)
        else:
            target_str = target
        self.assertIn("integrations", target_str)


class TestGetAuditLogsFunction(unittest.TestCase):
    """GetAuditLogs Lambda 함수 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_get_audit_logs_function_exists(self):
        """GetAuditLogsFunction 리소스 존재"""
        resources = self.template.get("Resources", {})
        self.assertIn("GetAuditLogsFunction", resources)

        func = resources["GetAuditLogsFunction"]
        self.assertEqual(func["Type"], "AWS::Serverless::Function")
        self.assertEqual(func["Properties"]["Runtime"], "python3.12")

    def test_get_audit_logs_handler(self):
        """Handler 경로 확인"""
        resources = self.template.get("Resources", {})
        func = resources["GetAuditLogsFunction"]

        handler = func["Properties"]["Handler"]
        self.assertEqual(handler, "guardian/handlers/audit_api_handler.handle_get_audit_logs")

    def test_get_audit_logs_environment_variables(self):
        """환경 변수 설정"""
        resources = self.template.get("Resources", {})
        func = resources["GetAuditLogsFunction"]

        env_vars = func["Properties"]["Environment"]["Variables"]
        self.assertIn("AUDIT_LOGS_TABLE", env_vars)


class TestAuditApiPermission(unittest.TestCase):
    """Lambda 권한 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_get_audit_logs_function_permission_exists(self):
        """GetAuditLogsFunctionPermission 리소스 존재"""
        resources = self.template.get("Resources", {})
        self.assertIn("GetAuditLogsFunctionPermission", resources)

        perm = resources["GetAuditLogsFunctionPermission"]
        self.assertEqual(perm["Type"], "AWS::Lambda::Permission")

    def test_get_audit_logs_permission_principal(self):
        """권한이 API Gateway에 의한 호출"""
        resources = self.template.get("Resources", {})
        perm = resources["GetAuditLogsFunctionPermission"]

        props = perm["Properties"]
        self.assertEqual(props["Principal"], "apigateway.amazonaws.com")
        self.assertEqual(props["Action"], "lambda:InvokeFunction")

    def test_get_audit_logs_permission_source(self):
        """권한의 SourceArn이 AuditApiGateway 참조"""
        resources = self.template.get("Resources", {})
        perm = resources["GetAuditLogsFunctionPermission"]

        source_arn = perm["Properties"]["SourceArn"]
        self.assertIsInstance(source_arn, dict)
        # !Sub 참조 확인
        keys = list(source_arn.keys())
        self.assertTrue(any("ub" in k or "Sub" in k for k in keys))


class TestAuditApiOutputs(unittest.TestCase):
    """API 출력값 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_audit_api_endpoint_output_exists(self):
        """AuditApiEndpoint 출력값 존재"""
        outputs = self.template.get("Outputs", {})

        self.assertIn("AuditApiEndpoint", outputs)
        output = outputs["AuditApiEndpoint"]

        self.assertIn("Description", output)
        self.assertIn("Value", output)
        self.assertIn("Export", output)

    def test_audit_api_endpoint_format(self):
        """출력값이 올바른 형식"""
        outputs = self.template.get("Outputs", {})
        output = outputs["AuditApiEndpoint"]

        value = output["Value"]
        # !Sub 형식 확인
        self.assertIsInstance(value, dict)
        keys = list(value.keys())
        self.assertTrue(any("ub" in k or "Sub" in k for k in keys))

    def test_audit_api_endpoint_export(self):
        """Export 이름이 올바른 형식"""
        outputs = self.template.get("Outputs", {})
        output = outputs["AuditApiEndpoint"]

        export = output["Export"]["Name"]
        self.assertIsInstance(export, dict)
        keys = list(export.keys())
        self.assertTrue(any("ub" in k or "Sub" in k for k in keys))


class TestAuditApiIntegration(unittest.TestCase):
    """Integration 상세 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_integration_payload_format(self):
        """PayloadFormatVersion 설정"""
        resources = self.template.get("Resources", {})
        integration = resources["AuditApiIntegration"]

        self.assertEqual(integration["Properties"]["PayloadFormatVersion"], "2.0")

    def test_integration_lambda_uri(self):
        """IntegrationUri가 Lambda ARN 참조"""
        resources = self.template.get("Resources", {})
        integration = resources["AuditApiIntegration"]

        uri = integration["Properties"]["IntegrationUri"]
        self.assertIsInstance(uri, dict)
        keys = list(uri.keys())
        self.assertTrue(any("ub" in k or "Sub" in k for k in keys))


if __name__ == "__main__":
    unittest.main()
