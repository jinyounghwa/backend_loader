"""
Sprint 31 Phase 3: Audit Logging 테스트
DynamoDB 감사 로그 테이블, IAM 권한, 환경 변수 검증
"""

import unittest
import yaml
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


class TestDynamoDBTable(unittest.TestCase):
    """DynamoDB 테이블 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_websocket_audit_logs_table_exists(self):
        """WebSocketAuditLogsTable 리소스 존재"""
        resources = self.template.get("Resources", {})
        self.assertIn("WebSocketAuditLogsTable", resources)

        table = resources["WebSocketAuditLogsTable"]
        self.assertEqual(table["Type"], "AWS::DynamoDB::Table")
        self.assertIn("Properties", table)

    def test_table_billing_mode(self):
        """테이블 청구 모드 PAY_PER_REQUEST"""
        resources = self.template.get("Resources", {})
        table = resources["WebSocketAuditLogsTable"]

        self.assertEqual(table["Properties"]["BillingMode"], "PAY_PER_REQUEST")

    def test_table_name_format(self):
        """테이블 이름이 올바른 형식"""
        resources = self.template.get("Resources", {})
        table = resources["WebSocketAuditLogsTable"]
        name = table["Properties"]["TableName"]

        # !Sub 문법 확인
        self.assertIsInstance(name, dict)
        keys = list(name.keys())
        self.assertTrue(any("ub" in k or "Sub" in k for k in keys))

    def test_ttl_specification(self):
        """TTL 설정 활성화"""
        resources = self.template.get("Resources", {})
        table = resources["WebSocketAuditLogsTable"]

        self.assertIn("TimeToLiveSpecification", table["Properties"])
        ttl = table["Properties"]["TimeToLiveSpecification"]
        self.assertEqual(ttl["AttributeName"], "expiration_time")
        self.assertTrue(ttl["Enabled"])


class TestTableAttributes(unittest.TestCase):
    """DynamoDB 테이블 속성 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_attribute_definitions(self):
        """속성 정의 검증"""
        resources = self.template.get("Resources", {})
        table = resources["WebSocketAuditLogsTable"]

        attrs = table["Properties"]["AttributeDefinitions"]
        self.assertIsInstance(attrs, list)
        self.assertGreaterEqual(len(attrs), 2)

        # connection_id와 timestamp 확인
        attr_names = [attr["AttributeName"] for attr in attrs]
        self.assertIn("connection_id", attr_names)
        self.assertIn("timestamp", attr_names)

        # 타입 확인
        for attr in attrs:
            if attr["AttributeName"] == "connection_id":
                self.assertEqual(attr["AttributeType"], "S")
            elif attr["AttributeName"] == "timestamp":
                self.assertEqual(attr["AttributeType"], "S")

    def test_key_schema(self):
        """키 스키마 검증 (PK: connection_id, SK: timestamp)"""
        resources = self.template.get("Resources", {})
        table = resources["WebSocketAuditLogsTable"]

        keys = table["Properties"]["KeySchema"]
        self.assertIsInstance(keys, list)
        self.assertEqual(len(keys), 2)

        # HASH 키 (PK)
        hash_key = next((k for k in keys if k["KeyType"] == "HASH"), None)
        self.assertIsNotNone(hash_key)
        self.assertEqual(hash_key["AttributeName"], "connection_id")

        # RANGE 키 (SK)
        range_key = next((k for k in keys if k["KeyType"] == "RANGE"), None)
        self.assertIsNotNone(range_key)
        self.assertEqual(range_key["AttributeName"], "timestamp")

    def test_table_tags(self):
        """테이블에 Project와 Environment 태그"""
        resources = self.template.get("Resources", {})
        table = resources["WebSocketAuditLogsTable"]

        self.assertIn("Tags", table["Properties"])
        tags = table["Properties"]["Tags"]
        tag_keys = [tag.get("Key") for tag in tags]

        self.assertIn("Project", tag_keys)
        self.assertIn("Environment", tag_keys)


