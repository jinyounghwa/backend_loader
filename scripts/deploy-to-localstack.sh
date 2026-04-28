#!/bin/bash
# AWS Guardian - LocalStack Deployment using AWS CLI
# Bypasses Terraform provider issues with direct Lambda + EventBridge setup

set -e

# Configuration
ENDPOINT="http://localhost:4566"
REGION="us-east-1"
ROLE_NAME="aws-guardian-role"
LAMBDA_NAME="aws-guardian-monitor"
LAMBDA_ZIP="lambda_guardian.zip"

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verify LocalStack
check_localstack() {
    print_header "LocalStack Health Check"
    if ! curl -s "$ENDPOINT/_localstack/health" > /dev/null; then
        print_error "LocalStack is not running"
        exit 1
    fi
    print_success "LocalStack is running"
}

# Create IAM role for Lambda
create_iam_role() {
    print_header "Creating IAM Role"

    TRUST_POLICY='{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }'

    if aws iam get-role --role-name "$ROLE_NAME" --endpoint-url "$ENDPOINT" 2>/dev/null; then
        print_success "IAM role already exists"
    else
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document "$TRUST_POLICY" \
            --endpoint-url "$ENDPOINT"
        print_success "IAM role created"
    fi

    # Get role ARN
    ROLE_ARN=$(aws iam get-role \
        --role-name "$ROLE_NAME" \
        --endpoint-url "$ENDPOINT" \
        --query 'Role.Arn' \
        --output text)

    print_info "Role ARN: $ROLE_ARN"
}

# Attach policies to role
attach_policies() {
    print_header "Attaching Policies"

    POLICY_DOCUMENT='{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "ec2:DescribeInstances",
            "ec2:StopInstances",
            "s3:ListAllMyBuckets",
            "s3:GetBucketPublicAccessBlock",
            "s3:PutPublicAccessBlock",
            "ce:GetCostAndUsage",
            "cloudtrail:LookupEvents",
            "iam:ListUsers",
            "iam:ListAccessKeys",
            "iam:GetUser",
            "guardduty:ListDetectors",
            "guardduty:ListFindings",
            "guardduty:GetFindings",
            "dynamodb:PutItem",
            "dynamodb:GetItem",
            "dynamodb:Query",
            "dynamodb:Scan",
            "dynamodb:CreateTable",
            "dynamodb:DescribeTable",
            "ssm:GetParameter"
          ],
          "Resource": "*"
        }
      ]
    }'

    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "guardian-policy" \
        --policy-document "$POLICY_DOCUMENT" \
        --endpoint-url "$ENDPOINT"

    print_success "Policies attached"
}

# Deploy Lambda function
deploy_lambda() {
    print_header "Deploying Lambda Function"

    if [ ! -f "$LAMBDA_ZIP" ]; then
        print_error "Lambda ZIP file not found: $LAMBDA_ZIP"
        exit 1
    fi

    # Check if function exists
    if aws lambda get-function --function-name "$LAMBDA_NAME" --endpoint-url "$ENDPOINT" 2>/dev/null; then
        print_info "Updating existing Lambda function..."
        aws lambda update-function-code \
            --function-name "$LAMBDA_NAME" \
            --zip-file "fileb://$LAMBDA_ZIP" \
            --endpoint-url "$ENDPOINT"
        print_success "Lambda function updated"
    else
        print_info "Creating new Lambda function..."
        aws lambda create-function \
            --function-name "$LAMBDA_NAME" \
            --runtime python3.10 \
            --role "$ROLE_ARN" \
            --handler lambda.guardian.handler.lambda_handler \
            --zip-file "fileb://$LAMBDA_ZIP" \
            --timeout 60 \
            --memory-size 256 \
            --endpoint-url "$ENDPOINT"
        print_success "Lambda function created"
    fi
}

# Create DynamoDB tables
create_dynamodb_tables() {
    print_header "Creating DynamoDB Tables"

    # Events table
    print_info "Creating events table..."
    aws dynamodb create-table \
        --table-name aws-guardian-events \
        --attribute-definitions AttributeName=event_id,AttributeType=S AttributeName=timestamp,AttributeType=S \
        --key-schema AttributeName=event_id,KeyType=HASH AttributeName=timestamp,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --endpoint-url "$ENDPOINT" 2>/dev/null || print_info "Events table already exists"
    print_success "Events table created"

    # Responses table
    print_info "Creating responses table..."
    aws dynamodb create-table \
        --table-name aws-guardian-responses \
        --attribute-definitions AttributeName=timestamp,AttributeType=S AttributeName=action_type,AttributeType=S \
        --key-schema AttributeName=timestamp,KeyType=HASH AttributeName=action_type,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --endpoint-url "$ENDPOINT" 2>/dev/null || print_info "Responses table already exists"
    print_success "Responses table created"

    # IAM baseline table
    print_info "Creating IAM baseline table..."
    aws dynamodb create-table \
        --table-name guardian-iam-baseline \
        --attribute-definitions AttributeName=baseline_id,AttributeType=S \
        --key-schema AttributeName=baseline_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --endpoint-url "$ENDPOINT" 2>/dev/null || print_info "IAM baseline table already exists"
    print_success "IAM baseline table created"
}

