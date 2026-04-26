resource "aws_cloudwatch_event_rule" "hourly_check" {
  name                = "aws-guardian-hourly-check"
  description         = "Trigger AWS Guardian monitoring every hour"
  schedule_expression = "rate(1 hour)"
  is_enabled          = true
}

resource "aws_cloudwatch_event_target" "guardian_target" {
  rule      = aws_cloudwatch_event_rule.hourly_check.name
  target_id = "GuardianLambda"
  arn       = aws_lambda_function.guardian.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  input = jsonencode({
    source = "aws.events"
  })
}

resource "aws_iam_role" "eventbridge_role" {
  name = "aws-guardian-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_invoke_policy" {
  name = "aws-guardian-eventbridge-invoke-policy"
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.guardian.arn
      }
    ]
  })
}
