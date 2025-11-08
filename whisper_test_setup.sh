#!/bin/bash
###############################################################################
# WHISPER TEST SETUP - Per PC con RTX 3060
# Esegui questo script sul TUO PC Linux con le GPU
###############################################################################

echo "=========================================="
echo "🚀 Whisper GPU Test Setup"
echo "=========================================="
echo ""

# 1. Verifica GPU
echo "📊 Step 1: Verifica GPU NVIDIA..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
else
    echo "❌ ERRORE: nvidia-smi non trovato!"
    echo "   Installa i driver NVIDIA prima di continuare"
    exit 1
fi
echo ""

# 2. Verifica Python
echo "🐍 Step 2: Verifica Python..."
python3 --version
echo ""

# 3. Crea ambiente virtuale
echo "📦 Step 3: Crea ambiente virtuale..."
if [ ! -d "whisper_env" ]; then
    python3 -m venv whisper_env
    echo "✅ Ambiente virtuale creato: whisper_env"
else
    echo "ℹ️  Ambiente già esistente"
fi
echo ""

# 4. Attiva ambiente e installa dipendenze
echo "📥 Step 4: Installa dipendenze..."
source whisper_env/bin/activate

# Installa PyTorch con CUDA 11.8 (compatibile con RTX 3060)
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Installa Whisper
pip install openai-whisper

# Installa utility
pip install ffmpeg-python
pip install tqdm

echo ""
echo "✅ Installazione completata!"
echo ""

# 5. Test CUDA
echo "🔥 Step 5: Test CUDA..."
python3 << EOF
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"Number of GPUs: {torch.cuda.device_count()}")

if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        props = torch.cuda.get_device_properties(i)
        print(f"    Memory: {props.total_memory / 1024**3:.2f} GB")
        print(f"    Compute Capability: {props.major}.{props.minor}")
else:
    print("❌ CUDA non disponibile!")
EOF

echo ""
echo "=========================================="
echo "✅ Setup completato!"
echo ""
echo "Prossimi passi:"
echo "1. Attiva l'ambiente: source whisper_env/bin/activate"
echo "2. Esegui il test: python3 whisper_benchmark.py"
echo "=========================================="
