#!/usr/bin/env python3
"""
Upgrade database PostgreSQL a schema v2.0
MCP-Optimized Context Architecture
"""

import psycopg2
import sys

POSTGRES_HOST = "srv778971.hstgr.cloud"
POSTGRES_PORT = 5433
POSTGRES_DB = "unified_memory"
POSTGRES_USER = "memory_user"
POSTGRES_PASS = "MemoryDB2025!Sicura"

# Leggi schema SQL
try:
    with open('init-db-v2.sql', 'r') as f:
        schema_sql = f.read()
except FileNotFoundError:
    print("❌ File init-db-v2.sql non trovato!")
    print("   Assicurati di essere nella directory corretta")
    sys.exit(1)

print("=" * 60)
print("🔄 UPGRADE DATABASE TO SCHEMA V2.0")
print("=" * 60)
print(f"\nTarget: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
print("\n⚠️  ATTENZIONE: Questo eliminerà le tabelle esistenti!")
print("   (I dati audio sono già stati puliti prima)")
print("\nContinuare? (y/n): ", end='')

risposta = input().strip().lower()
if risposta != 'y':
    print("Operazione annullata.")
    sys.exit(0)

print("\n📊 Applicando schema v2.0...")

try:
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASS
    )

    cur = conn.cursor()

    # Esegui schema SQL
    cur.execute(schema_sql)
    conn.commit()

    print("✅ Schema v2.0 applicato con successo!")

    # Verifica tabelle create
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)

    tables = cur.fetchall()

    print("\n📋 Tabelle presenti:")
    for table in tables:
        print(f"   ✅ {table[0]}")

    # Statistiche
    cur.execute("SELECT * FROM database_stats")
    stats = cur.fetchone()

    print("\n📊 Statistiche database:")
    print(f"   Entities: {stats[0]}")
    print(f"   Observations: {stats[1]}")
    print(f"   Relations: {stats[2]}")
    print(f"   Sources: {stats[3]}")
    print(f"   Transcriptions: {stats[5]}")
    print(f"   Summaries: {stats[6]}")
    print(f"     - TL;DR: {stats[7]}")
    print(f"     - Detailed: {stats[8]}")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ UPGRADE COMPLETATO")
    print("=" * 60)
    print("\n🎯 Prossimi step:")
    print("   1. Workflow modificato per creare riassunti")
    print("   2. Test con nuovo audio")
    print("   3. Verifica MCP integration")

except Exception as e:
    print(f"\n❌ Errore durante upgrade: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
