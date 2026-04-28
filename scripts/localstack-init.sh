#!/bin/bash
set -e

echo "🚀 LocalStack initialization script"
echo "=================================="

# Wait for LocalStack to be healthy
echo "⏳ Waiting for LocalStack to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:4566/_localstack/health | grep -q '"services"'; then
        echo "✅ LocalStack is ready!"
        break
    fi
    echo "   Attempt $i/30..."
    sleep 2
done

# Set LocalStack endpoint
export AWS_ENDPOINT_URL_EC2=http://localhost:4566
export AWS_ENDPOINT_URL_S3=http://localhost:4566
export AWS_ENDPOINT_URL_DYNAMODB=http://localhost:4566
export AWS_ENDPOINT_URL_LOGS=http://localhost:4566
export AWS_ENDPOINT_URL_SSM=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export LOCALSTACK_ENDPOINT=http://localhost:4566

# Create DynamoDB table
echo ""
echo "📊 Creating DynamoDB table..."
aws dynamodb create-table \
    --table-name aws-guardian-events \
    --attribute-definitions AttributeName=timestamp,AttributeType=S AttributeName=event_type,AttributeType=S \
    --key-schema AttributeName=timestamp,KeyType=HASH AttributeName=event_type,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --endpoint-url http://localhost:4566 \
    2>/dev/null || echo "   Table already exists"

# Create S3 buckets
echo "🪣 Creating test S3 buckets..."
aws s3 mb s3://test-bucket-1 --endpoint-url http://localhost:4566 2>/dev/null || echo "   Bucket test-bucket-1 already exists"
aws s3 mb s3://test-bucket-2 --endpoint-url http://localhost:4566 2>/dev/null || echo "   Bucket test-bucket-2 already exists"

# Create EC2 security group and instances (for testing)
echo "🔒 Creating test EC2 security group..."
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
    --group-name test-sg \
    --description "Test security group" \
    --endpoint-url http://localhost:4566 \
    --query 'GroupId' \
    --output text 2>/dev/null || echo "sg-existing")

echo "🖥️  Creating test EC2 instances..."
aws ec2 run-instances \
    --image-id ami-12345678 \
    --count 1 \
    --instance-type t2.micro \
    --security-group-ids $SECURITY_GROUP_ID \
    --endpoint-url http://localhost:4566 \
    2>/dev/null || echo "   Instances already created"

# Create SSM parameters
echo "⚙️  Creating SSM parameters..."
aws ssm put-parameter \
    --name /guardian/cost-threshold \
    --value 10.0 \
    --type String \
    --endpoint-url http://localhost:4566 \
    --overwrite 2>/dev/null || true

echo ""
echo "✨ LocalStack initialization complete!"
echo ""
echo "Environment variables set:"
echo "  LOCALSTACK_ENDPOINT=http://localhost:4566"
echo "  AWS_DEFAULT_REGION=us-east-1"
echo "  AWS_ACCESS_KEY_ID=test"
echo "  AWS_SECRET_ACCESS_KEY=test"
echo ""
echo "Ready to run tests with: python -m pytest tests/ -v"
