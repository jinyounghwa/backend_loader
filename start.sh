#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo "${BLUE}[AWS Guardian]${NC} $1"; }
ok()   { echo "${GREEN}[OK]${NC} $1"; }
fail() { echo "${RED}[FAIL]${NC} $1"; }

# --- Load .env file ---
if [ -f ".env" ]; then
    log "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
    ok "Environment variables loaded"
else
    fail ".env file not found. Copy from .env.example: cp .env.example .env"
    exit 1
fi

log "Starting AWS Guardian..."

# --- Docker check ---
if ! docker info > /dev/null 2>&1; then
    fail "Docker is not running. Start Docker first."
    exit 1
fi
ok "Docker is running"

# --- LocalStack ---
log "Starting LocalStack..."
docker-compose up -d 2>/dev/null

log "Waiting for LocalStack..."
for i in $(seq 1 30); do
    if curl -s http://localhost:4566/_localstack/health 2>/dev/null | grep -q '"services"'; then
        break
    fi
    if [ "$i" = "30" ]; then
        fail "LocalStack did not start. Run: docker-compose logs"
        exit 1
    fi
    sleep 2
done
ok "LocalStack is ready (http://localhost:4566)"

# --- Python venv ---
log "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt --quiet 2>/dev/null
ok "Dependencies installed"

# --- Init LocalStack resources ---
log "Initializing LocalStack resources..."
python3 scripts/init_localstack.py
ok "Resources created (DynamoDB, S3, EC2, SSM)"

# --- Environment ---
export AWS_ENV=localstack
export LOCALSTACK_ENDPOINT=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export DYNAMODB_TABLE_NAME=aws-guardian-events

# --- Start scheduler ---
echo ""
log "Starting Guardian scheduler (1-hour interval)..."
nohup python3 lambda/guardian/scheduler.py > guardian-scheduler.log 2>&1 &
SCHEDULER_PID=$!
echo "$SCHEDULER_PID" > .guardian-scheduler.pid
ok "Scheduler started (PID: $SCHEDULER_PID, log: guardian-scheduler.log)"
echo ""

# --- Telegram status ---
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    ok "Telegram alerts sent"

    # --- Telegram bot listener ---
    log "Starting Telegram bot listener..."
    nohup python3 lambda/guardian/responders/telegram_bot.py > guardian-bot.log 2>&1 &
    BOT_PID=$!
    echo "$BOT_PID" > .guardian-bot.pid
    ok "Bot listener started (PID: $BOT_PID, log: guardian-bot.log)"
    echo ""
    echo "  Telegram Commands:"
    echo "    상태: /status, /instances, /history [시간]"
    echo "    제어: /stop <id>, /threshold <금액>"
    echo "    자동: 요금과다 원인수정, 해킹우려 수정"
    echo "    도움: /help"
else
    log "Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable alerts."
fi

echo ""
log "Done. System Running:"
echo ""
echo "  📊 Scheduler:     guardian-scheduler.log (1-hour checks)"
echo "  💬 Telegram Bot:  guardian-bot.log (command listener)"
echo "  🌐 Dashboard:     cd apps/web && npm run dev (port 3000)"
echo ""
echo "  Stop system:      ./stop.sh"
echo "  Run tests:        source venv/bin/activate && python -m pytest tests/ -v"
echo "  View logs:        tail -f guardian-scheduler.log"
echo ""
