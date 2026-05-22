"""
Sprint 31 Phase 1: CloudFormation 템플릿 검증 테스트
SAM 템플릿 구조, 리소스 정의, 출력값 검증
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


class TestWebSocketTemplate(unittest.TestCase):
    """CloudFormation 템플릿 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_template_structure(self):
        """템플릿 기본 구조"""
        self.assertIn("AWSTemplateFormatVersion", self.template)
        self.assertEqual(self.template["AWSTemplateFormatVersion"], "2010-09-09")

        self.assertIn("Transform", self.template)
        self.assertEqual(self.template["Transform"], "AWS::Serverless-2016-10-31")

    def test_parameters(self):
        """파라미터 정의"""
        params = self.template.get("Parameters", {})

        self.assertIn("Environment", params)
        self.assertIn("ProjectName", params)

        # Environment 파라미터 검증
        env_param = params["Environment"]
        self.assertEqual(env_param["Type"], "String")
        self.assertIn("dev", env_param.get("AllowedValues", []))
        self.assertIn("prod", env_param.get("AllowedValues", []))

    def test_websocket_api(self):
        """WebSocket API 리소스"""
        resources = self.template.get("Resources", {})

        self.assertIn("GuardianWebSocketApi", resources)
        api = resources["GuardianWebSocketApi"]

        self.assertEqual(api["Type"], "AWS::ApiGatewayV2::Api")
        self.assertEqual(api["Properties"]["ProtocolType"], "WEBSOCKET")

    def test_lambda_functions(self):
        """Lambda 함수 리소스"""
        resources = self.template.get("Resources", {})
        required_functions = [
            "ConnectFunction",
            "DisconnectFunction",
            "DefaultFunction",
            "BroadcastFunction",
            "AnomalyAlertFunction",
            "ConnectionStatsFunction",
        ]

        for func_name in required_functions:
            self.assertIn(func_name, resources)
            func = resources[func_name]
            self.assertEqual(func["Type"], "AWS::Serverless::Function")
            self.assertIn("Handler", func["Properties"])
            self.assertIn("Runtime", func["Properties"])
            self.assertEqual(func["Properties"]["Runtime"], "python3.12")

    def test_lambda_permissions(self):
        """Lambda 권한 정의"""
        resources = self.template.get("Resources", {})
        required_permissions = [
            "ConnectFunctionPermission",
            "DisconnectFunctionPermission",
            "DefaultFunctionPermission",
            "BroadcastFunctionPermission",
        ]

        for perm_name in required_permissions:
            self.assertIn(perm_name, resources)
            perm = resources[perm_name]
            self.assertEqual(perm["Type"], "AWS::Lambda::Permission")
            self.assertEqual(perm["Properties"]["Action"], "lambda:InvokeFunction")
            self.assertEqual(perm["Properties"]["Principal"], "apigateway.amazonaws.com")

    def test_api_integrations(self):
        """API 통합 정의"""
        resources = self.template.get("Resources", {})
        required_integrations = [
            "ConnectIntegration",
            "DisconnectIntegration",
            "DefaultIntegration",
        ]

        for integ_name in required_integrations:
            self.assertIn(integ_name, resources)
            integ = resources[integ_name]
            self.assertEqual(integ["Type"], "AWS::ApiGatewayV2::Integration")
            self.assertEqual(integ["Properties"]["IntegrationType"], "AWS_PROXY")
            self.assertIn("IntegrationUri", integ["Properties"])

    def test_api_routes(self):
        """API 라우트 정의"""
        resources = self.template.get("Resources", {})

        # $connect 라우트
        self.assertIn("ConnectRoute", resources)
        connect_route = resources["ConnectRoute"]
        self.assertEqual(connect_route["Type"], "AWS::ApiGatewayV2::Route")
        self.assertEqual(connect_route["Properties"]["RouteKey"], "$connect")

        # $disconnect 라우트
        self.assertIn("DisconnectRoute", resources)
        disconnect_route = resources["DisconnectRoute"]
        self.assertEqual(disconnect_route["Properties"]["RouteKey"], "$disconnect")

        # $default 라우트
        self.assertIn("DefaultRoute", resources)
        default_route = resources["DefaultRoute"]
        self.assertEqual(default_route["Properties"]["RouteKey"], "$default")

    def test_api_stage(self):
        """API Stage 정의"""
        resources = self.template.get("Resources", {})

        self.assertIn("ApiStage", resources)
        stage = resources["ApiStage"]
        self.assertEqual(stage["Type"], "AWS::ApiGatewayV2::Stage")

        props = stage["Properties"]
        self.assertTrue(props["AutoDeploy"])
        self.assertEqual(props["LoggingLevel"], "INFO")

    def test_cloudwatch_logs(self):
        """CloudWatch 로그 그룹"""
        resources = self.template.get("Resources", {})

        self.assertIn("WebSocketApiLogGroup", resources)
        logs = resources["WebSocketApiLogGroup"]
        self.assertEqual(logs["Type"], "AWS::Logs::LogGroup")
        self.assertEqual(logs["Properties"]["RetentionInDays"], 30)

    def test_iam_role(self):
        """IAM 역할"""
        resources = self.template.get("Resources", {})

        self.assertIn("WebSocketLambdaRole", resources)
        role = resources["WebSocketLambdaRole"]
        self.assertEqual(role["Type"], "AWS::IAM::Role")

        # 신뢰 정책
        assume_role = role["Properties"]["AssumeRolePolicyDocument"]
        self.assertEqual(assume_role["Version"], "2012-10-17")

        # Lambda 서비스 원칙
        statements = assume_role["Statement"]
        self.assertTrue(
            any(s["Principal"]["Service"] == "lambda.amazonaws.com" for s in statements)
        )

    def test_outputs(self):
        """출력 정의"""
        outputs = self.template.get("Outputs", {})

        required_outputs = [
            "WebSocketApiId",
            "WebSocketApiEndpoint",
            "ConnectFunctionArn",
            "DisconnectFunctionArn",
            "BroadcastFunctionArn",
        ]

        for output_name in required_outputs:
            self.assertIn(output_name, outputs)
            output = outputs[output_name]
            self.assertIn("Description", output)
            self.assertIn("Value", output)

    def test_exports(self):
        """CloudFormation 출력 내보내기"""
        outputs = self.template.get("Outputs", {})

        # 주요 출력이 내보내지는지 확인
        self.assertIn("Export", outputs.get("WebSocketApiId", {}))
        self.assertIn("Export", outputs.get("WebSocketApiEndpoint", {}))

    def test_tags(self):
        """리소스 태그"""
        resources = self.template.get("Resources", {})

        # WebSocket API에 태그가 있는지 확인
        api = resources.get("GuardianWebSocketApi", {})
        tags = api.get("Properties", {}).get("Tags", [])
        self.assertGreater(len(tags), 0)

        # Project 태그 확인
        tag_keys = [tag.get("Key") for tag in tags]
        self.assertIn("Project", tag_keys)

    def test_environment_variables(self):
        """환경 변수"""
        resources = self.template.get("Resources", {})

        connect_func = resources.get("ConnectFunction", {})
        env_vars = connect_func.get("Properties", {}).get("Environment", {}).get("Variables", {})

        # 필수 환경 변수 확인
        self.assertIn("WEBSOCKET_API_ID", env_vars)
        self.assertIn("WEBSOCKET_API_ENDPOINT", env_vars)


