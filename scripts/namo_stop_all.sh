#!/bin/bash

# =============================================================================
# Namo Core - Linux Stop Script
# =============================================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT/logs/.pids"

echo -e "\e[33m[Namo] Stopping all services...\e[0m"

if [ -f "$PID_FILE" ]; then
    BACKEND_PID=$(python3 -c "import json; print(json.load(open('$PID_FILE'))['backend'])" 2>/dev/null || echo 0)
    TUNNEL_PID=$(python3 -c "import json; print(json.load(open('$PID_FILE'))['tunnel'])" 2>/dev/null || echo 0)

    if [ "$BACKEND_PID" -gt 0 ]; then
        kill $BACKEND_PID 2>/dev/null && echo -e "  [OK] Stopped API (PID $BACKEND_PID)"
    fi

    if [ "$TUNNEL_PID" -gt 0 ]; then
        kill $TUNNEL_PID 2>/dev/null && echo -e "  [OK] Stopped Tunnel (PID $TUNNEL_PID)"
    fi

    rm "$PID_FILE"
else
    echo -e "  [INFO] No PID file found. Cleaning up by name..."
    pkill -f "namo_core.main"
    pkill -f "cloudflared"
fi

echo -e "\e[32m  [DONE] All services stopped.\e[0m"