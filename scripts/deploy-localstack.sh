#!/bin/bash
# AWS Guardian - LocalStack Deployment Script
# Deploys the entire infrastructure to LocalStack for testing

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
LOCALSTACK_ENDPOINT="http://localhost:4566"
AWS_REGION="us-east-1"
AWS_ACCESS_KEY_ID="test"
AWS_SECRET_ACCESS_KEY="test"

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

# Check LocalStack
check_localstack() {
    print_header "LocalStack Health Check"

    # Check if LocalStack is running
    if ! curl -s "$LOCALSTACK_ENDPOINT/_localstack/health" > /dev/null; then
        print_error "LocalStack is not running or not responding"
        echo -e "${YELLOW}Start LocalStack with: docker-compose up -d${NC}"
        exit 1
    fi

    print_success "LocalStack is running"
    print_info "Endpoint: $LOCALSTACK_ENDPOINT"
}

# Set AWS credentials for LocalStack
setup_aws_env() {
    print_header "AWS Credentials Setup"

    export AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY"
    export AWS_DEFAULT_REGION="$AWS_REGION"
    export AWS_ENDPOINT_URL_S3="$LOCALSTACK_ENDPOINT"
    export AWS_ENDPOINT_URL_DYNAMODB="$LOCALSTACK_ENDPOINT"
    export AWS_ENDPOINT_URL_LAMBDA="$LOCALSTACK_ENDPOINT"
    export AWS_ENDPOINT_URL_EVENTS="$LOCALSTACK_ENDPOINT"
    export AWS_ENDPOINT_URL_IAM="$LOCALSTACK_ENDPOINT"

    print_success "AWS environment variables set"
    print_info "Using LocalStack endpoint: $LOCALSTACK_ENDPOINT"
}

# Create S3 bucket
create_s3_bucket() {
    print_header "Step 1: S3 Bucket Creation"

    BUCKET_NAME="aws-guardian-state"

    # Check if bucket exists
    if aws s3 ls "s3://$BUCKET_NAME" --endpoint-url "$LOCALSTACK_ENDPOINT" 2>/dev/null; then
        print_success "S3 bucket already exists: $BUCKET_NAME"
    else
        print_info "Creating S3 bucket: $BUCKET_NAME"
        aws s3 mb "s3://$BUCKET_NAME" \
            --region "$AWS_REGION" \
            --endpoint-url "$LOCALSTACK_ENDPOINT"
        print_success "S3 bucket created"
    fi

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$BUCKET_NAME" \
        --versioning-configuration Status=Enabled \
        --endpoint-url "$LOCALSTACK_ENDPOINT"
    print_success "Versioning enabled"

    echo "$BUCKET_NAME" > /tmp/localstack_bucket.txt
}

# Create DynamoDB table
create_dynamodb_tables() {
    print_header "Step 2: DynamoDB Tables Creation"

    # Create events table
    EVENTS_TABLE="aws-guardian-events"

    # Check if table exists
    if aws dynamodb describe-table \
        --table-name "$EVENTS_TABLE" \
        --endpoint-url "$LOCALSTACK_ENDPOINT" \
        --region "$AWS_REGION" 2>/dev/null; then
        print_success "Events table already exists"
    else
        print_info "Creating events table: $EVENTS_TABLE"
        aws dynamodb create-table \
            --table-name "$EVENTS_TABLE" \
            --attribute-definitions \
                AttributeName=event_id,AttributeType=S \
                AttributeName=timestamp,AttributeType=S \
                AttributeName=gsi_pk,AttributeType=S \
                AttributeName=event_type,AttributeType=S \
                AttributeName=severity,AttributeType=S \
            --key-schema \
                AttributeName=event_id,KeyType=HASH \
                AttributeName=timestamp,KeyType=RANGE \
            --global-secondary-indexes \
                "IndexName=AllEventsIndex,KeySchema=[{AttributeName=gsi_pk,KeyType=HASH},{AttributeName=timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=10,WriteCapacityUnits=10}" \
                "IndexName=TypeTimestampIndex,KeySchema=[{AttributeName=event_type,KeyType=HASH},{AttributeName=timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=10,WriteCapacityUnits=10}" \
                "IndexName=SeverityTimestampIndex,KeySchema=[{AttributeName=severity,KeyType=HASH},{AttributeName=timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=10,WriteCapacityUnits=10}" \
            --billing-mode PROVISIONED \
            --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 \
            --endpoint-url "$LOCALSTACK_ENDPOINT" \
            --region "$AWS_REGION"
        print_success "Events table created"
    fi

    # Create terraform locks table
    LOCKS_TABLE="terraform-locks"

    if aws dynamodb describe-table \
        --table-name "$LOCKS_TABLE" \
        --endpoint-url "$LOCALSTACK_ENDPOINT" \
        --region "$AWS_REGION" 2>/dev/null; then
        print_success "Locks table already exists"
    else
        print_info "Creating locks table: $LOCKS_TABLE"
        aws dynamodb create-table \
            --table-name "$LOCKS_TABLE" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --endpoint-url "$LOCALSTACK_ENDPOINT" \
            --region "$AWS_REGION"
        print_success "Locks table created"
    fi
}

