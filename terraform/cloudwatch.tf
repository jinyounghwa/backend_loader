# CloudWatch Dashboard for AWS Guardian Performance Monitoring
# Displays Lambda execution metrics, DynamoDB queries, and Gemini API latency

resource "aws_cloudwatch_dashboard" "guardian_performance" {
  dashboard_name = "aws-guardian-performance"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["aws-guardian", "Duration", { stat = "Average", label = "Avg Execution Time" }],
            [".", ".", { stat = "Maximum", label = "Max Execution Time" }],
            [".", "ColdStartDuration", { stat = "Average", label = "Avg Cold Start" }],
            [".", "DynamoDBQueryTime", { stat = "Average", label = "Avg DynamoDB Query" }],
            [".", "GeminiAPILatency", { stat = "Average", label = "Avg Gemini API" }],
          ]
          period       = 300
          stat         = "Average"
          region       = var.aws_region
          title        = "Lambda Performance Metrics"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
        width  = 12
        height = 6
        x      = 0
        y      = 0
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["aws-guardian", "MemoryUsed", { stat = "Average" }],
            [".", ".", { stat = "Maximum" }],
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Memory Usage"
          yAxis = {
            left = {
              min = 0
              max = 512
            }
          }
        }
        width  = 12
        height = 6
        x      = 12
        y      = 0
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["aws-guardian", "EventsProcessed", { stat = "Sum" }],
            [".", "ErrorCount", { stat = "Sum" }],
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Events and Errors"
        }
        width  = 12
        height = 6
        x      = 0
        y      = 6
      },
      {
        type = "log"
        properties = {
          query = "fields @timestamp, @duration, @memoryUsed | stats avg(@duration) as avgDuration, max(@memoryUsed) as maxMemory"
          region = var.aws_region
          title  = "CloudWatch Logs Summary"
        }
        width  = 12
        height = 6
        x      = 12
        y      = 6
      }
    ]
  })
}

# CloudWatch Alarms for error detection and performance degradation

resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  alarm_name          = "aws-guardian-error-rate-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ErrorCount"
  namespace           = "aws-guardian"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when AWS Guardian Lambda error count exceeds 5 in 1 minute"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration_high" {
  alarm_name          = "aws-guardian-execution-time-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "aws-guardian"
  period              = 60
  statistic           = "Average"
  threshold           = 30000  # 30 seconds
  alarm_description   = "Alert when average Lambda execution time exceeds 30 seconds"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
}

resource "aws_cloudwatch_metric_alarm" "lambda_memory_high" {
  alarm_name          = "aws-guardian-memory-usage-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUsed"
  namespace           = "aws-guardian"
  period              = 300
  statistic           = "Average"
  threshold           = 400
  alarm_description   = "Alert when average memory usage exceeds 400MB"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []
}
