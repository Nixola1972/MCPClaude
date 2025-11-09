#!/bin/bash
#
# Upgrade database PostgreSQL a schema v2.0
# MCP-Optimized Context Architecture
#

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🔄 UPGRADE DATABASE TO SCHEMA V2.0                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Configurazione
DB_HOST="srv778971.hstgr.cloud"
DB_PORT="5433"
DB_NAME="unified_memory"
DB_USER="memory_user"
DB_PASS="MemoryDB2025!Sicura"

echo "📋 Target database:"
echo "   Host: $DB_HOST"
echo "   Port: $DB_PORT"
echo "   Database: $DB_NAME"
echo ""

# Backup prima di procedere
echo "📦 Creating backup..."
BACKUP_FILE="unified_memory_backup_$(date +%Y%m%d_%H%M%S).sql"

PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -F plain \
    -f "$BACKUP_FILE" 2>/dev/null || echo "⚠️  pg_dump non disponibile, skip backup"

if [ -f "$BACKUP_FILE" ]; then
    echo "   ✅ Backup salvato: $BACKUP_FILE"
else
    echo "   ⚠️  Backup non creato (continua comunque)"
fi

echo ""
echo "⬆️  Applicando schema v2.0..."

# Applica nuovo schema
PGPASSWORD="$DB_PASS" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f init-db-v2.sql

echo ""
echo "✅ Schema v2.0 applicato con successo!"
echo ""
echo "📊 Nuove tabelle create:"
echo "   • transcriptions - testi completi"
echo "   • summaries - riassunti multi-layer"
echo "   • sources - aggiornata con duration_seconds"
echo "   • entities - mantenuta"
echo "   • observations - mantenuta"
echo "   • relations - mantenuta"
echo ""
echo "🔍 Nuove funzionalità:"
echo "   • Multi-layer summaries (tldr, detailed, structured)"
echo "   • JSONB metadata strutturati (participants, topics, decisions, actions)"
echo "   • Full-text search su summaries"
echo "   • Performance index su JSONB fields"
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ UPGRADE COMPLETATO                                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
