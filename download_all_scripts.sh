#!/bin/bash
#
# Scarica TUTTI gli script del sistema unified memory
#

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║   📥 DOWNLOAD COMPLETO UNIFIED MEMORY SCRIPTS         ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

GITHUB_RAW_URL="https://raw.githubusercontent.com/Nixola1972/MCPClaude/claude/analyze-server-rhapsody-011CUvAgxegbjcrF6JavPUgK"

# Lista file da scaricare
declare -a FILES=(
    "audio_processing_workflow.py"
    "query_all_data.py"
    "reset_qdrant_collection.py"
    "update_workflow.sh"
)

echo "📂 Target directory: $HOME"
echo ""

for file in "${FILES[@]}"; do
    echo "⬇️  Downloading: $file"

    # Backup se esiste
    if [ -f "$HOME/$file" ]; then
        cp "$HOME/$file" "$HOME/${file}.backup_$(date +%Y%m%d_%H%M%S)"
        echo "   📦 Backup creato"
    fi

    # Download
    if curl -f -o "$HOME/$file" "${GITHUB_RAW_URL}/$file"; then
        chmod +x "$HOME/$file"
        echo "   ✅ Downloaded: $HOME/$file"
    else
        echo "   ⚠️  Errore download: $file (potrebbe non esistere su GitHub)"
    fi
    echo ""
done

echo "╔════════════════════════════════════════════════════════╗"
echo "║   ✅ DOWNLOAD COMPLETATO                              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📋 FILE DISPONIBILI:"
echo ""
echo "1️⃣  audio_processing_workflow.py"
echo "    Workflow principale (con UUID fix + auto-archiving)"
echo ""
echo "2️⃣  query_all_data.py"
echo "    Query completa PostgreSQL + Qdrant (limit=1000)"
echo ""
echo "3️⃣  reset_qdrant_collection.py"
echo "    Reset collection Qdrant (ricrea pulita)"
echo ""
echo "4️⃣  update_workflow.sh"
echo "    Script di aggiornamento automatico"
echo ""
echo "🚀 QUICK START:"
echo ""
echo "   # Configura credenziali (prima volta)"
echo "   nano ~/audio_processing_workflow.py"
echo ""
echo "   # (Opzionale) Reset Qdrant"
echo "   source ~/whisper_env/bin/activate"
echo "   python3 ~/reset_qdrant_collection.py"
echo ""
echo "   # Lancia workflow"
echo "   python3 ~/audio_processing_workflow.py"
echo ""
echo "   # Query dati"
echo "   python3 ~/query_all_data.py"
echo ""
