#!/bin/bash
# AWS Guardian - Phase 2: Terraform Backend Infrastructure Setup
# This script automates the creation of S3 bucket, DynamoDB lock table, and GitHub OIDC IAM role

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REGION="us-east-1"
GITHUB_ORG="${1:-}"
GITHUB_REPO="backend_loader"

# Helper functions
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

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    print_success "AWS CLI found"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials are not configured properly."
        exit 1
    fi

    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
    print_success "AWS credentials verified"
    print_info "Account ID: $ACCOUNT_ID"
    print_info "User: $AWS_USER"

    # Check GitHub org
    if [ -z "$GITHUB_ORG" ]; then
        print_error "GitHub organization not provided"
        echo -e "${YELLOW}Usage: $0 <GITHUB_ORG>${NC}"
        echo -e "${YELLOW}Example: $0 your-org${NC}"
        exit 1
    fi
    print_success "GitHub org: $GITHUB_ORG"
}

# Step 1: Verify/Create GitHub OIDC Provider
setup_github_oidc_provider() {
    print_header "Step 1: GitHub OIDC Provider Setup"

    # Check if provider already exists
    PROVIDER_EXISTS=$(aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[?OpenIDConnectProviderArn | contains(@, `token.actions.githubusercontent.com`)]' --output json)

    if [ "$(echo $PROVIDER_EXISTS | wc -c)" -gt 5 ]; then
        print_success "GitHub OIDC Provider already exists"
    else
        print_info "Creating GitHub OIDC Provider..."
        aws iam create-open-id-connect-provider \
            --url https://token.actions.githubusercontent.com \
            --client-id-list sts.amazonaws.com \
            --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
            --region $REGION
        print_success "GitHub OIDC Provider created"
    fi
}

# Step 2: Create S3 bucket for Terraform state
setup_s3_bucket() {
    print_header "Step 2: S3 Bucket Creation"

    BUCKET_NAME="aws-guardian-terraform-state-$(date +%s)"

    print_info "Creating S3 bucket: $BUCKET_NAME"
    aws s3 mb s3://${BUCKET_NAME} --region ${REGION}
    print_success "S3 bucket created"

    print_info "Enabling versioning..."
    aws s3api put-bucket-versioning \
        --bucket ${BUCKET_NAME} \
        --versioning-configuration Status=Enabled
    print_success "Versioning enabled"

    print_info "Blocking public access..."
    aws s3api put-public-access-block \
        --bucket ${BUCKET_NAME} \
        --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    print_success "Public access blocked"

    print_info "Enabling encryption..."
    aws s3api put-bucket-encryption \
        --bucket ${BUCKET_NAME} \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'
    print_success "Encryption enabled"

    # Save bucket name for later use
    echo "$BUCKET_NAME" > /tmp/aws_guardian_bucket.txt
    print_info "Bucket name saved to /tmp/aws_guardian_bucket.txt"
}

# Step 3: Create DynamoDB lock table
setup_dynamodb_locks() {
    print_header "Step 3: DynamoDB Lock Table Creation"

    LOCK_TABLE="terraform-locks"

    # Check if table already exists
    TABLE_EXISTS=$(aws dynamodb describe-table --table-name $LOCK_TABLE --region $REGION 2>/dev/null || echo "NOT_FOUND")

    if [ "$TABLE_EXISTS" != "NOT_FOUND" ]; then
        print_success "Lock table '$LOCK_TABLE' already exists"
    else
        print_info "Creating DynamoDB lock table: $LOCK_TABLE"
        aws dynamodb create-table \
            --table-name $LOCK_TABLE \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region ${REGION}

        print_info "Waiting for table to be created..."
        aws dynamodb wait table-exists \
            --table-name $LOCK_TABLE \
            --region ${REGION}
        print_success "Lock table created"
    fi
}

# Step 4: Create GitHub OIDC IAM role
setup_github_iam_role() {
    print_header "Step 4: GitHub OIDC IAM Role Creation"

    ROLE_NAME="github-actions-aws-guardian"
    BUCKET_NAME=$(cat /tmp/aws_guardian_bucket.txt)

    # Create trust policy
    print_info "Creating trust policy..."
    cat > /tmp/github-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

    # Check if role already exists
    ROLE_EXISTS=$(aws iam get-role --role-name $ROLE_NAME 2>/dev/null || echo "NOT_FOUND")

    if [ "$ROLE_EXISTS" != "NOT_FOUND" ]; then
        print_success "Role '$ROLE_NAME' already exists"
    else
        print_info "Creating IAM role: $ROLE_NAME"
        aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document file:///tmp/github-trust-policy.json
        print_success "IAM role created"
    fi

    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
    print_info "Role ARN: $ROLE_ARN"
    echo "$ROLE_ARN" > /tmp/aws_guardian_role_arn.txt
}

# Step 5: Attach permissions to GitHub role
setup_github_role_policy() {
    print_header "Step 5: GitHub IAM Role Policy Attachment"

    ROLE_NAME="github-actions-aws-guardian"
    BUCKET_NAME=$(cat /tmp/aws_guardian_bucket.txt)

    # Create inline policy
    print_info "Creating inline policy..."
    cat > /tmp/github-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaPermissions",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction",
        "lambda:DeleteFunction",
        "lambda:TagResource",
        "lambda:UntagResource"
      ],
      "Resource": "arn:aws:lambda:*:*:function/aws-guardian-*"
    },
    {
      "Sid": "EventBridgePermissions",
      "Effect": "Allow",
      "Action": [
        "events:PutRule",
        "events:PutTargets",
        "events:RemoveTargets",
        "events:DeleteRule",
        "events:DescribeRule",
        "events:ListRulesByTarget",
        "events:ListTargetsByRule"
      ],
      "Resource": "arn:aws:events:*:*:rule/aws-guardian-*"
    },
    {
      "Sid": "DynamoDBPermissions",
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:UpdateTable",
        "dynamodb:DeleteTable",
        "dynamodb:DescribeTable",
        "dynamodb:CreateGlobalSecondaryIndex",
        "dynamodb:UpdateGlobalSecondaryIndexThroughput",
        "dynamodb:DeleteGlobalSecondaryIndex",
        "dynamodb:TagResource",
        "dynamodb:UntagResource"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/aws-guardian-*"
    },
    {
      "Sid": "CloudWatchLogsPermissions",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:DeleteLogGroup",
        "logs:PutRetentionPolicy",
        "logs:DescribeLogGroups",
        "logs:TagLogGroup",
        "logs:UntagLogGroup"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/aws-guardian-*"
    },
    {
      "Sid": "SSMParameterPermissions",
      "Effect": "Allow",
      "Action": [
        "ssm:PutParameter",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:DeleteParameter",
        "ssm:TagResource",
        "ssm:UntagResource"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/aws-guardian/*"
    },
    {
      "Sid": "IAMPermissions",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PassRole",
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies"
      ],
      "Resource": "arn:aws:iam::*:role/aws-guardian-*"
    },
    {
      "Sid": "TerraformStateBackendPermissions",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::aws-guardian-terraform-state-*/*"
    },
    {
      "Sid": "TerraformLockPermissions",
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/terraform-locks"
    }
  ]
}
EOF

    print_info "Attaching policy to role..."
    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name github-actions-policy \
        --policy-document file:///tmp/github-policy.json
    print_success "Policy attached"
}

