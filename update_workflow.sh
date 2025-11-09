#!/bin/bash
#
# Script di aggiornamento automatico del workflow
# Scarica l'ultima versione da GitHub e fa backup del vecchio
#

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║   🔄 AGGIORNAMENTO WORKFLOW AUDIO PROCESSING          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Variabili
GITHUB_RAW_URL="https://raw.githubusercontent.com/Nixola1972/MCPClaude/claude/analyze-server-rhapsody-011CUvAgxegbjcrF6JavPUgK"
TARGET_FILE="$HOME/audio_processing_workflow.py"
BACKUP_DIR="$HOME/workflow_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Crea directory backup
mkdir -p "$BACKUP_DIR"

# Backup file esistente
if [ -f "$TARGET_FILE" ]; then
    echo "📦 Backup file esistente..."
    cp "$TARGET_FILE" "$BACKUP_DIR/audio_processing_workflow_${TIMESTAMP}.py"
    echo "   ✅ Backup salvato: $BACKUP_DIR/audio_processing_workflow_${TIMESTAMP}.py"
else
    echo "ℹ️  Nessun file esistente da backuppare (prima installazione)"
fi

echo ""
echo "⬇️  Download nuova versione da GitHub..."

# Download nuova versione
if curl -f -o "$TARGET_FILE" "${GITHUB_RAW_URL}/audio_processing_workflow.py"; then
    echo "   ✅ File scaricato con successo"
else
    echo "   ❌ Errore download! Ripristino backup..."
    if [ -f "$BACKUP_DIR/audio_processing_workflow_${TIMESTAMP}.py" ]; then
        cp "$BACKUP_DIR/audio_processing_workflow_${TIMESTAMP}.py" "$TARGET_FILE"
    fi
    exit 1
fi

# Rendi eseguibile
chmod +x "$TARGET_FILE"

echo ""
echo "🔍 Verifica modifiche applicate..."

# Verifica UUID fix
if grep -q "uuid.uuid4()" "$TARGET_FILE"; then
    echo "   ✅ UUID fix presente"
else
    echo "   ⚠️  UUID fix non trovato"
fi

# Verifica PROCESSED_FOLDER
if grep -q "PROCESSED_FOLDER" "$TARGET_FILE"; then
    echo "   ✅ PROCESSED_FOLDER configurato"
else
    echo "   ⚠️  PROCESSED_FOLDER non trovato"
fi

# Verifica move_processed_files
if grep -q "def move_processed_files" "$TARGET_FILE"; then
    echo "   ✅ Funzione move_processed_files presente"
else
    echo "   ⚠️  Funzione move_processed_files non trovata"
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   ✅ AGGIORNAMENTO COMPLETATO!                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📋 PROSSIMI STEP:"
echo ""
echo "1️⃣  Verifica configurazione (credenziali VPS nel file):"
echo "    nano ~/audio_processing_workflow.py"
echo ""
echo "2️⃣  (OPZIONALE) Reset Qdrant per ripartire pulito:"
echo "    source ~/whisper_env/bin/activate"
echo "    python3 ~/reset_qdrant_collection.py"
echo ""
echo "3️⃣  Test del nuovo workflow:"
echo "    source ~/whisper_env/bin/activate"
echo "    python3 ~/audio_processing_workflow.py"
echo ""
echo "4️⃣  Query dati per verifica:"
echo "    python3 ~/query_all_data.py"
echo ""
echo "🆕 NUOVE FUNZIONALITÀ:"
echo "   • Fix UUID: i dati ora si accumulano (non vengono sovrascritti)"
echo "   • Auto-archiving: file processati spostati in Audio_Processati"
echo "   • Smart download: salta file già processati"
echo ""
echo "📚 Documentazione completa:"
echo "   https://github.com/Nixola1972/MCPClaude/blob/claude/analyze-server-rhapsody-011CUvAgxegbjcrF6JavPUgK/AGGIORNA_WORKFLOW.md"
echo ""
