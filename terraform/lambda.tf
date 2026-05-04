resource "aws_lambda_function" "guardian" {
  filename      = "lambda_guardian.zip"
  function_name = "aws-guardian-monitor"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda.guardian.handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  environment {
    variables = {
      TELEGRAM_BOT_TOKEN  = aws_ssm_parameter.telegram_bot_token.value
      TELEGRAM_CHAT_ID    = aws_ssm_parameter.telegram_chat_id.value
      DISCORD_WEBHOOK_URL = aws_ssm_parameter.discord_webhook_url.value

    }
  }

  layers = [aws_lambda_layer_version.dependencies.arn]

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy,
    aws_cloudwatch_log_group.guardian_logs
  ]
}

resource "aws_lambda_function" "discord_webhook" {
  filename      = "lambda_discord.zip"
  function_name = "aws-guardian-discord-webhook"
  role          = aws_iam_role.lambda_role.arn
  handler       = "discord_webhook.handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

  environment {
    variables = {
      DISCORD_PUBLIC_KEY = aws_ssm_parameter.discord_public_key.value
    }
  }

  layers = [aws_lambda_layer_version.dependencies.arn]

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy,
    aws_cloudwatch_log_group.discord_logs
  ]
}

resource "aws_lambda_layer_version" "dependencies" {
  filename            = "python_dependencies.zip"
  layer_name          = "aws-guardian-dependencies"
  compatible_runtimes = ["python3.12"]

  source_code_hash = filebase64sha256("python_dependencies.zip")
}

resource "aws_cloudwatch_log_group" "guardian_logs" {
  name              = "/aws/lambda/aws-guardian-monitor"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "discord_logs" {
  name              = "/aws/lambda/aws-guardian-discord-webhook"
  retention_in_days = 7
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "eventbridge_guardian" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.guardian.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly_check.arn
}

# Lambda permission for API Gateway (Discord)
resource "aws_lambda_permission" "api_gateway_discord" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.discord_webhook.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.discord_api.execution_arn}/*/*"
}

# API Gateway for Discord webhook
resource "aws_api_gateway_rest_api" "discord_api" {
  name        = "aws-guardian-discord-webhook"
  description = "API Gateway for Discord interactions"
}

resource "aws_api_gateway_resource" "discord_resource" {
  rest_api_id = aws_api_gateway_rest_api.discord_api.id
  parent_id   = aws_api_gateway_rest_api.discord_api.root_resource_id
  path_part   = "interactions"
}

resource "aws_api_gateway_method" "discord_post" {
  rest_api_id   = aws_api_gateway_rest_api.discord_api.id
  resource_id   = aws_api_gateway_resource.discord_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "discord_integration" {
  rest_api_id             = aws_api_gateway_rest_api.discord_api.id
  resource_id             = aws_api_gateway_resource.discord_resource.id
  http_method             = aws_api_gateway_method.discord_post.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.discord_webhook.invoke_arn
}

resource "aws_api_gateway_deployment" "discord_deployment" {
  rest_api_id = aws_api_gateway_rest_api.discord_api.id

  depends_on = [aws_api_gateway_integration.discord_integration]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "discord_stage" {
  deployment_id = aws_api_gateway_deployment.discord_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.discord_api.id
  stage_name    = "prod"
}
