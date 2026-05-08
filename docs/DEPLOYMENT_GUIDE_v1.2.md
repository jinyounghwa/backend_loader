# AWS Guardian v1.2 Deployment Guide

**Last Updated**: May 8, 2026  
**Version**: v1.2  
**Status**: Production Ready  
**Environment**: AWS Lambda + EventBridge + DynamoDB

---

## Table of Contents

1. [Pre-Deployment](#pre-deployment)
2. [Deployment Methods](#deployment-methods)
3. [Verification](#verification)
4. [Rollback Procedure](#rollback-procedure)
5. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment

### Prerequisites

**AWS Account Requirements**:
- [ ] AWS Account with appropriate IAM permissions
- [ ] AWS CLI configured (v2.x or later)
- [ ] AWS SAM CLI installed (`sam --version`)
- [ ] Terraform 1.0+ (for IaC deployment)

**Local Environment**:
- [ ] Python 3.12 installed
- [ ] pip package manager available
- [ ] Docker running (for LocalStack testing)
- [ ] Git configured (for version control)

**External Services**:
- [ ] Telegram bot token configured
- [ ] Discord webhook URL configured
- [ ] AWS Cost Explorer API enabled
- [ ] CloudTrail enabled in AWS account

### Configuration Checklist

Before deployment, gather these values:

```bash
# 1. AWS Account Info
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"

# 2. Telegram Bot Token
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

# 3. Discord Webhook URL
export DISCORD_WEBHOOK_URL="https://discordapp.com/api/webhooks/..."

# 4. Email for alerts
export ALERT_EMAIL="your-email@example.com"

# 5. Budget threshold (dollars per day)
export BUDGET_THRESHOLD="10.00"

# 6. S3 bucket for CloudFormation templates
export S3_BUCKET="guardian-deployment-$(date +%s)"
```

### Environment Variables Setup

Create `.env` file in project root:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Monitoring Configuration
TELEGRAM_BOT_TOKEN=<your_token>
DISCORD_WEBHOOK_URL=<your_webhook>
ALERT_EMAIL=<your_email>
BUDGET_THRESHOLD=10.00

# Lambda Configuration
LAMBDA_MEMORY=512
LAMBDA_TIMEOUT=60
LAMBDA_RESERVED_CONCURRENCY=5

# DynamoDB Configuration
DYNAMODB_BILLING_MODE=PAY_PER_REQUEST
DYNAMODB_POINT_IN_TIME_RECOVERY=true

# CloudWatch Configuration
LOG_RETENTION_DAYS=30
METRIC_NAMESPACE=AwsGuardian
```

---

## Deployment Methods

### Method 1: AWS SAM (Recommended for Quick Deployment)

**Best for**: Development, testing, small-scale deployments

**Step 1: Build**
```bash
cd lambda
sam build --use-container
```

**Step 2: Deploy**
```bash
sam deploy --guided \
  --stack-name guardian-stack \
  --s3-prefix guardian-v1.2 \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM
```

**Step 3: Answer Prompts**
```
Stack Name [aws-guardian]: guardian-stack
Region [us-east-1]: us-east-1
Confirm changes before deploy [y/N]: y
Allow SAM CLI IAM role creation [Y/n]: y
Save parameters to samconfig.toml [Y/n]: y
```

**Expected Output**:
```
Successfully created/updated stack - guardian-stack in us-east-1
```

### Method 2: Terraform (Recommended for Production)

**Best for**: Infrastructure-as-code, enterprise deployments, version control

**Step 1: Initialize**
```bash
cd terraform
terraform init \
  -backend-config="bucket=$BUCKET" \
  -backend-config="key=guardian/terraform.tfstate" \
  -backend-config="region=us-east-1"
```

**Step 2: Plan**
```bash
terraform plan \
  -var="aws_region=us-east-1" \
  -var="telegram_bot_token=$TELEGRAM_BOT_TOKEN" \
  -var="discord_webhook_url=$DISCORD_WEBHOOK_URL" \
  -out=tfplan
```

**Step 3: Apply**
```bash
terraform apply tfplan
```

**Step 4: Save State**
```bash
# State automatically saved to S3
# Backup locally
terraform state pull > terraform.state.backup
```

### Method 3: Docker Compose (Development/Testing)

**Best for**: Local testing, development environment

**Step 1: Start Services**
```bash
docker-compose -f docker-compose.production.yml up -d
```

**Step 2: Deploy Stack**
```bash
# CloudFormation via LocalStack
aws cloudformation create-stack \
  --endpoint-url http://localhost:4566 \
  --stack-name guardian-local \
  --template-body file://lambda/template.yaml
```

**Step 3: Verify**
```bash
docker-compose logs -f guardian-lambda
```

---

## Verification

### Immediate Checks (Post-Deployment)

**Check 1: Lambda Function Created**
```bash
aws lambda get-function-configuration \
  --function-name guardian-checker \
  --region us-east-1
```

Expected output includes:
- FunctionName: `guardian-checker`
- Runtime: `python3.12`
- MemorySize: `512`
- Timeout: `60`
- Handler: `handler.main`

**Check 2: EventBridge Rule Active**
```bash
aws events describe-rule \
  --name guardian-schedule \
  --region us-east-1
```

Expected output:
- State: `ENABLED`
- ScheduleExpression: `rate(1 hour)`

**Check 3: DynamoDB Tables Created**
```bash
aws dynamodb list-tables --region us-east-1
```

Expected tables:
- `guardian-events`
- `guardian-remediation-metrics`
- `guardian-audit-logs`
- `guardian-response-rules`

**Check 4: Lambda Permissions**
```bash
aws lambda get-policy \
  --function-name guardian-checker \
  --region us-east-1
```

Should include EventBridge as principal.

### Functional Tests

**Test 1: Invoke Lambda Manually**
```bash
# Test cost checker
aws lambda invoke \
  --function-name guardian-checker \
  --payload '{"check_type": "cost"}' \
  --log-type Tail \
  response.json

cat response.json
```

Expected response:
```json
{
  "statusCode": 200,
  "body": {
    "status": "success",
    "checks_run": 1,
    "alerts_sent": 0
  }
}
```

**Test 2: Security Checker**
```bash
aws lambda invoke \
  --function-name guardian-checker \
  --payload '{"check_type": "security"}' \
  --log-type Tail \
  response.json

cat response.json
```

**Test 3: All Checks**
```bash
aws lambda invoke \
  --function-name guardian-checker \
  --payload '{"check_type": "all"}' \
  --log-type Tail \
  response.json

cat response.json
```

### Integration Tests

**Test 4: Telegram Notification**
```bash
# Send test message to Telegram bot
python3 -c "
import json
import boto3
import os

lambda_client = boto3.client('lambda')
payload = {
    'test_mode': True,
    'check_type': 'all'
}

response = lambda_client.invoke(
    FunctionName='guardian-checker',
    Payload=json.dumps(payload)
)

print('Lambda Response:', response)
"
```

Check Telegram for test notification.

**Test 5: Discord Webhook**
```bash
# Check Discord webhook is working
curl -X POST $DISCORD_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"content":"AWS Guardian v1.2 deployment successful!"}'
```

**Test 6: CloudWatch Metrics**
```bash
# View metrics in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AwsGuardian \
  --metric-name ChecksRun \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### Performance Validation

**Test 7: Execution Time**
```bash
# Run 3x to get avg warm invocation
for i in {1..3}; do
  echo "Invocation $i:"
  time aws lambda invoke \
    --function-name guardian-checker \
    --payload '{"check_type": "all"}' \
    response-$i.json
done
```

Expected: ~300-500ms warm invocation time

**Test 8: Multi-Region Performance**
```bash
# Test with 4 regions
aws lambda invoke \
  --function-name guardian-checker \
  --payload '{
    "check_type": "security",
    "regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"]
  }' \
  response-regions.json

cat response-regions.json
```

Expected: ~3000-4000ms for 4 parallel regions

### Full Verification Checklist

- [ ] Lambda function deployed and callable
- [ ] EventBridge rule triggering on schedule
- [ ] DynamoDB tables created and accessible
- [ ] Lambda has proper IAM permissions
- [ ] Telegram notifications working
- [ ] Discord webhook working
- [ ] CloudWatch logs being generated
- [ ] Metrics being published
- [ ] No errors in Lambda logs
- [ ] Cold start < 2500ms
- [ ] Warm invocation < 500ms
- [ ] Multi-region < 5000ms

---

## Rollback Procedure

### Rollback from v1.1 to v1.0 (if needed)

**Step 1: Stop Current Stack**
```bash
# SAM
sam delete --stack-name guardian-stack --region us-east-1

# Terraform
terraform destroy -auto-approve
```

**Step 2: Restore Previous Lambda Code**
```bash
# Restore from backup
aws s3 cp s3://guardian-backup/lambda-v1.1.zip ./lambda-v1.1.zip

# Update Lambda function
aws lambda update-function-code \
  --function-name guardian-checker \
  --s3-bucket guardian-backup \
  --s3-key lambda-v1.1.zip

# Wait for update
aws lambda wait function-updated \
  --function-name guardian-checker
```

**Step 3: Verify**
```bash
# Check function version
aws lambda get-function-configuration \
  --function-name guardian-checker

# Invoke test
aws lambda invoke \
  --function-name guardian-checker \
  --payload '{"check_type": "cost"}' \
  response.json
```

### Database Rollback

**If DynamoDB data corruption occurs**:

```bash
# Create backup of corrupted data
aws dynamodb create-backup \
  --table-name guardian-events \
  --backup-name guardian-events-rollback-$(date +%s)

# Restore from previous backup
aws dynamodb restore-table-from-backup \
  --target-table-name guardian-events-restored \
  --backup-arn arn:aws:dynamodb:...

# Verify restored data
aws dynamodb scan \
  --table-name guardian-events-restored \
  --limit 10
```

---

## Troubleshooting

### Problem 1: Lambda Timeout

**Symptoms**: Invocation timeout after 60 seconds

**Solution**:
```bash
# Increase timeout
aws lambda update-function-configuration \
  --function-name guardian-checker \
  --timeout 120

# Investigate slow checks
aws logs tail /aws/lambda/guardian-checker --follow
```

### Problem 2: Telegram Bot Not Responding

**Symptoms**: Lambda executes but Telegram messages not received

**Solution**:
```bash
# Verify token
curl -s https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe | jq

# Check Lambda logs
aws logs tail /aws/lambda/guardian-checker --follow | grep -i telegram

# Test Telegram API directly
python3 -c "
import requests
token = '${TELEGRAM_BOT_TOKEN}'
chat_id = 'YOUR_CHAT_ID'
url = f'https://api.telegram.org/bot{token}/sendMessage'
requests.post(url, json={'chat_id': chat_id, 'text': 'Test'})
"
```

### Problem 3: DynamoDB Throttling

**Symptoms**: `ProvisionedThroughputExceededException`

**Solution**:
```bash
# For on-demand billing (recommended)
aws dynamodb update-billing-mode \
  --table-name guardian-events \
  --billing-mode PAY_PER_REQUEST

# For provisioned (if preferred)
aws dynamodb update-table \
  --table-name guardian-events \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=5
```

### Problem 4: Permission Denied Errors

**Symptoms**: `AccessDeniedException` in logs

**Solution**:
```bash
# Check Lambda execution role
aws lambda get-function \
  --function-name guardian-checker \
  --query 'Configuration.Role' | xargs -I {} \
  aws iam get-role --role-name {}

# Attach missing policies
aws iam attach-role-policy \
  --role-name guardian-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

# Verify EC2/S3 permissions
aws iam put-role-policy \
  --role-name guardian-lambda-role \
  --policy-name guardian-ec2-s3-policy \
  --policy-document file://policies/ec2-s3-policy.json
```

### Problem 5: LocalStack Connection Issues

**Symptoms**: "Could not connect to endpoint" errors

**Solution**:
```bash
# Verify LocalStack is running
docker-compose ps

# Check endpoint
netstat -an | grep 4566

# Restart LocalStack
docker-compose down
docker-compose up -d
docker-compose logs localstack
```

---

## Post-Deployment

### Monitoring Setup

**CloudWatch Dashboard**:
```bash
# Create custom dashboard
aws cloudwatch put-dashboard \
  --dashboard-name GuardianMonitoring \
  --dashboard-body file://dashboards/guardian-dashboard.json
```

**Alarms**:
```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name guardian-high-errors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

### Scheduled Reports

**Weekly Status Report**:
```bash
# Generate report from DynamoDB
python3 scripts/generate_weekly_report.py \
  --table guardian-events \
  --output report.html
```

### Backup Strategy

**Automatic Backups**:
```bash
# Enable point-in-time recovery for DynamoDB
aws dynamodb update-continuous-backups \
  --table-name guardian-events \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

---

## Support

For issues or questions:

1. **Check logs**: `aws logs tail /aws/lambda/guardian-checker --follow`
2. **Review documentation**: See `docs/` directory
3. **Test locally**: Use Docker Compose for isolated testing
4. **Check status**: Visit GitHub issues for known problems

---

**Deployment Guide Complete**

Version: v1.2  
Last Updated: 2026-05-08  
Status: Production Ready
