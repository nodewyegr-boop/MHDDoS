#!/usr/bin/env bash
# run.sh — start valan api + bot, detached
set -e
cd "$(dirname "$0")"

export BOT_TOKEN="${BOT_TOKEN:?BOT_TOKEN required}"
export PANEL_USERNAME="${PANEL_USERNAME:-valannnnnnnnnnnnnnnnnnnnnnnnnn}"
export API_HOST="${API_HOST:-127.0.0.1}"
export API_PORT="${API_PORT:-8080}"
export API_PUBLIC="${API_PUBLIC:-https://api.valan.shop}"
export API_SELF="${API_SELF:-http://127.0.0.1:8080}"
export DB_PATH="${DB_PATH:-$(pwd)/data/valan.db}"
export MAX_CONCURRENT="${MAX_CONCURRENT:-6}"
export MAX_TIME="${MAX_TIME:-250}"
export MHDDOS_DIR="${MHDDOS_DIR:-$(pwd)}"

mkdir -p data logs

pkill -f "uvicorn api:app" 2>/dev/null || true
pkill -f "python bot.py"   2>/dev/null || true
sleep 1

nohup python3 -m uvicorn api:app --host "$API_HOST" --port "$API_PORT" \
    > logs/api.log 2>&1 &
echo $! > data/api.pid

nohup python3 bot.py > logs/bot.log 2>&1 &
echo $! > data/bot.pid

sleep 3
echo ""
echo "==> valan started"
echo "  api pid : $(cat data/api.pid)  -> logs/api.log"
echo "  bot pid : $(cat data/bot.pid)  -> logs/bot.log"
echo "  health  : curl http://$API_HOST:$API_PORT/health"
echo "  watch   : tail -f logs/api.log logs/bot.log"
echo "  stop    : kill \$(cat data/api.pid) \$(cat data/bot.pid)"