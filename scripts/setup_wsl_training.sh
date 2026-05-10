#!/bin/bash
# setup_wsl_training.sh — Automates LoRA training environment setup for WSL2

set -e

echo "🚀 Starting Namo-LoRA Setup for Linux/WSL2..."

# 1. Update and install system dependencies
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3-venv python3-pip python3-dev build-essential dos2unix virtualenv

# 2. Setup Virtual Environment
if [ -d ".venv_linux" ] && [ ! -f ".venv_linux/bin/activate" ]; then
    echo "⚠️ Found broken .venv_linux, removing..."
    rm -rf .venv_linux
fi

VENV_PATH=".venv_linux"
if [ ! -d ".venv_linux" ]; then
    echo "🐍 Creating .venv_linux..."
    # Try standard venv first
    if ! python3 -m venv .venv_linux --copies 2>/dev/null; then
        echo "⚠️  Failed to create venv on /mnt/c (NTFS/OneDrive permission error)."
        echo "🚀 Creating venv in Linux native storage (~/.venv_namo) for better performance..."
        python3 -m venv ~/.venv_namo
        VENV_PATH="$HOME/.venv_namo"
        # Try to symlink for convenience
        ln -sf "$VENV_PATH" .venv_linux || echo "ℹ️  Note: Symlink failed, using direct path."
    fi
fi

# Ensure we source the correct one
source "$VENV_PATH/bin/activate" || source ~/.venv_namo/bin/activate
echo "✅ Virtual environment activated: $(which python)"

# 3. Install PyTorch with CUDA 12.1 (Crucial for GPU training)
echo "🔥 Installing PyTorch with CUDA 12.1 support..."
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 4. Install training requirements
echo "📚 Installing requirements from tools/lora/requirements.txt..."
pip install -r tools/lora/requirements.txt

# 5. Verification
echo "✅ Verifying GPU access..."
python3 -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'Device Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

echo ""
echo "🎉 Setup complete! To start training, run:"
echo "source .venv_linux/bin/activate && python3 tools/lora/train.py"