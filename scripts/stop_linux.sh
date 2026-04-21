#!/usr/bin/env bash
# =============================================================================
# Namo Core — Linux/NAS Graceful Stop Script
# Phase 8: Deployment
#
# Stops all Namo Core processes started by start_linux.sh
# Run from the project root:
#   ./scripts/stop_linux.sh
# =============================================================================

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT/logs/.pids"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo ""
echo -e "${YELLOW}Stopping Namo Core...${NC}"

stop_pid() {
    local pid="$1"
    local name="$2"
    if [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid"
            sleep 1
            kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true
            echo -e "${GREEN}  Stopped $name (PID $pid)${NC}"
        else
            echo "  $name (PID $pid) already stopped."
        fi
    fi
}

if [ -f "$PID_FILE" ]; then
    BACKEND_PID=$(python3 -c "import json,sys; d=json.load(open('$PID_FILE')); print(d.get('backend',0))" 2>/dev/null || echo 0)
    FRONTEND_PID=$(python3 -c "import json,sys; d=json.load(open('$PID_FILE')); print(d.get('frontend',0))" 2>/dev/null || echo 0)
    stop_pid "$BACKEND_PID" "Backend"
    stop_pid "$FRONTEND_PID" "Frontend"
    rm -f "$PID_FILE"
else
    echo -e "${YELLOW}  No PID file found. Searching for namo_core processes...${NC}"
    pkill -f "namo_core.main" 2>/dev/null && echo "  Stopped namo_core.main" || echo "  No namo_core.main process found."
fi

echo -e "${GREEN}  Done.${NC}"
echo ""
