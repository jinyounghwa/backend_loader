# AWS Guardian v1.3 Deployment Guide

**Version:** 1.3.0-rc1  
**Date:** 2026-05-10  
**Features:** Redis Distributed Caching, aioboto3 Async Migration, Multi-Account Support

---

## Overview

AWS Guardian v1.3 introduces three major enhancements:
1. **Redis Distributed Caching** - Reduce API calls with distributed cache
2. **aioboto3 Async I/O** - 3x+ performance improvement with true async operations
3. **Multi-Account Support** - Monitor and control multiple AWS accounts from single Lambda

---

## Prerequisites

### AWS Services
- AWS Lambda (Python 3.12+)
- AWS EventBridge (for scheduling)
- AWS ElastiCache (for Redis) - *Optional*
- AWS Organizations (for multi-account) - *Optional*
- AWS DynamoDB (for state storage)
- AWS CloudWatch (for metrics)

### IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeRegions",
        "ec2:DescribeSecurityGroups",
        "s3:ListAllMyBuckets",
        "s3:GetBucketAcl",
        "s3:GetBucketPolicy",
        "s3:GetPublicAccessBlock",
        "ce:GetCostAndUsage",
        "cloudtrail:LookupEvents",
        "iam:ListUsers",
        "iam:ListAccessKeys",
        "guardduty:ListDetectors",
        "guardduty:ListFindings",
        "guardduty:GetFindings"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/guardian-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole"
      ],
      "Resource": "arn:aws:iam::*:role/GuardianCrossAccountRole"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/guardian*"
    }
  ]
}
```

### Cross-Account IAM Role (for multi-account support)

In each target AWS account, create role:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::MAIN_ACCOUNT_ID:role/lambda-guardian-role"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Role name: `GuardianCrossAccountRole`  
Permissions: Same as above

---

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/aws-guardian.git
cd aws-guardian
```

### 2. Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install lambda dependencies
pip install -r lambda/requirements.txt

# Install dev dependencies (for testing)
pip install pytest pytest-asyncio pytest-mock
```

### 3. Configure Environment Variables
```bash
# Cache configuration
export CACHE_BACKEND=redis              # or "memory" for in-memory only
export REDIS_URL=redis://elasticache-endpoint:6379/0

# Multi-account configuration (optional)
export AWS_ORGANIZATIONS_ENABLED=true
export AWS_CROSS_ACCOUNT_ROLE_NAME=GuardianCrossAccountRole

# Notification configuration
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id

# Check configuration
export COST_THRESHOLD=10.0              # Daily cost threshold in USD
export CLOUDTRAIL_LOOKBACK_HOURS=1      # CloudTrail events lookback
export GUARDDUTY_LOOKBACK_HOURS=24      # GuardDuty findings lookback
```

### 4. Deploy with SAM
```bash
# Build
sam build

# Deploy (interactive)
sam deploy --guided

# Deploy (non-interactive)
sam deploy \
  --parameter-overrides \
  ParameterKey=TelegramBotToken,ParameterValue=$TELEGRAM_BOT_TOKEN \
  ParameterKey=TelegramChatId,ParameterValue=$TELEGRAM_CHAT_ID
```

### 5. Deploy with Terraform (Alternative)
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

---

## Configuration

### Redis Cache Configuration

**Using AWS ElastiCache**
```bash
# Create ElastiCache cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id guardian-cache \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --port 6379

# Get endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id guardian-cache \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address'

# Configure
export CACHE_BACKEND=redis
export REDIS_URL=redis://guardian-cache.xxxxx.cache.amazonaws.com:6379/0
```

**Using In-Memory Cache (Development)**
```bash
export CACHE_BACKEND=memory
# No REDIS_URL needed - automatically falls back to in-memory
```

### Multi-Account Configuration

**Enable Organizations**
```bash
# Check if Organizations is enabled
aws organizations describe-organization

# Set environment variable
export AWS_ORGANIZATIONS_ENABLED=true

# List accounts
aws organizations list-accounts
```

**Create Cross-Account Role**
```bash
# In each target account:
aws iam create-role \
  --role-name GuardianCrossAccountRole \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name GuardianCrossAccountRole \
  --policy-arn arn:aws:iam::aws:policy/SecurityAudit
```

**trust-policy.json**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/lambda-guardian-role"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

---

## Testing

### Run Unit Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/guardian/ -v

# Run specific test file
pytest tests/guardian/test_cache.py -v

# Run with coverage
pytest tests/guardian/ --cov=lambda/guardian --cov-report=html
```

