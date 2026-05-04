terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # LocalStack-specific configuration — only active when use_localstack=true
  dynamic "endpoints" {
    for_each = var.use_localstack ? [1] : []
    content {
      apigateway = "http://localhost:4566"
      cloudwatch = "http://localhost:4566"
      dynamodb   = "http://localhost:4566"
      ec2        = "http://localhost:4566"
      events     = "http://localhost:4566"
      iam        = "http://localhost:4566"
      lambda     = "http://localhost:4566"
      s3         = "http://localhost:4566"
      ssm        = "http://localhost:4566"
      sts        = "http://localhost:4566"
      logs       = "http://localhost:4566"
    }
  }

  skip_credentials_validation = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  skip_requesting_account_id  = var.use_localstack

  allowed_account_ids = var.use_localstack ? ["000000000000"] : null

  default_tags {
    tags = {
      Project     = "aws-guardian"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# SSM Parameter Store — secrets and configuration
resource "aws_ssm_parameter" "cost_threshold" {
  name        = "/aws-guardian/cost-threshold"
  type        = "String"
  value       = tostring(var.cost_threshold)
  description = "AWS Guardian daily cost threshold"
  tags        = { Name = "cost-threshold" }
}

resource "aws_ssm_parameter" "telegram_bot_token" {
  name        = "/aws-guardian/telegram-bot-token"
  type        = "SecureString"
  value       = var.telegram_bot_token
  description = "Telegram Bot Token"
  tags        = { Name = "telegram-bot-token" }
}

resource "aws_ssm_parameter" "telegram_chat_id" {
  name        = "/aws-guardian/telegram-chat-id"
  type        = "SecureString"
  value       = var.telegram_chat_id
  description = "Telegram Chat ID"
  tags        = { Name = "telegram-chat-id" }
}

resource "aws_ssm_parameter" "discord_webhook_url" {
  name        = "/aws-guardian/discord-webhook-url"
  type        = "SecureString"
  value       = var.discord_webhook_url
  description = "Discord Webhook URL"
  tags        = { Name = "discord-webhook-url" }
}

resource "aws_ssm_parameter" "discord_public_key" {
  name        = "/aws-guardian/discord-public-key"
  type        = "SecureString"
  value       = var.discord_public_key
  description = "Discord Public Key"
  tags        = { Name = "discord-public-key" }
}
