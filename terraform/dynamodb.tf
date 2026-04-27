resource "aws_dynamodb_table" "events" {
  name           = "aws-guardian-events"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "event_id"
  range_key      = "timestamp"

  attribute {
    name = "event_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "event_type"
    type = "S"
  }

  attribute {
    name = "severity"
    type = "S"
  }

  attribute {
    name = "gsi_pk"
    type = "S"
  }

  # ============================================================================
  # Global Secondary Indexes for efficient querying
  # ============================================================================

  # GSI 1: AllEventsIndex - for dashboard recent activity
  # Partition Key: gsi_pk (constant "EVENT")
  # Sort Key: timestamp (DESC for latest first)
  global_secondary_index {
    name            = "AllEventsIndex"
    hash_key        = "gsi_pk"
    range_key       = "timestamp"
    projection_type = "INCLUDE"
    non_key_attributes = [
      "event_type",
      "severity",
      "details"
    ]
  }

  # GSI 2: TypeTimestampIndex - for filtering by event_type
  # Partition Key: event_type (cost, ec2, s3, etc.)
  # Sort Key: timestamp (DESC)
  global_secondary_index {
    name            = "TypeTimestampIndex"
    hash_key        = "event_type"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # GSI 3: SeverityTimestampIndex - for filtering by severity
  # Partition Key: severity (info, warning, critical)
  # Sort Key: timestamp (DESC)
  global_secondary_index {
    name            = "SeverityTimestampIndex"
    hash_key        = "severity"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "aws-guardian-events"
    Environment = var.environment
    Purpose     = "AWS Guardian monitoring and alerting"
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
