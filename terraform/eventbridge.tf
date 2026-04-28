# ============================================================================
# EventBridge Rules for AWS Guardian Monitoring
# ============================================================================
# Split strategy to optimize Cost Explorer API costs:
# - Hourly Rule: EC2 + S3 security checks only (no cost check)
# - Daily Rule: Cost Explorer check only
#
# Cost Impact:
# - Cost Explorer at hourly rate: $0.01 × 730 calls/month = $7.30/month ❌
# - Cost Explorer at daily rate: $0.01 × 30 calls/month = $0.30/month ✅
# - Savings: $7.00/month toward $0.50/month target

# ============================================================================
# Rule 1: Hourly EC2 + S3 Security Monitoring
# ============================================================================
resource "aws_cloudwatch_event_rule" "hourly_security_check" {
  name                = "aws-guardian-hourly-security"
  description         = "Hourly EC2 and S3 security checks (no cost check)"
  schedule_expression = "cron(0 * * * ? *)" # Every hour at :00
  is_enabled          = true

  tags = {
    Name = "aws-guardian-hourly-security"
  }
}

resource "aws_cloudwatch_event_target" "hourly_security_lambda" {
  rule      = aws_cloudwatch_event_rule.hourly_security_check.name
  target_id = "GuardianSecurityCheckLambda"
  arn       = aws_lambda_function.guardian.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  input = jsonencode({
    time       = "$.time"
    source     = "aws.events"
    check_type = "security" # Tells Lambda to skip cost check
  })
}

# ============================================================================
# Rule 2: Daily Cost Monitoring (Once per day at midnight UTC)
# ============================================================================
resource "aws_cloudwatch_event_rule" "daily_cost_check" {
  name                = "aws-guardian-daily-cost"
  description         = "Daily Cost Explorer check only"
  schedule_expression = "cron(0 0 * * ? *)" # Every day at 00:00 UTC
  is_enabled          = true

  tags = {
    Name = "aws-guardian-daily-cost"
  }
}

resource "aws_cloudwatch_event_target" "daily_cost_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_cost_check.name
  target_id = "GuardianCostCheckLambda"
  arn       = aws_lambda_function.guardian.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  input = jsonencode({
    time       = "$.time"
    source     = "aws.events"
    check_type = "cost" # Tells Lambda to run cost check only
  })
}

# ============================================================================
# IAM Role for EventBridge to invoke Lambda
# ============================================================================
resource "aws_iam_role" "eventbridge_role" {
  name_prefix = "aws-guardian-eventbridge-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "aws-guardian-eventbridge-role"
  }
}

# ============================================================================
# IAM Policy: Allow EventBridge to invoke Guardian Lambda
# ============================================================================
resource "aws_iam_role_policy" "eventbridge_lambda_invoke" {
  name_prefix = "eventbridge-lambda-invoke-"
  role        = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "${aws_lambda_function.guardian.arn}:*"
      }
    ]
  })
}

# ============================================================================
# Lambda Permissions
# ============================================================================
resource "aws_lambda_permission" "allow_eventbridge_hourly" {
  statement_id  = "AllowExecutionFromEventBridgeHourly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.guardian.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly_security_check.arn
}

resource "aws_lambda_permission" "allow_eventbridge_daily" {
  statement_id  = "AllowExecutionFromEventBridgeDaily"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.guardian.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_cost_check.arn
}

# ============================================================================
# Outputs
# ============================================================================
output "hourly_rule_arn" {
  value       = aws_cloudwatch_event_rule.hourly_security_check.arn
  description = "ARN of hourly security check rule"
}

output "daily_rule_arn" {
  value       = aws_cloudwatch_event_rule.daily_cost_check.arn
  description = "ARN of daily cost check rule"
}
