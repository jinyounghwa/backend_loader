"""Tests for EC2 checker - LocalStack integration tests"""
import unittest
import time
import boto3

from guardian.checkers.ec2 import EC2Checker
from guardian.config import Config
from guardian.responders.aws_action_executor import AWSActionExecutor


class TestEC2Checker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        kwargs = Config.get_boto3_kwargs()
        cls.ec2_client = boto3.client('ec2', **kwargs)
        cls.test_instance_ids = []
        try:
            response = cls.ec2_client.run_instances(
                ImageId='ami-12345678',
                InstanceType='t2.micro',
                MinCount=2,
                MaxCount=2,
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'test-guardian-instance'},
                        {'Key': 'TestSuite', 'Value': 'true'}
                    ]
                }]
            )
            for instance in response['Instances']:
                cls.test_instance_ids.append(instance['InstanceId'])
            time.sleep(1)
        except Exception as e:
            print(f"Setup warning (instances may already exist): {e}")

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.test_instance_ids:
                cls.ec2_client.terminate_instances(InstanceIds=cls.test_instance_ids)
        except Exception:
            pass

    def setUp(self):
        self.ec2_checker = EC2Checker(authorized_regions=['us-east-1', 'us-west-2'])

    def test_get_all_instances(self):
        instances = self.ec2_checker._get_all_instances()
        self.assertIsInstance(instances, dict)
        self.assertIn('us-east-1', instances)
        self.assertGreaterEqual(len(instances['us-east-1']), 2)
        for instance in instances['us-east-1']:
            self.assertIn('InstanceId', instance)
            self.assertIn('InstanceType', instance)
            self.assertIn('State', instance)

    def test_no_unauthorized_when_us_east_1_authorized(self):
        checker = EC2Checker(authorized_regions=['us-east-1'])
        unauthorized = checker._get_unauthorized_regions_instances()
        self.assertEqual(len(unauthorized), 0)

    def test_unauthorized_detected_when_us_east_1_not_authorized(self):
        checker = EC2Checker(authorized_regions=['eu-west-1', 'ap-northeast-1'])
        unauthorized = checker._get_unauthorized_regions_instances()
        self.assertIn('us-east-1', unauthorized)

    def test_check_ec2_anomalies_structure(self):
        is_anomaly, data = self.ec2_checker.check_ec2_anomalies()
        self.assertIsInstance(is_anomaly, bool)
        for key in ['is_anomaly', 'unauthorized_region_instances',
                     'exposed_instances', 'new_instances', 'anomalies', 'timestamp']:
            self.assertIn(key, data)

    def test_stop_instance_via_executor(self):
        if not self.test_instance_ids:
            self.skipTest("No test instances available")
        executor = AWSActionExecutor()
        success = executor.stop_ec2_instance(
            self.test_instance_ids[0], 'us-east-1'
        )
        self.assertTrue(success)

    def test_check_returns_check_result(self):
        result = self.ec2_checker.check()
        self.assertIn(result.severity, ['INFO', 'HIGH', 'CRITICAL'])
        self.assertIsNotNone(result.details)


if __name__ == '__main__':
    unittest.main()
