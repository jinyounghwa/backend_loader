#!/bin/bash
set -e

echo "🛠️  AWS Guardian Local Development Setup"
echo "========================================"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if Docker is running
echo "🐳 Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker."
    exit 1
fi

# Start LocalStack
echo "🚀 Starting LocalStack container..."
docker-compose up -d

# Wait and initialize
echo ""
echo "⏳ Waiting for LocalStack to be healthy..."
sleep 10

chmod +x scripts/localstack-init.sh
source scripts/localstack-init.sh

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt --quiet

# Setup environment
echo ""
echo "🔧 Setting up environment variables..."
export LOCALSTACK_ENDPOINT=http://localhost:4566
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export TELEGRAM_BOT_TOKEN=test_token
export TELEGRAM_CHAT_ID=test_chat
export DISCORD_WEBHOOK_URL=http://localhost:9999
export DISCORD_PUBLIC_KEY=test_key
export GLM_API_KEY=${GLM_API_KEY:-5fafb543164c452bacbb13aaafdd31a4.yEj71FHKcqNB8o2f}
export DYNAMODB_TABLE_NAME=aws-guardian-events

echo ""
echo "✅ Local development environment ready!"
echo ""
echo "📚 Available commands:"
echo ""
echo "  Test all:"
echo "    python -m pytest tests/ -v"
echo ""
echo "  Test specific module:"
echo "    python -m pytest tests/test_cost.py -v"
echo ""
echo "  Run guardian handler (local):"
echo "    python lambda/guardian/handler.py"
echo ""
echo "  View LocalStack logs:"
echo "    docker-compose logs -f localstack"
echo ""
echo "  Stop LocalStack:"
echo "    docker-compose down"
echo ""