# Run Terraform
run_terraform() {
    print_header "Step 3: Terraform Deployment"

    BUCKET_NAME=$(cat /tmp/localstack_bucket.txt)

    # Create backend configuration for LocalStack
    print_info "Creating Terraform backend configuration..."
    cat > terraform/backend-local.tf << 'EOF'
terraform {
  backend "s3" {
    endpoint            = "http://localhost:4566"
    region              = "us-east-1"
    bucket              = "aws-guardian-state"
    key                 = "aws-guardian/terraform.tfstate"
    encrypt             = false
    dynamodb_table      = "terraform-locks"
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
  }
}
EOF
    print_success "Backend configuration created"

    # Initialize Terraform
    print_info "Initializing Terraform..."
    cd terraform

    # Set AWS credentials for Terraform
    export TF_VAR_aws_access_key="test"
    export TF_VAR_aws_secret_key="test"

    terraform init \
        -backend-config="endpoint=http://localhost:4566" \
        -backend-config="region=us-east-1" \
        -backend-config="bucket=$BUCKET_NAME" \
        -backend-config="key=aws-guardian/terraform.tfstate" \
        -backend-config="dynamodb_table=terraform-locks" \
        -backend-config="skip_region_validation=true" \
        -backend-config="skip_credentials_validation=true" \
        -backend-config="skip_metadata_api_check=true"

    print_success "Terraform initialized"

    # Plan
    print_info "Running Terraform plan..."
    terraform plan \
        -var="telegram_bot_token=test-token" \
        -var="telegram_chat_id=test-chat" \
        -var="discord_webhook_url=test-webhook" \
        -var="discord_public_key=test-key" \
        -out=tfplan.local

    print_success "Terraform plan completed"

    # Apply
    print_info "Applying Terraform configuration..."
    terraform apply -auto-approve tfplan.local

    print_success "Terraform apply completed"

    cd ..
}

# Verify deployment
verify_deployment() {
    print_header "Step 4: Deployment Verification"

    # Check Lambda function
    print_info "Checking Lambda function..."
    if aws lambda list-functions \
        --endpoint-url "$LOCALSTACK_ENDPOINT" \
        --region "$AWS_REGION" | grep -q "aws-guardian"; then
        print_success "Lambda function deployed"
    else
        print_error "Lambda function not found"
    fi

    # Check EventBridge rules
    print_info "Checking EventBridge rules..."
    RULES=$(aws events list-rules \
        --endpoint-url "$LOCALSTACK_ENDPOINT" \
        --region "$AWS_REGION" --query 'Rules[*].Name' --output text)

    if echo "$RULES" | grep -q "aws-guardian"; then
        print_success "EventBridge rules deployed"
        echo "Rules: $RULES"
    else
        print_error "EventBridge rules not found"
    fi

    # Check DynamoDB tables
    print_info "Checking DynamoDB tables..."
    TABLES=$(aws dynamodb list-tables \
        --endpoint-url "$LOCALSTACK_ENDPOINT" \
        --region "$AWS_REGION" --query 'TableNames' --output text)

    if echo "$TABLES" | grep -q "aws-guardian"; then
        print_success "DynamoDB tables deployed"
        echo "Tables: $TABLES"
    else
        print_error "DynamoDB tables not found"
    fi
}

# Print summary
print_summary() {
    print_header "LocalStack Deployment Complete"

    cat << EOF
${GREEN}✅ Deployment to LocalStack successful!${NC}

${BLUE}LocalStack Information:${NC}
  Endpoint: http://localhost:4566
  Region: us-east-1
  Docker: Running (docker-compose ps)

${BLUE}Deployed Resources:${NC}
  ✅ Lambda: aws-guardian-monitor
  ✅ EventBridge: Hourly & Daily rules
  ✅ DynamoDB: Events & Locks tables
  ✅ IAM: Guardian roles & policies

${BLUE}Verify Locally:${NC}
  # Check Lambda
  aws lambda list-functions \\
    --endpoint-url http://localhost:4566 \\
    --region us-east-1

  # Check EventBridge
  aws events list-rules \\
    --endpoint-url http://localhost:4566 \\
    --region us-east-1

  # Check DynamoDB
  aws dynamodb list-tables \\
    --endpoint-url http://localhost:4566 \\
    --region us-east-1

${YELLOW}Next Steps:${NC}
  1. Test Lambda invocation locally
  2. Verify DynamoDB event storage
  3. Check EventBridge rule execution
  4. Ready for production deployment (Phase 5)

${BLUE}Stop LocalStack:${NC}
  docker-compose down

EOF
}

# Main execution
main() {
    check_localstack
    setup_aws_env
    create_s3_bucket
    create_dynamodb_tables
    run_terraform
    verify_deployment
    print_summary
}

main "$@"
