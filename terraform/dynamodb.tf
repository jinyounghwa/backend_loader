resource "aws_dynamodb_table" "events" {
  name           = "aws-guardian-events"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "timestamp"
  range_key      = "event_type"

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "event_type"
    type = "S"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "aws-guardian-events"
  }
}

resource "aws_dynamodb_table" "responses" {
  name           = "aws-guardian-responses"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "timestamp"
  range_key      = "action_type"

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "action_type"
    type = "S"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  tags = {
    Name = "aws-guardian-responses"
  }
}

output "events_table_name" {
  value       = aws_dynamodb_table.events.name
  description = "Name of the events DynamoDB table"
}

output "responses_table_name" {
  value       = aws_dynamodb_table.responses.name
  description = "Name of the responses DynamoDB table"
}
