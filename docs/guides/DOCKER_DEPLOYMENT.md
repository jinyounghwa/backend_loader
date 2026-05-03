# AWS Guardian - Docker Deployment Guide

> Production-ready Docker Compose configuration for AWS Guardian monitoring system

---

## 📋 Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Production Deployment](#production-deployment)
3. [Environment Variables](#environment-variables)
4. [Security Best Practices](#security-best-practices)
5. [Monitoring & Logging](#monitoring--logging)
6. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- Python 3.12+
- Git

### Step 1: Clone and Setup

```bash
git clone <repository>
cd aws-guardian
cp .env.example .env
```

### Step 2: Configure .env

Edit `.env` with your development credentials:

```bash
# Telegram (optional for testing)
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id

# Discord (optional for testing)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_BOT_TOKEN=your_token

# Cost Threshold
COST_THRESHOLD=10.0
```

### Step 3: Start LocalStack

```bash
docker-compose up -d
```

Verify LocalStack is running:

```bash
docker-compose ps
# Expected: localstack service is "Up"

# Check health
curl http://localhost:4566/_localstack/health
```

### Step 4: Initialize LocalStack Resources

```bash
python scripts/init_localstack.py
```

This will create:
- DynamoDB `guardian_events` table
- S3 buckets for testing
- IAM roles and policies
- CloudWatch Logs streams

### Step 5: Run Local Tests

```bash
./start.sh
```

Verify in logs:
```bash
tail -f guardian.log
```

Expected output:
```
[INFO] AWS Guardian orchestration started
[INFO] Checking AWS costs...
[INFO] Checking EC2 instances...
[INFO] Checking S3 buckets...
[INFO] AWS Guardian orchestration completed
```

---

## Production Deployment

### Architecture

```
┌─────────────────────┐
│   AWS Lambda        │
│  (aws-guardian)     │
└──────────┬──────────┘
           │ (hourly trigger)
           ▼
┌─────────────────────┐
│   EventBridge       │
│  (cron: 0 * * * ?)  │
└─────────────────────┘
           │
           ▼
┌──────────────────────┐
│   EC2/S3/Cost        │
│   Monitoring         │
└──────────┬───────────┘
           │
           ├──► Telegram (alerts)
           ├──► Discord (dashboard)
           └──► DynamoDB (events)
```

### Step 1: Prerequisites

- AWS Account with appropriate IAM permissions
- Terraform 1.0+
- AWS CLI configured

### Step 2: Secrets Setup

Store production credentials in AWS Secrets Manager:

```bash
# Telegram Bot Token
aws secretsmanager create-secret \
  --name aws-guardian/telegram-bot-token \
  --secret-string "your-token-here"

# Discord Webhook
aws secretsmanager create-secret \
  --name aws-guardian/discord-webhook \
  --secret-string "https://discord.com/api/webhooks/..."
```

### Step 3: Terraform Deployment

```bash
cd terraform

# Set production environment
export AWS_REGION=us-east-1
export AWS_ENV=production

# Initialize and validate
terraform init
terraform plan

# Deploy
terraform apply
```

### Step 4: Deploy Lambda Function

```bash
cd ../scripts
./deploy.sh --env production
```

### Step 5: Verify Deployment

```bash
# Check Lambda function
aws lambda get-function-configuration \
  --function-name aws-guardian

# Monitor CloudWatch Logs
aws logs tail /aws/lambda/aws-guardian --follow
```

---

## Environment Variables

### Development (.env)

| Variable | Purpose | Default |
|----------|---------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | Test credentials | `test` |
| `AWS_SECRET_ACCESS_KEY` | Test credentials | `test` |
| `LOCALSTACK_ENDPOINT` | LocalStack URL | `http://localhost:4566` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | _(required for alerts)_ |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | _(required for alerts)_ |
| `DISCORD_WEBHOOK_URL` | Discord webhook | _(required for alerts)_ |
| `COST_THRESHOLD` | Cost alert threshold (USD/day) | `10.0` |
| `DEBUG` | Enable debug logging | `1` |

### Production (.env.production)

| Variable | Purpose | Source |
|----------|---------|--------|
| `AWS_REGION` | AWS region | Environment |
| `AWS_ACCESS_KEY_ID` | AWS credentials | AWS Secrets Manager |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | AWS Secrets Manager |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | AWS Secrets Manager |
| `DISCORD_WEBHOOK_URL` | Discord webhook | AWS Secrets Manager |
| `COST_THRESHOLD` | Cost alert threshold | Parameter Store |
| `DEBUG` | Debug logging | `0` |
| `ENABLE_CLOUDWATCH` | CloudWatch integration | `true` |

---

## Security Best Practices

### ✅ DO

1. **Use IAM Roles** instead of hardcoded credentials
   ```bash
   # Lambda: Attach execution role
   # EC2: Use instance profile
   # ECS: Use task role
   ```

2. **Store Secrets in AWS Secrets Manager**
   ```bash
   aws secretsmanager get-secret-value \
     --secret-id aws-guardian/telegram-bot-token
   ```

3. **Enable CloudWatch Monitoring**
   - Set retention period: 7 days
   - Create alarms for failures
   - Enable X-Ray tracing

4. **Use VPC Endpoints** (if in VPC)
   - S3 gateway endpoint
   - DynamoDB gateway endpoint

5. **Enable DynamoDB Encryption**
   ```bash
   # Enable server-side encryption
   aws dynamodb update-table \
     --table-name guardian_events \
     --sse-specification Enabled=true
   ```

### ❌ DON'T

1. ❌ Hardcode credentials in code or docker-compose
2. ❌ Use `DEBUG=1` in production
3. ❌ Expose ports to the internet (use VPC)
4. ❌ Commit `.env` or secrets files to git
5. ❌ Use LocalStack in production
6. ❌ Allow public DynamoDB access

### 🔒 Network Security

```yaml
# Local Development: Localhost only
ports:
  - "127.0.0.1:4566:4566"  # ✅ Good

# Production: Use VPC
# ❌ Don't expose ports
# ports:
#   - "4566:4566"
```

---

## Monitoring & Logging

### CloudWatch Logs

CloudWatch automatically captures:
- Lambda execution logs
- DynamoDB API calls
- S3 access logs
- Cost anomalies

View logs:
```bash
aws logs tail /aws/lambda/aws-guardian --follow
```

### Alarms

Set up alarms for:

1. **Lambda Errors**
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name aws-guardian-errors \
     --alarm-description "Alert on Lambda errors" \
     --metric-name Errors \
     --namespace AWS/Lambda \
     --threshold 1 \
     --comparison-operator GreaterThanOrEqualToThreshold
   ```

2. **High Costs**
   - Telegram notification configured
   - Cost threshold: $100/day (production)

3. **Missing Checks**
   - If no check result in 2 hours
   - Enable SNS notification

### DynamoDB Monitoring

```bash
# Check table metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=guardian_events \
  --start-time 2026-04-27T00:00:00Z \
  --end-time 2026-04-27T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

---

## Troubleshooting

### LocalStack Not Starting

```bash
# Check Docker daemon
docker ps

# Check LocalStack logs
docker logs aws-guardian-localstack

# Verify Docker socket
ls -la /var/run/docker.sock
```

### Lambda Function Not Triggered

```bash
# Check EventBridge rule
aws events list-rules --name-prefix aws-guardian

# Check Lambda permissions
aws lambda get-policy \
  --function-name aws-guardian \
  --query Policy
```

### DynamoDB Write Errors

```bash
# Check table status
aws dynamodb describe-table \
  --table-name guardian_events \
  --query 'Table.TableStatus'

# Check write capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=guardian_events \
  --start-time 2026-04-27T00:00:00Z \
  --end-time 2026-04-27T23:59:59Z \
  --period 60 \
  --statistics Sum
```

### Telegram Bot Not Sending Alerts

```bash
# Check token validity
curl https://api.telegram.org/bot<TOKEN>/getMe

# Check chat ID
curl https://api.telegram.org/bot<TOKEN>/getChat?chat_id=<CHAT_ID>

# View Lambda logs
aws logs tail /aws/lambda/aws-guardian --follow | grep telegram
```

---

## Cost Estimation (Production)

| Service | Monthly Cost | Note |
|---------|--------------|------|
| Lambda | ~$0.20 | 720 invocations + 1GB-second compute |
| DynamoDB | ~$0.25 | <100KB stored data (free tier) |
| CloudWatch | ~$0.50 | Logs + basic monitoring |
| Secrets Manager | ~$0.40 | 1 secret stored |
| **Total** | **~$1.35** | Within AWS free tier |

---

## Next Steps

- [ ] Set up Telegram bot notifications
- [ ] Configure Discord webhook
- [ ] Test production deployment
- [ ] Set up CloudWatch alarms
- [ ] Document runbook for incidents
- [ ] Schedule regular security audits

---

## References

- [LocalStack Documentation](https://docs.localstack.cloud/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/lambda-best-practices.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