# Print summary
print_summary() {
    print_header "Infrastructure Setup Summary"

    BUCKET_NAME=$(cat /tmp/aws_guardian_bucket.txt)
    ROLE_ARN=$(cat /tmp/aws_guardian_role_arn.txt)

    cat << EOF
${GREEN}✅ Infrastructure Setup Complete!${NC}

${BLUE}AWS Account Information:${NC}
  Account ID: $ACCOUNT_ID
  Region: $REGION

${BLUE}S3 Terraform State Bucket:${NC}
  Bucket Name: $BUCKET_NAME
  Versioning: Enabled
  Encryption: AES256
  Public Access: Blocked

${BLUE}DynamoDB Lock Table:${NC}
  Table Name: terraform-locks
  Billing Mode: PAY_PER_REQUEST
  Primary Key: LockID

${BLUE}GitHub OIDC IAM Role:${NC}
  Role Name: github-actions-aws-guardian
  Role ARN: $ROLE_ARN
  Trust Policy: GitHub (${GITHUB_ORG}/${GITHUB_REPO})

${YELLOW}Next Steps:${NC}
1. Configure GitHub Secrets with the values above:
   - AWS_ROLE_TO_ASSUME: $ROLE_ARN
   - TERRAFORM_STATE_BUCKET: $BUCKET_NAME
   - TERRAFORM_STATE_KEY: aws-guardian/terraform.tfstate
   - TERRAFORM_LOCK_TABLE: terraform-locks

2. Add Telegram and Discord secrets (optional but recommended):
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
   - DISCORD_WEBHOOK_URL
   - DISCORD_PUBLIC_KEY
   - SLACK_WEBHOOK (optional)

3. Run: ./scripts/configure-github-secrets.sh

4. Push code to GitHub and create a PR to trigger CI/CD:
   git push origin chore/deploy-to-production

${BLUE}Temporary files created:${NC}
  /tmp/aws_guardian_bucket.txt
  /tmp/aws_guardian_role_arn.txt
  /tmp/github-trust-policy.json
  /tmp/github-policy.json

EOF
}

# Main execution
main() {
    check_prerequisites
    setup_github_oidc_provider
    setup_s3_bucket
    setup_dynamodb_locks
    setup_github_iam_role
    setup_github_role_policy
    print_summary
}

# Run main function
main "$@"