# Create EventBridge rules
create_eventbridge_rules() {
    print_header "Creating EventBridge Rules"

    # Hourly rule (EC2 + S3)
    print_info "Creating hourly rule (EC2 + S3)..."
    HOURLY_RULE="aws-guardian-hourly"

    aws events put-rule \
        --name "$HOURLY_RULE" \
        --schedule-expression "rate(1 hour)" \
        --state ENABLED \
        --endpoint-url "$ENDPOINT"

    print_success "Hourly rule created"

    # Daily rule (Cost check)
    print_info "Creating daily rule (Cost check)..."
    DAILY_RULE="aws-guardian-daily"

    aws events put-rule \
        --name "$DAILY_RULE" \
        --schedule-expression "rate(1 day)" \
        --state ENABLED \
        --endpoint-url "$ENDPOINT"

    print_success "Daily rule created"
}

# Add Lambda targets to rules
add_targets() {
    print_header "Adding Lambda Targets"

    LAMBDA_ARN="arn:aws:lambda:$REGION:000000000000:function:$LAMBDA_NAME"

    # Hourly rule targets
    print_info "Adding target to hourly rule..."
    aws events put-targets \
        --rule "$HOURLY_RULE" \
        --targets "[{\"Id\":\"1\",\"Arn\":\"$LAMBDA_ARN\",\"RoleArn\":\"$ROLE_ARN\"}]" \
        --endpoint-url "$ENDPOINT"

    print_success "Hourly target added"

    # Daily rule targets
    print_info "Adding target to daily rule..."
    aws events put-targets \
        --rule "$DAILY_RULE" \
        --targets "[{\"Id\":\"1\",\"Arn\":\"$LAMBDA_ARN\",\"RoleArn\":\"$ROLE_ARN\"}]" \
        --endpoint-url "$ENDPOINT"

    print_success "Daily target added"
}

# Grant EventBridge permission to invoke Lambda
grant_lambda_permissions() {
    print_header "Granting Permissions"

    aws lambda add-permission \
        --function-name "$LAMBDA_NAME" \
        --statement-id "AllowEventBridgeInvoke" \
        --action "lambda:InvokeFunction" \
        --principal "events.amazonaws.com" \
        --endpoint-url "$ENDPOINT" 2>/dev/null || true

    print_success "Lambda permissions granted"
}

# Verify deployment
verify_deployment() {
    print_header "Verifying Deployment"

    print_info "Checking Lambda function..."
    aws lambda get-function \
        --function-name "$LAMBDA_NAME" \
        --endpoint-url "$ENDPOINT" \
        --query 'Configuration.FunctionName' \
        --output text

    print_success "Lambda function verified"

    print_info "Checking EventBridge rules..."
    aws events list-rules \
        --endpoint-url "$ENDPOINT" \
        --query 'Rules[*].Name' \
        --output text

    print_success "EventBridge rules verified"
}

# Print summary
print_summary() {
    print_header "LocalStack Deployment Complete"

    cat << EOF
${GREEN}✅ AWS Guardian deployed to LocalStack successfully!${NC}

${BLUE}Deployed Resources:${NC}
  ✅ IAM Role: $ROLE_NAME (with CloudTrail, IAM, GuardDuty permissions)
  ✅ Lambda: $LAMBDA_NAME
  ✅ DynamoDB Tables: events, responses, guardian-iam-baseline
  ✅ EventBridge Rules: hourly (EC2/S3) & daily (Cost)

${BLUE}Test Commands:${NC}
  # Invoke Lambda directly
  aws lambda invoke --function-name $LAMBDA_NAME \\
    --payload '{"check_type":"hourly"}' \\
    --endpoint-url $ENDPOINT \\
    /tmp/response.json

  # List EventBridge rules
  aws events list-rules --endpoint-url $ENDPOINT

  # Check Lambda logs (if available)
  aws logs tail /aws/lambda/$LAMBDA_NAME --follow --endpoint-url $ENDPOINT

${YELLOW}Next Steps:${NC}
  1. Test Lambda invocation with sample event
  2. Verify DynamoDB event storage
  3. Monitor CloudWatch logs
  4. Ready for production deployment

EOF
}

# Main execution
main() {
    check_localstack
    create_iam_role
    attach_policies
    create_dynamodb_tables
    deploy_lambda
    create_eventbridge_rules
    add_targets
    grant_lambda_permissions
    verify_deployment
    print_summary
}

main "$@"