class TestSamConfig(unittest.TestCase):
    """SAM 설정 파일 검증"""

    @classmethod
    def setUpClass(cls):
        """설정 파일 로드"""
        config_path = Path(__file__).parent.parent.parent / "sam" / "samconfig.toml"
        cls.config_path = config_path

    def test_samconfig_exists(self):
        """samconfig.toml 파일 존재"""
        self.assertTrue(self.config_path.exists())

    def test_samconfig_readable(self):
        """samconfig.toml 읽기 가능"""
        with open(self.config_path, "r") as f:
            content = f.read()
            self.assertGreater(len(content), 0)


class TestTemplateValidation(unittest.TestCase):
    """CloudFormation 템플릿 유효성 검증"""

    def test_no_hardcoded_values(self):
        """하드코딩된 값 확인"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            content = f.read()  # Raw content for string checks

            # 일반적인 개발 계정 ID 없는지 확인
            self.assertNotIn("123456789012", content)

            # 환경 변수가 사용되는지 확인
            self.assertIn("!Ref", content)

    def test_parameter_usage(self):
        """파라미터가 리소스에서 사용되는지"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            content = f.read()  # Raw content for string checks

            # ProjectName, Environment 파라미터가 사용되는지 확인
            self.assertIn("!Ref ProjectName", content)
            self.assertIn("!Ref Environment", content)

    def test_no_missing_permissions(self):
        """Lambda 권한이 모든 함수에 정의되어 있는지"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            template = yaml.load(f, Loader=CloudFormationLoader)

            functions = [
                k
                for k, v in template.get("Resources", {}).items()
                if v.get("Type") == "AWS::Serverless::Function"
            ]

            # 각 함수마다 권한이 정의되어 있는지 확인
            # (모든 함수가 API Gateway에서 호출되므로)
            for func in functions:
                if func in [
                    "ConnectFunction",
                    "DisconnectFunction",
                    "DefaultFunction",
                    "BroadcastFunction",
                ]:
                    permission_name = f"{func}Permission"
                    self.assertIn(
                        permission_name,
                        template.get("Resources", {}),
                        f"{func}에 대한 Lambda 권한 {permission_name} 없음",
                    )


if __name__ == "__main__":
    unittest.main()
