#!/bin/bash
# Script per testare connessione PostgreSQL e vedere cosa contiene

echo "=========================================="
echo "TEST DATABASE POSTGRESQL REMOTO"
echo "=========================================="
echo ""
echo "Host: srv778971.hstgr.cloud"
echo "Port: 5433"
echo "Database: unified_memory"
echo "User: memory_user"
echo ""

echo "=========================================="
echo "TEST 1: Connessione al database"
echo "=========================================="
PGPASSWORD="MemoryDB2025!Sicura" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory -c "SELECT version();" 2>&1

echo ""
echo ""
echo "=========================================="
echo "TEST 2: Quanti record nelle tabelle?"
echo "=========================================="
PGPASSWORD="MemoryDB2025!Sicura" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory -c "
SELECT
  (SELECT COUNT(*) FROM sources) as sources_count,
  (SELECT COUNT(*) FROM transcriptions) as transcriptions_count,
  (SELECT COUNT(*) FROM summaries) as summaries_count;
" 2>&1

echo ""
echo ""
echo "=========================================="
echo "TEST 3: Ultimi 3 file processati"
echo "=========================================="
PGPASSWORD="MemoryDB2025!Sicura" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory -c "
SELECT
  s.source_id as filename,
  s.created_at,
  s.duration_seconds as duration_sec,
  t.word_count,
  (SELECT COUNT(*) FROM summaries WHERE source_id = s.id) as summary_count
FROM sources s
LEFT JOIN transcriptions t ON t.source_id = s.id
ORDER BY s.created_at DESC
LIMIT 3;
" 2>&1

echo ""
echo ""
echo "=========================================="
echo "TEST 4: Esempio di summary (se esiste)"
echo "=========================================="
PGPASSWORD="MemoryDB2025!Sicura" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory -c "
SELECT
  s.source_id as filename,
  su.summary_type,
  su.participants,
  su.topics,
  LENGTH(su.content) as content_length,
  ARRAY_LENGTH(su.decisions, 1) as decisions_count,
  ARRAY_LENGTH(su.action_items, 1) as action_items_count
FROM sources s
JOIN summaries su ON su.source_id = s.id
ORDER BY s.created_at DESC
LIMIT 2;
" 2>&1

echo ""
echo ""
echo "=========================================="
echo "TEST 5: Verificare se colonna file_hash esiste"
echo "=========================================="
PGPASSWORD="MemoryDB2025!Sicura" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory -c "
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'sources' AND column_name = 'file_hash';
" 2>&1

echo ""
echo ""
echo "=========================================="
echo "COMANDI MANUALI UTILI"
echo "=========================================="
echo ""
echo "# Connessione interattiva:"
echo "PGPASSWORD=\"MemoryDB2025!Sicura\" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory"
echo ""
echo "# Query SQL diretta:"
echo "PGPASSWORD=\"MemoryDB2025!Sicura\" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory -c \"SELECT * FROM summaries LIMIT 1;\""
echo ""