### Run Integration Tests (with LocalStack)
```bash
# Start LocalStack
docker-compose -f docker-compose.localstack.yml up -d

# Set LocalStack endpoint
export LOCALSTACK_ENDPOINT=http://localhost:4566
export AWS_ENDPOINT_URL=http://localhost:4566

# Run integration tests
pytest tests/guardian/test_integration_localstack.py -v

# Run performance tests
pytest tests/guardian/test_performance.py -v
```

### Manual Testing

**Test Single Check**
```python
import asyncio
from guardian.checkers.ec2 import EC2Checker

async def test():
    checker = EC2Checker({}, {"authorized_regions": ["us-east-1"]})
    result = await checker.check_async()
    print(f"Severity: {result.severity}")
    print(f"Message: {result.message}")

asyncio.run(test())
```

**Test Multi-Account**
```python
import asyncio
from guardian.orchestrator import GuardianOrchestrator
from guardian.storage.dynamodb import DynamoDBStorage
from guardian.checkers.ec2 import EC2Checker
import logging

logger = logging.getLogger()
storage = DynamoDBStorage()
checker = EC2Checker({}, {})

orchestrator = GuardianOrchestrator(
    logger=logger,
    cost_checker=None,
    ec2_checker=checker,
    s3_checker=None,
    storage=storage
)

result = orchestrator.run_all_checks({
    "check_type": "security",
    "time": "2026-05-10T00:00:00Z"
})

print(result)
```

---

## Monitoring & Operations

### CloudWatch Metrics
Guardian publishes metrics to CloudWatch:
- `Duration` - Check execution time (milliseconds)
- `EventsProcessed` - Number of events processed
- `ErrorCount` - Number of errors encountered

**View Metrics**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=guardian-checker \
  --start-time 2026-05-10T00:00:00Z \
  --end-time 2026-05-11T00:00:00Z \
  --period 3600 \
  --statistics Average,Maximum
```

### CloudWatch Logs
```bash
# View recent logs
aws logs tail /aws/lambda/guardian-checker --follow

# Filter errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/guardian-checker \
  --filter-pattern "ERROR"

# Get log statistics
aws logs describe-log-streams \
  --log-group-name /aws/lambda/guardian-checker \
  --query 'logStreams[0].{lastEvent:lastEventTimestamp,size:storedBytes}'
```

### Cache Monitoring

**Redis Cache Health**
```bash
# Connect to ElastiCache
redis-cli -h guardian-cache.xxxxx.cache.amazonaws.com -p 6379

# Check memory usage
INFO memory

# Check key count
DBSIZE

# Monitor operations
MONITOR

# Clear cache if needed
FLUSHDB
```

**Cache Hit Rate**
```python
# Enable cache statistics in code
from guardian.cache import get_cache_backend

cache = get_cache_backend()
# Cache keeps internal hit/miss statistics
```

---

## Troubleshooting

### Issue: Redis Connection Failure
**Symptom:** Cache operations fall back to in-memory  
**Solution:**
```bash
# Check ElastiCache cluster status
aws elasticache describe-cache-clusters \
  --cache-cluster-id guardian-cache \
  --query 'CacheClusters[0].CacheClusterStatus'

# Check security group
aws elasticache describe-cache-security-groups

# Test connection
redis-cli -h endpoint -p 6379 PING
```

### Issue: Async Checker Timeout
**Symptom:** Checker takes longer than expected  
**Solution:**
```bash
# Increase Lambda timeout
aws lambda update-function-configuration \
  --function-name guardian-checker \
  --timeout 300  # 5 minutes

# Check CloudWatch logs for bottlenecks
aws logs filter-log-events \
  --log-group-name /aws/lambda/guardian-checker \
  --filter-pattern "completed in"
```

### Issue: Cross-Account Role Assumption Fails
**Symptom:** Multi-account checks skip accounts  
**Solution:**
```bash
# Verify role exists in target account
aws iam get-role \
  --role-name GuardianCrossAccountRole \
  --profile target-account

# Test assume role
aws sts assume-role \
  --role-arn arn:aws:iam::TARGET_ACCOUNT:role/GuardianCrossAccountRole \
  --role-session-name test-guardian

# Check trust relationship
aws iam get-role \
  --role-name GuardianCrossAccountRole \
  --query 'Role.AssumeRolePolicyDocument'
