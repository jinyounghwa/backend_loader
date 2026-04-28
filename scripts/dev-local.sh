#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "AWS Guardian - LocalStack Development"
echo "======================================="

if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

echo ""
echo "[1/4] Starting LocalStack..."
docker-compose up -d

echo "[2/4] Waiting for LocalStack..."
for i in $(seq 1 30); do
    if curl -s http://localhost:4566/_localstack/health 2>/dev/null | grep -q '"services"'; then
        echo "  LocalStack ready."
        break
    fi
    if [ "$i" = "30" ]; then
        echo "  LocalStack did not start. Check: docker-compose logs"
        exit 1
    fi
    sleep 2
done

echo "[3/4] Initializing LocalStack resources..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt --quiet 2>/dev/null
python3 scripts/init_localstack.py

echo "[4/4] Setting environment..."
export AWS_ENV=localstack
export LOCALSTACK_ENDPOINT=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export DYNAMODB_TABLE_NAME=aws-guardian-events

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    echo "  Telegram: configured"
else
    echo "  Telegram: not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)"
fi

echo ""
echo "Ready. Commands:"
echo ""
echo "  Run guardian:       python3 lambda/guardian/handler.py"
echo "  Run tests:          python -m pytest tests/ -v"
echo "  Start dashboard:    cd apps/web && npm run dev"
echo "  Stop LocalStack:    docker-compose down"
echo ""
