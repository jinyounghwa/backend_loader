output "guardian_lambda_arn" {
  value       = aws_lambda_function.guardian.arn
  description = "ARN of the Guardian Lambda function"
}

output "discord_webhook_lambda_arn" {
  value       = aws_lambda_function.discord_webhook.arn
  description = "ARN of the Discord Webhook Lambda function"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.events.name
  description = "DynamoDB table for events"
}

output "events_table_name" {
  value       = aws_dynamodb_table.events.name
  description = "Name of the events DynamoDB table"
}

output "responses_table_name" {
  value       = aws_dynamodb_table.responses.name
  description = "Name of the responses DynamoDB table"
}

output "iam_baseline_table_name" {
  value       = aws_dynamodb_table.iam_baseline.name
  description = "Name of the IAM baseline tracking table"
}

output "discord_webhook_endpoint" {
  value       = "${aws_api_gateway_stage.discord_stage.invoke_url}/interactions"
  description = "Discord webhook endpoint URL"
}

output "hourly_rule_arn" {
  value       = aws_cloudwatch_event_rule.hourly_security_check.arn
  description = "ARN of hourly security check rule"
}

output "daily_rule_arn" {
  value       = aws_cloudwatch_event_rule.daily_cost_check.arn
  description = "ARN of daily cost check rule"
}
