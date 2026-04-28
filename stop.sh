#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log()   { echo "${BLUE}[AWS Guardian]${NC} $1"; }
ok()    { echo "${GREEN}[OK]${NC} $1"; }
warn()  { echo "${YELLOW}[INFO]${NC} $1"; }

log "Shutting down AWS Guardian..."

# --- Stop scheduler ---
if [ -f ".guardian-scheduler.pid" ]; then
    SCHEDULER_PID=$(cat .guardian-scheduler.pid)
    if kill -0 "$SCHEDULER_PID" 2>/dev/null; then
        log "Stopping Guardian scheduler (PID: $SCHEDULER_PID)..."
        kill "$SCHEDULER_PID" 2>/dev/null || true
        ok "Scheduler stopped"
    else
        warn "Scheduler not running"
    fi
    rm -f .guardian-scheduler.pid
else
    warn "Scheduler not found"
fi

# --- Stop bot listener ---
if [ -f ".guardian-bot.pid" ]; then
    BOT_PID=$(cat .guardian-bot.pid)
    if kill -0 "$BOT_PID" 2>/dev/null; then
        log "Stopping Telegram bot listener (PID: $BOT_PID)..."
        kill "$BOT_PID" 2>/dev/null || true
        ok "Bot listener stopped"
    else
        warn "Bot listener not running"
    fi
    rm -f .guardian-bot.pid
else
    warn "Bot listener not found"
fi

# --- Stop frontend ---
if lsof -ti:3000 > /dev/null 2>&1; then
    log "Stopping frontend dashboard (port 3000)..."
    kill $(lsof -ti:3000) 2>/dev/null || true
    ok "Frontend stopped"
else
    warn "Frontend not running"
fi

# --- Stop LocalStack ---
if docker ps --format '{{.Names}}' | grep -q 'aws-guardian-localstack'; then
    log "Stopping LocalStack container..."
    docker-compose down
    ok "LocalStack stopped"
else
    warn "LocalStack not running"
fi

# --- Deactivate venv ---
if [ -n "$VIRTUAL_ENV" ]; then
    log "Deactivating Python virtual environment..."
    deactivate 2>/dev/null || true
    ok "Virtual environment deactivated"
fi

# --- Unset env vars ---
log "Cleaning environment variables..."
unset AWS_ENV LOCALSTACK_ENDPOINT AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
unset AWS_DEFAULT_REGION DYNAMODB_TABLE_NAME
unset TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID
unset MOCK_DAILY_COST MOCK_MONTHLY_COST
unset DISCORD_WEBHOOK_URL DISCORD_PUBLIC_KEY DISCORD_BOT_TOKEN
ok "Environment variables cleared"

echo ""
ok "AWS Guardian shutdown complete"
echo ""
echo "  Start again:  ./start.sh"
echo ""
