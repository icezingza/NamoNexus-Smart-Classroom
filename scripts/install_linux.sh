#!/usr/bin/env bash
# =============================================================================
# Namo Core — Linux/NAS One-Time Installation Script
# Phase 8: Deployment
#
# Compatible with: Ubuntu 20.04+, Debian, Raspberry Pi OS, Synology NAS (DSM7)
#
# Run once from the project root:
#   chmod +x scripts/install_linux.sh && ./scripts/install_linux.sh
# =============================================================================

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Namo Core — Installation (Linux/NAS)${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Python version check
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[1/6] Checking Python version...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}  ERROR: python3 not found.${NC}"
    echo "  Install with: sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi
PYTHON_VER=$(python3 --version)
echo -e "${GREEN}  Found: $PYTHON_VER${NC}"

# ---------------------------------------------------------------------------
# Step 2: Create virtual environment
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[2/6] Creating Python virtual environment...${NC}"
VENV_PATH="$ROOT/.venv"
if [ -d "$VENV_PATH" ]; then
    echo "  .venv already exists — skipping creation."
else
    python3 -m venv "$VENV_PATH"
    echo -e "${GREEN}  Created: $VENV_PATH${NC}"
fi

# ---------------------------------------------------------------------------
# Step 3: Install Python dependencies
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[3/6] Installing Python dependencies...${NC}"
"$VENV_PATH/bin/pip" install --upgrade pip -q
"$VENV_PATH/bin/pip" install -r "$ROOT/namo_core/requirements.txt"
echo -e "${GREEN}  Dependencies installed.${NC}"

# ---------------------------------------------------------------------------
# Step 4: Node.js check + frontend install
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[4/6] Installing frontend dependencies...${NC}"
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    echo -e "${GREEN}  Found Node.js: $NODE_VER${NC}"
    cd "$ROOT/dashboard" && npm install --silent && cd "$ROOT"
    echo -e "${GREEN}  Frontend dependencies installed.${NC}"
else
    echo -e "${YELLOW}  WARNING: Node.js not found. Dashboard will not be available.${NC}"
    echo "  Install: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install nodejs"
fi

# ---------------------------------------------------------------------------
# Step 5: Copy .env.example → .env (if not exists)
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[5/6] Configuring environment...${NC}"
if [ -f "$ROOT/.env" ]; then
    echo "  .env already exists — skipping copy."
else
    cp "$ROOT/.env.example" "$ROOT/.env"
    echo -e "${GREEN}  Created .env from .env.example${NC}"
    echo -e "${YELLOW}  IMPORTANT: Edit .env to configure API keys and settings.${NC}"
fi

# ---------------------------------------------------------------------------
# Step 6: Create runtime directories + set permissions
# ---------------------------------------------------------------------------
echo -e "${YELLOW}[6/6] Creating runtime directories...${NC}"
mkdir -p "$ROOT/namo_core/data"
mkdir -p "$ROOT/backups"
mkdir -p "$ROOT/logs"
chmod +x "$ROOT/scripts/"*.sh 2>/dev/null || true
echo -e "${GREEN}  Runtime directories ready.${NC}"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Installation complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo "  1. Edit .env with your LLM API keys (if using real LLM)"
echo "  2. Run: ./scripts/start_linux.sh"
echo ""
