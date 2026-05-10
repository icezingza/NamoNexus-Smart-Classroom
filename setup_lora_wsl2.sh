#!/bin/bash
# Namo-LoRA WSL2 Setup — Steps 1-6
# Run this in WSL2 Ubuntu with: bash setup_lora_wsl2.sh

set -e  # Exit on error

echo "=== LoRA Training WSL2 Setup (Steps 1-6) ==="
echo ""

# Step 1: Navigate to project folder
echo "[Step 1] Navigate to project folder..."
cd /mnt/c/Users/icezi/NamoNexus-Smart-Classroom
echo "✓ Current directory: $(pwd)"
echo ""

# Step 2: Install Python and Pip (if not already installed)
echo "[Step 2] Ensure Python 3.10+ and Pip are installed..."
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
else
    echo "✓ Python $(python3 --version) already installed"
fi
echo "✓ Pip version: $(pip3 --version)"
echo ""

# Step 3: Create virtual environment for Linux (.venv_linux)
echo "[Step 3] Create virtual environment (.venv_linux)..."
if [ -d ".venv_linux" ]; then
    echo "✓ .venv_linux already exists — skipping creation"
else
    python3 -m venv .venv_linux
    echo "✓ Virtual environment created at .venv_linux/"
fi

# Activate virtual environment
source .venv_linux/bin/activate
echo "✓ Virtual environment activated"
echo "✓ Python in venv: $(which python)"
echo ""

# Upgrade pip
echo "[Step 3.5] Upgrade pip in venv..."
pip install --upgrade pip
echo ""

# Step 4: Install PyTorch with CUDA 12.1 support
echo "[Step 4] Install PyTorch with CUDA 12.1 support..."
echo "Installing torch + torchvision + torchaudio (CUDA 12.1)..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
echo "✓ PyTorch installed"
echo ""

# Step 5: Install training libraries from tools/lora/requirements.txt
echo "[Step 5] Install LoRA training libraries from tools/lora/requirements.txt..."
pip install -r tools/lora/requirements.txt
echo "✓ All dependencies installed"
echo ""

# Step 6: Test GPU access with torch.cuda.is_available()
echo "[Step 6] Test GPU access (torch.cuda.is_available())..."
python3 << 'EOF'
import torch

print("=" * 60)
print("CUDA/GPU TEST RESULTS")
print("=" * 60)
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Capability: {torch.cuda.get_device_capability(0)}")
    print(f"CUDA Compute: {torch.cuda.get_device_capability(0)[0]}.{torch.cuda.get_device_capability(0)[1]}")
    print(f"CUDA Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
else:
    print("⚠️  GPU not detected — CPU mode only")
print("=" * 60)

# Test basic tensor operations
print("\nTest basic tensor operation...")
if torch.cuda.is_available():
    x = torch.randn(3, 3).cuda()
    y = torch.randn(3, 3).cuda()
    z = torch.matmul(x, y)
    print(f"✓ GPU tensor operation successful")
    print(f"Result device: {z.device}")
else:
    x = torch.randn(3, 3)
    y = torch.randn(3, 3)
    z = torch.matmul(x, y)
    print(f"✓ CPU tensor operation successful")

print("\nSetup complete! You're ready to train LoRA models.")
EOF

echo ""
echo "=== Setup Complete ✓ ==="
echo "Next steps:"
echo "  1. Run: python3 tools/lora/prepare_data.py"
echo "  2. Run: python3 tools/lora/train.py"
echo ""