```

### Issue: DynamoDB Throttling
**Symptom:** "ProvisionedThroughputExceededException"  
**Solution:**
```bash
# Increase DynamoDB capacity
aws dynamodb update-table \
  --table-name guardian-events \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10

# Or enable on-demand billing
aws dynamodb update-table \
  --table-name guardian-events \
  --billing-mode PAY_PER_REQUEST
```

---

## Performance Tuning

### Optimize Cache Backend
```python
# For high-throughput environments
cache = RedisCache(
    redis_url="redis://...",
    default_ttl=300,        # 5-minute cache
    max_connections=50
)

# For low-throughput or testing
cache = InMemoryCache(ttl_seconds=600)  # 10-minute cache
```

### Lambda Configuration
```bash
# Increase Lambda memory (faster CPU)
aws lambda update-function-configuration \
  --function-name guardian-checker \
  --memory-size 1024  # 1GB for better async performance

# Increase timeout
aws lambda update-function-configuration \
  --function-name guardian-checker \
  --timeout 300  # 5 minutes
```

### EventBridge Schedule
```bash
# Current: Every 1 hour
# For more frequent checks:
aws events put-rule \
  --name guardian-schedule \
  --schedule-expression "rate(30 minutes)"

# For less frequent checks:
aws events put-rule \
  --name guardian-schedule \
  --schedule-expression "rate(4 hours)"
```

---

## Rollback Procedures

### Rollback Lambda Function
```bash
# Get previous version
aws lambda list-versions-by-function \
  --function-name guardian-checker

# Deploy specific version
sam deploy \
  --parameter-overrides \
  LambdaCodeHash=sha256:previous_hash

# Or manually update
aws lambda update-function-code \
  --function-name guardian-checker \
  --s3-bucket deployment-bucket \
  --s3-key guardian-1.2.0.zip
```

### Rollback Cache Configuration
```bash
# Disable Redis, use in-memory
export CACHE_BACKEND=memory
unset REDIS_URL

# Update Lambda environment
aws lambda update-function-configuration \
  --function-name guardian-checker \
  --environment Variables="{CACHE_BACKEND=memory}"
```

### Disable Multi-Account
```bash
# Disable Organizations
export AWS_ORGANIZATIONS_ENABLED=false

# Update Lambda environment
aws lambda update-function-configuration \
  --function-name guardian-checker \
  --environment Variables="{AWS_ORGANIZATIONS_ENABLED=false}"
```

---

## Upgrade Path from v1.2 → v1.3

### Step 1: Backup Current Configuration
```bash
# Export Lambda environment
aws lambda get-function-configuration \
  --function-name guardian-checker > backup-v1.2.json

# Export DynamoDB data
aws dynamodb scan \
  --table-name guardian-events > backup-events.json
```

### Step 2: Deploy v1.3
```bash
# Build and deploy
sam build
sam deploy

# Or with Terraform
cd terraform
terraform plan
terraform apply
```

### Step 3: Enable New Features (Optional)
```bash
# Enable Redis caching
export CACHE_BACKEND=redis
export REDIS_URL=redis://new-elasticache-endpoint:6379/0

# Enable multi-account (if using Organizations)
export AWS_ORGANIZATIONS_ENABLED=true

# Update Lambda
aws lambda update-function-configuration \
  --function-name guardian-checker \
  --environment Variables="{CACHE_BACKEND=redis,REDIS_URL=...}"
```

### Step 4: Verify
```bash
# Test single check
aws lambda invoke \
  --function-name guardian-checker \
  --payload '{"check_type":"ec2"}' \
  response.json

cat response.json
```

---

## Maintenance Schedule

### Daily
- Monitor CloudWatch metrics
- Check error logs
- Verify cache hit rates

### Weekly
- Review CloudTrail findings
- Validate multi-account checks
- Performance analysis

### Monthly
- Clean up old DynamoDB records
- Update security rules
- Review cost trends

### Quarterly
- Update dependencies
- Security patch review
- Performance benchmark

---

## Support & Documentation

- **GitHub Issues:** Report bugs and feature requests
- **Email:** guardian-team@example.com
- **Wiki:** https://github.com/yourorg/aws-guardian/wiki
- **Docs:** https://aws-guardian.readthedocs.io

---

## License

See LICENSE file in repository.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.3.0 | 2026-05-10 | Redis caching, aioboto3 async, multi-account support |
| 1.2.0 | 2026-04-15 | Performance optimization, caching layer |
| 1.1.0 | 2026-03-20 | Initial release with 6 security checkers |

