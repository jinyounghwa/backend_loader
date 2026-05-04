#!/usr/bin/env python3
"""Initialize LocalStack for AWS Guardian testing"""
import os
import sys
import boto3
from botocore.config import Config

# Set environment variables
os.environ['AWS_ENDPOINT_URL_EC2'] = 'http://localhost:4566'
os.environ['AWS_ENDPOINT_URL_S3'] = 'http://localhost:4566'
os.environ['AWS_ENDPOINT_URL_DYNAMODB'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

def init_dynamodb():
    print("📊 Creating DynamoDB table...")
    try:
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1'
        )

        # Drop old table if it has the wrong schema (timestamp HASH)
        try:
            old_desc = dynamodb.describe_table(TableName='aws-guardian-events')
            key_schema = old_desc['Table']['KeySchema']
            hash_key = next((k for k in key_schema if k['KeyType'] == 'HASH'), None)
            if hash_key and hash_key['AttributeName'] == 'timestamp':
                print("  Dropping old table with outdated schema...")
                dynamodb.delete_table(TableName='aws-guardian-events')
                waiter = dynamodb.get_waiter('table_not_exists')
                waiter.wait(TableName='aws-guardian-events')
        except dynamodb.exceptions.ResourceNotFoundException:
            pass
        except Exception:
            pass

        dynamodb.create_table(
            TableName='aws-guardian-events',
            KeySchema=[
                {'AttributeName': 'event_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'event_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'event_type', 'AttributeType': 'S'},
                {'AttributeName': 'severity', 'AttributeType': 'S'},
                {'AttributeName': 'gsi_pk', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'AllEventsIndex',
                    'KeySchema': [
                        {'AttributeName': 'gsi_pk', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': 'TypeTimestampIndex',
                    'KeySchema': [
                        {'AttributeName': 'event_type', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': 'SeverityTimestampIndex',
                    'KeySchema': [
                        {'AttributeName': 'severity', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("✅ DynamoDB table created")
    except dynamodb.exceptions.ResourceInUseException:
        print("✅ DynamoDB table already exists")
    except Exception as e:
        print(f"⚠️ Error creating DynamoDB table: {e}")

def init_s3():
    """Create S3 buckets"""
    print("🪣 Creating test S3 buckets...")
    try:
        s3 = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1'
        )

        buckets = ['test-bucket-1', 'test-bucket-2', 'public-test-bucket']
        for bucket in buckets:
            try:
                s3.create_bucket(Bucket=bucket)
                print(f"✅ Created bucket: {bucket}")
            except s3.exceptions.BucketAlreadyExists:
                print(f"✅ Bucket {bucket} already exists")
            except Exception as e:
                print(f"⚠️ Error creating bucket {bucket}: {e}")

    except Exception as e:
        print(f"⚠️ Error initializing S3: {e}")

def init_ec2():
    """Create test EC2 resources"""
    print("🖥️ Creating test EC2 resources...")
    try:
        ec2 = boto3.client(
            'ec2',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1'
        )

        # Create security group
        try:
            sg_response = ec2.create_security_group(
                GroupName='test-sg',
                Description='Test security group'
            )
            sg_id = sg_response['GroupId']
            print(f"✅ Created security group: {sg_id}")

            # Add open rule (for testing exposure detection)
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            print(f"✅ Added open SSH rule to security group")

        except Exception as e:
            print(f"⚠️ Error with security group: {e}")

        # Create instance
        try:
            instances = ec2.run_instances(
                ImageId='ami-12345678',
                MinCount=1,
                MaxCount=1,
                InstanceType='t2.micro'
            )
            instance_id = instances['Instances'][0]['InstanceId']
            print(f"✅ Created instance: {instance_id}")
        except Exception as e:
            print(f"⚠️ Error creating instance: {e}")

    except Exception as e:
        print(f"⚠️ Error initializing EC2: {e}")

def init_ssm():
    """Create SSM parameters"""
    print("⚙️ Creating SSM parameters...")
    try:
        ssm = boto3.client(
            'ssm',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1'
        )

        params = {
            '/guardian/cost-threshold': '10.0',
            '/guardian/authorized-regions': 'us-east-1,us-west-2'
        }

        for param_name, param_value in params.items():
            try:
                ssm.put_parameter(
                    Name=param_name,
                    Value=param_value,
                    Type='String',
                    Overwrite=True
                )
                print(f"✅ Created parameter: {param_name}")
            except Exception as e:
                print(f"⚠️ Error creating parameter {param_name}: {e}")

    except Exception as e:
        print(f"⚠️ Error initializing SSM: {e}")

def main():
    """Initialize LocalStack"""
    print("🚀 Initializing LocalStack for AWS Guardian")
    print("=" * 50)

    init_dynamodb()
    init_s3()
    init_ec2()
    init_ssm()

    print("=" * 50)
    print("✨ LocalStack initialization complete!")
    print("")
    print("Environment variables:")
    print("  LOCALSTACK_ENDPOINT=http://localhost:4566")
    print("  AWS_DEFAULT_REGION=us-east-1")
    print("  AWS_ACCESS_KEY_ID=test")
    print("  AWS_SECRET_ACCESS_KEY=test")

if __name__ == '__main__':
    main()
