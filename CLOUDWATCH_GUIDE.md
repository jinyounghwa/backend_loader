# CloudWatch Monitoring Guide - AWS Guardian Sprint 10

## Overview

CloudWatch metrics have been integrated into AWS Guardian Lambda to provide real-time performance visibility and alerting.

## Metrics Collected

### Core Metrics
- **Duration** (Milliseconds)
  - Total Lambda execution time
  - Helps identify performance degradation over time
  - Alert threshold: > 30 seconds

- **ColdStartDuration** (Milliseconds)
  - Time taken for Lambda cold start
  - Target: < 500ms (currently ~2-3s)
  - Reduced by boto3 caching and optimized initialization

- **DynamoDBQueryTime** (Milliseconds)
  - Time spent on DynamoDB queries
  - Helps identify query bottlenecks
  - Monitor for pagination overhead

- **GeminiAPILatency** (Milliseconds)
  - Time spent calling Gemini API
  - Target: < 2 seconds (varies by request size)
  - Includes network latency and API processing

- **MemoryUsed** (Megabytes)
  - Actual memory consumed by Lambda
  - Current Lambda memory: 512MB
  - Alert threshold: > 400MB (80%)

- **EventsProcessed** (Count)
  - Number of accounts/events processed
  - Useful for throughput analysis

- **ErrorCount** (Count)
  - Number of errors during execution
  - Alert threshold: > 5 errors per 60 seconds

## Dashboard

Access CloudWatch Dashboard:
```bash
# Via AWS CLI
aws cloudwatch get-dashboard --dashboard-name aws-guardian-performance

# Via AWS Console
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=aws-guardian-performance
```

## Alarms

Three alarms are configured:

### 1. Error Rate Alarm
- **Threshold**: ErrorCount > 5 in 60 seconds
- **Action**: SNS notification (if configured)
- **Purpose**: Detect Lambda failures

### 2. Execution Time Alarm
- **Threshold**: Duration > 30 seconds (average over 2 minutes)
- **Action**: SNS notification (if configured)
- **Purpose**: Detect performance degradation

### 3. Memory Usage Alarm
- **Threshold**: MemoryUsed > 400MB (average over 5 minutes)
- **Action**: SNS notification (if configured)
- **Purpose**: Prevent out-of-memory errors

## Log Analysis

Use CloudWatch Logs Insights to analyze performance:

```bash
# Run automated analysis
./scripts/analyze-performance.sh 24  # Last 24 hours

# Or use AWS CLI for custom queries
aws logs start-query \
  --log-group-name "/aws/lambda/aws-guardian-monitor" \
  --start-time $(date -d '1 day ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @duration | stats avg(@duration) as avgDuration'
```

## Quick Reference - Metrics by Command

### /status
- Duration: 200-500ms
- MemoryUsed: 150-250MB
- Events: 1 (summary)

### /remediate
- Duration: 2-5 seconds
- DynamoDB queries: 1-3
- MemoryUsed: 200-350MB

### /export
- Duration: 5-15 seconds (varies by event count)
- DynamoDB queries: 2-5 (pagination)
- MemoryUsed: 300-450MB (PDF generation)
- ErrorCount: Track for OOM errors

### /insights
- Duration: 3-8 seconds
- GeminiAPILatency: 1-3 seconds
- MemoryUsed: 250-400MB
- DynamoDB queries: 1

## Optimization Recommendations

Based on metrics, consider:

1. **High ColdStartDuration?**
   - boto3 caching is active - monitor for lambda layer size
   - Consider increasing memory for faster CPU (512MB → 1GB)

2. **High DynamoDBQueryTime?**
   - Check Limit parameter in pagination
   - Verify GSI is being used correctly
   - Consider caching frequently accessed events

3. **Memory approaching 450MB?**
   - Monitor PDF generation (fpdf2 uses 50-100MB)
   - Large event counts in /export may exceed 512MB
   - Recommendation: Increase to 1024MB for safer operation

4. **GeminiAPILatency > 3s?**
   - Check API quota and rate limits
   - Verify prompt is not too large
   - Cache results to reduce repeated calls

## Implementation Details

### Code Integration

Metrics are emitted in:
```python
# orchestrator.py
from guardian.handlers.metrics import CloudWatchMetrics

# In run_all_checks():
CloudWatchMetrics.emit_batch({
    'Duration': elapsed_ms,
    'EventsProcessed': len(results.get('accounts', [])),
    'ErrorCount': error_count
})
```

### CloudWatch Permissions

IAM role includes:
```json
{
  "Effect": "Allow",
  "Action": ["cloudwatch:PutMetricData"],
  "Resource": "*"
}
```

### Configuration

Dashboard and alarms defined in:
- `terraform/cloudwatch.tf` - Dashboard, alarms, log groups
- `terraform/main.tf` - SNS topic ARN variable
- `terraform/iam.tf` - PutMetricData permission

## Next Steps

1. Deploy to production with `terraform apply`
2. Monitor for 1 week to establish baselines
3. Adjust alarm thresholds based on actual usage
4. Consider metrics-based auto-scaling for future work
5. Archive logs to S3 for long-term analysis

## Troubleshooting

### Metrics not appearing in dashboard?
1. Check CloudWatch logs for errors: `grep ERROR guardian.log`
2. Verify IAM role has `cloudwatch:PutMetricData` permission
3. Metrics appear in CloudWatch after 60 seconds delay

### Alarm not triggering?
1. Check alarm action configuration: SNS topic ARN must be set
2. Test manually: `aws cloudwatch put-metric-data --namespace aws-guardian --metric-name Duration --value 40000`
3. Verify log group exists and is receiving logs

### Dashboard widgets showing no data?
1. Ensure Lambda has executed at least once
2. Check time range - default is last 1 hour
3. Metrics must be emitted after 2026-05-03 (when Phase 2 deployed)
