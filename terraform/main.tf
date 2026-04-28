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
  region              = var.aws_region
  allowed_account_ids = ["000000000000"]

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    apigateway     = "http://localhost:4566"
    cloudwatch     = "http://localhost:4566"
    dynamodb       = "http://localhost:4566"
    ec2            = "http://localhost:4566"
    events         = "http://localhost:4566"
    iam            = "http://localhost:4566"
    lambda         = "http://localhost:4566"
    s3             = "http://localhost:4566"
    ssm            = "http://localhost:4566"
    sts            = "http://localhost:4566"
    logs           = "http://localhost:4566"
  }

  default_tags {
    tags = {
      Project     = "aws-guardian"
      Environment = var.environment
      CreatedBy   = "Terraform"
    }
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "use_localstack" {
  description = "Use LocalStack for local development/testing"
  type        = bool
  default     = false
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "cost_threshold" {
  description = "Daily cost threshold in USD"
  type        = number
  default     = 10.0
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token"
  type        = string
  sensitive   = true
}

variable "telegram_chat_id" {
  description = "Telegram Chat ID"
  type        = string
  sensitive   = true
}

variable "discord_webhook_url" {
  description = "Discord Webhook URL"
  type        = string
  sensitive   = true
}

variable "discord_public_key" {
  description = "Discord Public Key"
  type        = string
  sensitive   = true
}

# Store configuration in Parameter Store
resource "aws_ssm_parameter" "cost_threshold" {
  name        = "/aws-guardian/cost-threshold"
  type        = "String"
  value       = var.cost_threshold
  description = "AWS Guardian cost threshold"
}

resource "aws_ssm_parameter" "telegram_bot_token" {
  name        = "/aws-guardian/telegram-bot-token"
  type        = "SecureString"
  value       = var.telegram_bot_token
  description = "Telegram Bot Token"
}

resource "aws_ssm_parameter" "telegram_chat_id" {
  name        = "/aws-guardian/telegram-chat-id"
  type        = "SecureString"
  value       = var.telegram_chat_id
  description = "Telegram Chat ID"
}

resource "aws_ssm_parameter" "discord_webhook_url" {
  name        = "/aws-guardian/discord-webhook-url"
  type        = "SecureString"
  value       = var.discord_webhook_url
  description = "Discord Webhook URL"
}

resource "aws_ssm_parameter" "discord_public_key" {
  name        = "/aws-guardian/discord-public-key"
  type        = "SecureString"
  value       = var.discord_public_key
  description = "Discord Public Key"
}

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