class TestDynamoDBAuditPolicy(unittest.TestCase):
    """DynamoDB IAM 권한 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_dynamodb_audit_policy_exists(self):
        """DynamoDBAuditPolicy 정책 존재"""
        resources = self.template.get("Resources", {})
        role = resources["WebSocketLambdaRole"]

        policies = role["Properties"]["Policies"]
        self.assertIsInstance(policies, list)

        audit_policy = None
        for policy in policies:
            if policy.get("PolicyName") == "DynamoDBAuditPolicy":
                audit_policy = policy
                break

        self.assertIsNotNone(audit_policy, "DynamoDBAuditPolicy 정책 없음")

    def test_dynamodb_audit_policy_actions(self):
        """DynamoDB 정책에 올바른 Actions"""
        resources = self.template.get("Resources", {})
        role = resources["WebSocketLambdaRole"]

        policies = role["Properties"]["Policies"]
        audit_policy = next(p for p in policies if p.get("PolicyName") == "DynamoDBAuditPolicy")

        doc = audit_policy["PolicyDocument"]
        statements = doc["Statement"]

        self.assertGreater(len(statements), 0)

        # 필요한 액션 확인
        statement = statements[0]
        actions = statement["Action"]

        self.assertIsInstance(actions, list)
        self.assertIn("dynamodb:PutItem", actions)
        self.assertIn("dynamodb:Query", actions)
        self.assertIn("dynamodb:GetItem", actions)

    def test_dynamodb_audit_policy_resource(self):
        """DynamoDB 정책이 테이블 ARN 참조"""
        resources = self.template.get("Resources", {})
        role = resources["WebSocketLambdaRole"]

        policies = role["Properties"]["Policies"]
        audit_policy = next(p for p in policies if p.get("PolicyName") == "DynamoDBAuditPolicy")

        doc = audit_policy["PolicyDocument"]
        statement = doc["Statement"][0]

        # Resource가 GetAtt 참조인지 확인
        resource = statement["Resource"]
        self.assertIsInstance(resource, dict)
        keys = list(resource.keys())
        self.assertTrue(
            any("GetAtt" in k or "etAtt" in k for k in keys), "Resource should use GetAtt"
        )


class TestAuditEnvironmentVariables(unittest.TestCase):
    """감사 로그 환경 변수 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_connect_function_audit_variables(self):
        """ConnectFunction에 감사 로그 환경 변수"""
        resources = self.template.get("Resources", {})
        func = resources["ConnectFunction"]

        env_vars = func["Properties"]["Environment"]["Variables"]
        self.assertIn("AUDIT_LOGS_TABLE", env_vars)
        self.assertIn("AUDIT_LOGS_ENABLED", env_vars)
        self.assertIn("TTL_DAYS", env_vars)

        self.assertEqual(env_vars["AUDIT_LOGS_ENABLED"], "true")
        self.assertEqual(env_vars["TTL_DAYS"], "90")

    def test_disconnect_function_audit_variables(self):
        """DisconnectFunction에 감사 로그 환경 변수"""
        resources = self.template.get("Resources", {})
        func = resources["DisconnectFunction"]

        env_vars = func["Properties"]["Environment"]["Variables"]
        self.assertIn("AUDIT_LOGS_TABLE", env_vars)
        self.assertIn("AUDIT_LOGS_ENABLED", env_vars)
        self.assertIn("TTL_DAYS", env_vars)

    def test_default_function_audit_variables(self):
        """DefaultFunction에 감사 로그 환경 변수"""
        resources = self.template.get("Resources", {})
        func = resources["DefaultFunction"]

        env_vars = func["Properties"]["Environment"]["Variables"]
        self.assertIn("AUDIT_LOGS_TABLE", env_vars)
        self.assertIn("AUDIT_LOGS_ENABLED", env_vars)
        self.assertIn("TTL_DAYS", env_vars)

    def test_broadcast_function_audit_variables(self):
        """BroadcastFunction에 감사 로그 환경 변수"""
        resources = self.template.get("Resources", {})
        func = resources["BroadcastFunction"]

        env_vars = func["Properties"]["Environment"]["Variables"]
        self.assertIn("AUDIT_LOGS_TABLE", env_vars)
        self.assertIn("AUDIT_LOGS_ENABLED", env_vars)
        self.assertIn("TTL_DAYS", env_vars)


class TestAuditOutputs(unittest.TestCase):
    """감사 로그 출력값 검증"""

    @classmethod
    def setUpClass(cls):
        """템플릿 로드"""
        template_path = Path(__file__).parent.parent.parent / "sam" / "template.yaml"
        with open(template_path, "r") as f:
            cls.template = yaml.load(f, Loader=CloudFormationLoader)

    def test_audit_logs_table_name_output(self):
        """AuditLogsTableName 출력값 존재"""
        outputs = self.template.get("Outputs", {})

        self.assertIn("AuditLogsTableName", outputs)
        output = outputs["AuditLogsTableName"]

        self.assertIn("Description", output)
        self.assertIn("Value", output)
        self.assertIn("Export", output)

    def test_audit_logs_table_arn_output(self):
        """AuditLogsTableArn 출력값 존재"""
        outputs = self.template.get("Outputs", {})

        self.assertIn("AuditLogsTableArn", outputs)
        output = outputs["AuditLogsTableArn"]

        self.assertIn("Description", output)
        self.assertIn("Value", output)
        self.assertIn("Export", output)

    def test_output_exports_format(self):
        """출력값의 Export 이름이 올바른 형식"""
        outputs = self.template.get("Outputs", {})

        for output_name in ["AuditLogsTableName", "AuditLogsTableArn"]:
            output = outputs[output_name]
            export = output["Export"]["Name"]

            # !Sub 문법 확인
            self.assertIsInstance(export, dict)
            keys = list(export.keys())
            self.assertTrue(any("ub" in k or "Sub" in k for k in keys))


if __name__ == "__main__":
    unittest.main()
