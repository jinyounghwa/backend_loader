#!/bin/bash
# AWS Guardian - Configure GitHub Secrets for CI/CD
# This script helps configure required secrets in GitHub

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check GitHub CLI
check_github_cli() {
    print_header "Checking GitHub CLI"

    if ! command -v gh &> /dev/null; then
        print_error "GitHub CLI is not installed."
        echo -e "${YELLOW}Install from: https://cli.github.com/${NC}"
        exit 1
    fi
    print_success "GitHub CLI found"

    # Check authentication
    if ! gh auth status &> /dev/null; then
        print_error "Not authenticated with GitHub CLI."
        echo -e "${YELLOW}Run: gh auth login${NC}"
        exit 1
    fi
    print_success "GitHub authentication verified"
}

# Get repository information
get_repo_info() {
    print_header "Repository Information"

    REPO=$(gh repo view --json nameWithOwner --q .nameWithOwner)
    if [ -z "$REPO" ]; then
        print_error "Could not determine repository."
        exit 1
    fi

    print_success "Repository: $REPO"
    echo ""
}

# Get AWS information
get_aws_info() {
    print_header "AWS Information"

    if [ -f /tmp/aws_guardian_bucket.txt ] && [ -f /tmp/aws_guardian_role_arn.txt ]; then
        BUCKET_NAME=$(cat /tmp/aws_guardian_bucket.txt)
        ROLE_ARN=$(cat /tmp/aws_guardian_role_arn.txt)
        print_info "Using values from Phase 2 infrastructure setup"
    else
        print_warning "Phase 2 output files not found. Please run deploy-infrastructure.sh first."
        echo ""
        read -p "Enter S3 bucket name: " BUCKET_NAME
        read -p "Enter GitHub IAM Role ARN: " ROLE_ARN
    fi

    print_success "S3 Bucket: $BUCKET_NAME"
    print_success "Role ARN: $ROLE_ARN"
    echo ""
}

# Prompt for optional secrets
get_optional_secrets() {
    print_header "Optional Secrets (Telegram & Discord)"

    echo -e "${YELLOW}These are optional but recommended for notifications.${NC}\n"

    read -p "Enter Telegram Bot Token (or press Enter to skip): " TELEGRAM_BOT_TOKEN
    read -p "Enter Telegram Chat ID (or press Enter to skip): " TELEGRAM_CHAT_ID
    read -p "Enter Discord Webhook URL (or press Enter to skip): " DISCORD_WEBHOOK_URL
    read -p "Enter Discord Public Key (or press Enter to skip): " DISCORD_PUBLIC_KEY
    read -p "Enter Slack Webhook URL (or press Enter to skip): " SLACK_WEBHOOK

    echo ""
}

# Set GitHub secrets
set_secrets() {
    print_header "Setting GitHub Secrets"

    # Required secrets
    echo -e "${BLUE}Setting required AWS secrets...${NC}"

    gh secret set AWS_ROLE_TO_ASSUME --body "$ROLE_ARN" --repo "$REPO"
    print_success "AWS_ROLE_TO_ASSUME"

    gh secret set TERRAFORM_STATE_BUCKET --body "$BUCKET_NAME" --repo "$REPO"
    print_success "TERRAFORM_STATE_BUCKET"

    gh secret set TERRAFORM_STATE_KEY --body "aws-guardian/terraform.tfstate" --repo "$REPO"
    print_success "TERRAFORM_STATE_KEY"

    gh secret set TERRAFORM_LOCK_TABLE --body "terraform-locks" --repo "$REPO"
    print_success "TERRAFORM_LOCK_TABLE"

    # Optional secrets
    if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        gh secret set TELEGRAM_BOT_TOKEN --body "$TELEGRAM_BOT_TOKEN" --repo "$REPO"
        print_success "TELEGRAM_BOT_TOKEN"
    fi

    if [ -n "$TELEGRAM_CHAT_ID" ]; then
        gh secret set TELEGRAM_CHAT_ID --body "$TELEGRAM_CHAT_ID" --repo "$REPO"
        print_success "TELEGRAM_CHAT_ID"
    fi

    if [ -n "$DISCORD_WEBHOOK_URL" ]; then
        gh secret set DISCORD_WEBHOOK_URL --body "$DISCORD_WEBHOOK_URL" --repo "$REPO"
        print_success "DISCORD_WEBHOOK_URL"
    fi

    if [ -n "$DISCORD_PUBLIC_KEY" ]; then
        gh secret set DISCORD_PUBLIC_KEY --body "$DISCORD_PUBLIC_KEY" --repo "$REPO"
        print_success "DISCORD_PUBLIC_KEY"
    fi

    if [ -n "$SLACK_WEBHOOK" ]; then
        gh secret set SLACK_WEBHOOK --body "$SLACK_WEBHOOK" --repo "$REPO"
        print_success "SLACK_WEBHOOK"
    fi

    echo ""
}

# Verify secrets
verify_secrets() {
    print_header "Verifying Secrets"

    echo -e "${BLUE}Repository secrets:${NC}"
    gh secret list --repo "$REPO"
    echo ""
}

# Print summary
print_summary() {
    print_header "GitHub Secrets Configuration Complete"

    cat << EOF
${GREEN}✅ All required secrets have been configured!${NC}

${BLUE}Repository: $REPO${NC}

${BLUE}Required Secrets (4):${NC}
  ✅ AWS_ROLE_TO_ASSUME
  ✅ TERRAFORM_STATE_BUCKET
  ✅ TERRAFORM_STATE_KEY
  ✅ TERRAFORM_LOCK_TABLE

${BLUE}Optional Secrets Configured:${NC}
EOF

    if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        echo "  ✅ TELEGRAM_BOT_TOKEN"
    else
        echo "  ⚠️  TELEGRAM_BOT_TOKEN (skipped)"
    fi

    if [ -n "$TELEGRAM_CHAT_ID" ]; then
        echo "  ✅ TELEGRAM_CHAT_ID"
    else
        echo "  ⚠️  TELEGRAM_CHAT_ID (skipped)"
    fi

    if [ -n "$DISCORD_WEBHOOK_URL" ]; then
        echo "  ✅ DISCORD_WEBHOOK_URL"
    else
        echo "  ⚠️  DISCORD_WEBHOOK_URL (skipped)"
    fi

    if [ -n "$DISCORD_PUBLIC_KEY" ]; then
        echo "  ✅ DISCORD_PUBLIC_KEY"
    else
        echo "  ⚠️  DISCORD_PUBLIC_KEY (skipped)"
    fi

    if [ -n "$SLACK_WEBHOOK" ]; then
        echo "  ✅ SLACK_WEBHOOK"
    else
        echo "  ⚠️  SLACK_WEBHOOK (skipped)"
    fi

    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Push code to GitHub:"
    echo "   git push origin chore/deploy-to-production"
    echo ""
    echo "2. Create a PR on GitHub"
    echo ""
    echo "3. Wait for GitHub Actions checks to pass (Lint → Test → Build)"
    echo ""
    echo "4. Merge PR to main branch"
    echo ""
    echo "5. Approve production deployment when prompted in GitHub Actions"
    echo ""
    echo "6. Monitor deployment in GitHub Actions"
    echo ""
}

# Main
main() {
    check_github_cli
    get_repo_info
    get_aws_info
    get_optional_secrets
    set_secrets
    verify_secrets
    print_summary
}

main "$@"
