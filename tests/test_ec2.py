"""Tests for EC2 checker - LocalStack integration tests"""
import unittest
import os
import sys
import time
import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from guardian.checkers.ec2 import EC2Checker
from guardian.config import Config


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
        instances = self.ec2_checker.get_all_instances()
        self.assertIsInstance(instances, dict)
        self.assertIn('us-east-1', instances)
        self.assertGreaterEqual(len(instances['us-east-1']), 2)
        for instance in instances['us-east-1']:
            self.assertIn('InstanceId', instance)
            self.assertIn('InstanceType', instance)
            self.assertIn('State', instance)

    def test_no_unauthorized_when_us_east_1_authorized(self):
        checker = EC2Checker(authorized_regions=['us-east-1'])
        unauthorized = checker.get_unauthorized_regions_instances()
        self.assertEqual(len(unauthorized), 0)

    def test_unauthorized_detected_when_us_east_1_not_authorized(self):
        checker = EC2Checker(authorized_regions=['eu-west-1', 'ap-northeast-1'])
        unauthorized = checker.get_unauthorized_regions_instances()
        self.assertIn('us-east-1', unauthorized)

    def test_check_ec2_anomalies_structure(self):
        is_anomaly, data = self.ec2_checker.check_ec2_anomalies()
        self.assertIsInstance(is_anomaly, bool)
        for key in ['is_anomaly', 'unauthorized_region_instances',
                     'exposed_instances', 'new_instances', 'anomalies', 'timestamp']:
            self.assertIn(key, data)

    def test_stop_instance(self):
        if not self.test_instance_ids:
            self.skipTest("No test instances available")
        success = self.ec2_checker.stop_instance(
            self.test_instance_ids[0], 'us-east-1'
        )
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
