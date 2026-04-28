#!/bin/bash

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_DIR="$SCRIPT_DIR/build"
LAMBDA_DIR="$SCRIPT_DIR/lambda/guardian"
TERRAFORM_DIR="$SCRIPT_DIR/terraform"

echo "🔨 LocalStack용 Lambda 함수 패키징..."
echo ""

# Clean up old builds
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/lambda-guardian"

# Copy Lambda source code
echo "📁 Lambda 소스 코드 복사 중..."
cp -r "$LAMBDA_DIR" "$BUILD_DIR/lambda-guardian/lambda/"

# Install dependencies
echo "📦 의존성 설치 중..."
cd "$BUILD_DIR/lambda-guardian"
/opt/homebrew/bin/python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" -t . --quiet

# Create zip file
echo "📦 ZIP 파일 생성 중..."
zip -r "$TERRAFORM_DIR/lambda_guardian.zip" . -q

echo "✅ Lambda 패키징 완료!"
echo "   파일: $TERRAFORM_DIR/lambda_guardian.zip"
echo "   크기: $(du -sh $TERRAFORM_DIR/lambda_guardian.zip | cut -f1)"

# List contents
echo ""
echo "📋 패키지 내용:"
unzip -l "$TERRAFORM_DIR/lambda_guardian.zip" | head -20

cd "$SCRIPT_DIR"
