#!/bin/bash

# =============================================================================
# Namo Core - Linux Master Startup Script
# Starts NRE API Server + Cloudflare Tunnel
# =============================================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
PID_FILE="$LOG_DIR/.pids"
VENV_PYTHON="$ROOT/.venv/bin/python"

cd "$ROOT"
mkdir -p "$LOG_DIR"

echo -e "\e[36m================================================\e[0m"
echo -e "\e[36m  Namo Core - Starting All Services (Ubuntu)\e[0m"
echo -e "\e[36m================================================\e[0m"

# 1. Check Redis
echo -e "\e[33m[Redis] Checking status...\e[0m"
if ! systemctl is-active --quiet redis-server; then
    echo -e "  Redis is offline. Starting..."
    sudo service redis-server start
fi
echo -e "\e[32m  [OK] Redis is running\e[0m"

# 2. Start Backend
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "\e[31m[ERROR] .venv not found. Please create it first.\e[0m"
    exit 1
fi

echo -e "\e[33m[API] Starting NRE API Server...\e[0m"
# กำหนด Host เป็น 0.0.0.0 เพื่อให้เป็นส่วนกลาง (Accessible from network)
export NAMO_API_HOST=0.0.0.0
export NAMO_API_PORT=8000
cd "$ROOT/backend"
nohup "$VENV_PYTHON" -m namo_core.main --host 0.0.0.0 --port $NAMO_API_PORT > "$LOG_DIR/backend.log" 2> "$LOG_DIR/backend_error.log" &
BACKEND_PID=$!
echo -e "  PID: $BACKEND_PID"

# Wait for /health
echo -n "  Waiting for API..."
READY=false
for i in {1..30}; do
    if curl -s "http://127.0.0.1:8000/health" > /dev/null; then
        READY=true
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

if [ "$READY" = true ]; then
    echo -e "\e[32m  [OK] API ready at http://127.0.0.1:8000\e[0m"
else
    echo -e "\e[33m  [WARN] API check timed out\e[0m"
fi

# 3. Start Cloudflare Tunnel (Optional)
TUNNEL_PID=0
if command -v cloudflared &> /dev/null; then
    echo -e "\e[33m[Tunnel] Starting Cloudflare Tunnel...\e[0m"
    nohup cloudflared tunnel run namo-core > "$LOG_DIR/tunnel.log" 2>&1 &
    TUNNEL_PID=$!
    echo -e "  PID: $TUNNEL_PID"
else
    echo -e "\e[33m  [SKIP] cloudflared not installed\e[0m"
fi

# Save PIDs
echo "{\"backend\": $BACKEND_PID, \"tunnel\": $TUNNEL_PID}" > "$PID_FILE"

echo -e "\e[32m================================================\e[0m"
echo -e "\e[32m  Namo Core - Ready!\e[0m"
echo -e "\e[32m================================================\e[0m"