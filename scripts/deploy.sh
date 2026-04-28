#!/bin/bash
set -e

echo "🚀 AWS Guardian Deployment Script"
echo "=================================="

# Variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="$PROJECT_ROOT/lambda"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"

echo "📁 Project root: $PROJECT_ROOT"

# Step 1: Build Lambda packages
echo ""
echo "📦 Building Lambda packages..."

# Create build directories
BUILD_DIR="$TERRAFORM_DIR/build"
mkdir -p "$BUILD_DIR"

# Install dependencies
echo "   Installing Python dependencies..."
pip install -r "$PROJECT_ROOT/requirements.txt" -t "$BUILD_DIR/python/lib/python3.12/site-packages/" --quiet

# Create dependencies layer zip
cd "$BUILD_DIR"
zip -r -q "$TERRAFORM_DIR/python_dependencies.zip" python/
cd "$PROJECT_ROOT"

# Package guardian function
# The zip must contain guardian/ at root so the handler path "guardian.handler.lambda_handler" resolves.
# We also include shared modules that guardian imports.
echo "   Packaging Guardian Lambda..."
cd "$LAMBDA_DIR"
zip -r -q "$TERRAFORM_DIR/lambda_guardian.zip" guardian/ -x "guardian/__pycache__/*" "guardian/*/__pycache__/*"
cd "$PROJECT_ROOT"

# Package discord webhook function
# discord_webhook imports from guardian.* so we include both packages.
echo "   Packaging Discord Webhook Lambda..."
cd "$LAMBDA_DIR"
zip -r -q "$TERRAFORM_DIR/lambda_discord.zip" discord_webhook/ guardian/ -x "*/__pycache__/*"
cd "$PROJECT_ROOT"

# Step 2: Deploy with Terraform
echo ""
echo "🌍 Deploying with Terraform..."

cd "$TERRAFORM_DIR"

# Initialize Terraform
terraform init -upgrade

# Plan
echo ""
echo "📋 Terraform Plan:"
terraform plan -out=tfplan

# Ask for confirmation
echo ""
read -p "Do you want to apply these changes? (yes/no) " -n 3 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    terraform apply tfplan
    echo ""
    echo "✅ Deployment completed successfully!"
    echo ""
    echo "📊 Outputs:"
    terraform output
else
    echo "❌ Deployment cancelled"
    exit 1
fi

cd "$PROJECT_ROOT"

# Step 3: Cleanup
echo ""
echo "🧹 Cleaning up..."
rm -rf "$BUILD_DIR" "$TERRAFORM_DIR/tfplan"

echo ""
echo "✨ AWS Guardian is now deployed and running!"
echo "   Monitoring will start automatically every hour."
