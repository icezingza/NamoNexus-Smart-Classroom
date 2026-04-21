#!/usr/bin/env bash
# =============================================================================
# Namo Core — Linux/NAS Startup Script
# Phase 8: Deployment
#
# Starts the FastAPI backend and optionally the React dashboard.
# Run from the project root:
#   ./scripts/start_linux.sh
#
# Options:
#   --backend-only    Start only the backend API server
#   --port 8000       Override API port (default: 8000)
# =============================================================================

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$ROOT/.venv/bin/python"
LOG_DIR="$ROOT/logs"
PID_FILE="$LOG_DIR/.pids"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

BACKEND_ONLY=false
API_PORT=8000

# Parse args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --backend-only) BACKEND_ONLY=true ;;
        --port) API_PORT="$2"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Namo Core — Starting (Linux/NAS)${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}ERROR: Virtual environment not found.${NC}"
    echo "Run first: ./scripts/install_linux.sh"
    exit 1
fi

if [ ! -f "$ROOT/.env" ]; then
    echo -e "${YELLOW}WARNING: .env not found. Copying from .env.example...${NC}"
    cp "$ROOT/.env.example" "$ROOT/.env"
    echo "  Edit .env before running in production."
fi

mkdir -p "$LOG_DIR"
export NAMO_API_PORT=$API_PORT

# ---------------------------------------------------------------------------
# Start Backend (FastAPI + uvicorn)
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[Backend] Starting FastAPI server...${NC}"
nohup "$VENV_PYTHON" -m namo_core.main \
    > "$LOG_DIR/backend.log" \
    2> "$LOG_DIR/backend_error.log" &
BACKEND_PID=$!
echo -e "${GREEN}  Backend PID: $BACKEND_PID${NC}"
echo -e "  Log: $LOG_DIR/backend.log"

# Wait for backend to become ready
echo -n "  Waiting for backend"
READY=false
for i in $(seq 1 20); do
    sleep 1
    if curl -s "http://127.0.0.1:$API_PORT/health" > /dev/null 2>&1; then
        READY=true
        break
    fi
    echo -n "."
done
echo ""

if [ "$READY" = true ]; then
    echo -e "${GREEN}  Backend ready at http://127.0.0.1:$API_PORT${NC}"
else
    echo -e "${YELLOW}  WARNING: Health check timed out. Check $LOG_DIR/backend.log${NC}"
fi

# ---------------------------------------------------------------------------
# Start Frontend (React + Vite) — optional
# ---------------------------------------------------------------------------
FRONTEND_PID=0
if [ "$BACKEND_ONLY" = false ]; then
    DASHBOARD_PATH="$ROOT/dashboard"
    if [ -d "$DASHBOARD_PATH/node_modules" ]; then
        echo ""
        echo -e "${YELLOW}[Frontend] Starting React dashboard...${NC}"
        nohup npm run dev --prefix "$DASHBOARD_PATH" \
            > "$LOG_DIR/frontend.log" 2>&1 &
        FRONTEND_PID=$!
        sleep 2
        echo -e "${GREEN}  Frontend PID: $FRONTEND_PID${NC}"
        echo -e "${GREEN}  Dashboard at http://localhost:5173${NC}"
    else
        echo "[Frontend] Skipped — node_modules not found."
    fi
fi

# Save PIDs
echo "{\"backend\": $BACKEND_PID, \"frontend\": $FRONTEND_PID}" > "$PID_FILE"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Namo Core is running!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "  API:       http://127.0.0.1:$API_PORT"
echo "  API Docs:  http://127.0.0.1:$API_PORT/docs"
[ "$BACKEND_ONLY" = false ] && echo "  Dashboard: http://localhost:5173"
echo ""
echo "  To stop:   ./scripts/stop_linux.sh"
echo "  Logs:      $LOG_DIR"
echo ""
