#!/bin/bash

# CloudWatch Logs Insights Analysis Helper
# Analyzes AWS Guardian Lambda performance using CloudWatch Logs Insights queries

LOG_GROUP="/aws/lambda/aws-guardian-monitor"
PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-us-east-1}"

# Determine hours parameter (default 24 hours)
HOURS=${1:-24}
SINCE="$((HOURS))h"

echo "📊 AWS Guardian Performance Analysis"
echo "📅 Time range: Last $HOURS hours"
echo "📍 Log group: $LOG_GROUP"
echo ""

# Query 1: Cold Start Analysis
echo "❄️  COLD START ANALYSIS"
echo "===================="
echo "Finding cold starts (Lambda init duration > 0)..."
aws logs start-query \
  --log-group-name "$LOG_GROUP" \
  --start-time "$(date -d "$HOURS hours ago" +%s)" \
  --end-time "$(date +%s)" \
  --query-string 'fields @timestamp, @duration, @initDuration | filter @initDuration > 0 | stats count() as coldStarts, avg(@initDuration) as avgColdStart, max(@initDuration) as maxColdStart' \
  --region "$REGION" \
  --profile "$PROFILE" \
  --output table
echo ""

# Query 2: Execution Time Distribution
echo "⏱️  EXECUTION TIME DISTRIBUTION"
echo "=============================="
echo "Analyzing Lambda execution time percentiles..."
aws logs start-query \
  --log-group-name "$LOG_GROUP" \
  --start-time "$(date -d "$HOURS hours ago" +%s)" \
  --end-time "$(date +%s)" \
  --query-string 'fields @duration | stats avg(@duration) as avgDuration, max(@duration) as maxDuration, pct(@duration, 50) as p50, pct(@duration, 90) as p90, pct(@duration, 99) as p99' \
  --region "$REGION" \
  --profile "$PROFILE" \
  --output table
echo ""

# Query 3: Slow Requests
echo "🐌 SLOW REQUESTS (>30 seconds)"
echo "=============================="
echo "Finding requests slower than 30 seconds..."
aws logs start-query \
  --log-group-name "$LOG_GROUP" \
  --start-time "$(date -d "$HOURS hours ago" +%s)" \
  --end-time "$(date +%s)" \
  --query-string 'fields @timestamp, @duration, @message | filter @duration > 30000 | stats count() as slowRequests by @message' \
  --region "$REGION" \
  --profile "$PROFILE" \
  --output table
echo ""

# Query 4: Memory Usage
echo "💾 MEMORY USAGE ANALYSIS"
echo "======================="
echo "Analyzing Lambda memory utilization..."
aws logs start-query \
  --log-group-name "$LOG_GROUP" \
  --start-time "$(date -d "$HOURS hours ago" +%s)" \
  --end-time "$(date +%s)" \
  --query-string 'fields @memoryUsed, @memorySize | stats avg(@memoryUsed/@memorySize*100) as avgMemoryPct, max(@memoryUsed/@memorySize*100) as maxMemoryPct, avg(@memoryUsed) as avgMemory, max(@memoryUsed) as maxMemory' \
  --region "$REGION" \
  --profile "$PROFILE" \
  --output table
echo ""

# Query 5: Error Analysis
echo "⚠️  ERROR ANALYSIS"
echo "================="
echo "Finding Lambda errors..."
aws logs start-query \
  --log-group-name "$LOG_GROUP" \
  --start-time "$(date -d "$HOURS hours ago" +%s)" \
  --end-time "$(date +%s)" \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | stats count() as errorCount by @message' \
  --region "$REGION" \
  --profile "$PROFILE" \
  --output table
echo ""

# Query 6: DynamoDB Query Performance
echo "🔄 DYNAMODB QUERY PERFORMANCE"
echo "============================="
echo "Analyzing DynamoDB query times..."
aws logs start-query \
  --log-group-name "$LOG_GROUP" \
  --start-time "$(date -d "$HOURS hours ago" +%s)" \
  --end-time "$(date +%s)" \
  --query-string 'fields @message | filter @message like /DynamoDB/ | stats count() as queryCount, avg(tonumber(word(@message, 4))) as avgTime' \
  --region "$REGION" \
  --profile "$PROFILE" \
  --output table
echo ""

echo "✅ Analysis complete!"
echo ""
echo "💡 Next steps:"
echo "  1. Review slow requests - identify bottlenecks"
echo "  2. Monitor memory usage - consider increasing Lambda memory if > 90%"
echo "  3. Analyze cold starts - optimize initialization"
echo "  4. Check DynamoDB performance - consider Limit parameter adjustment"
