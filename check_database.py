#!/usr/bin/env python3
"""
Script per verificare contenuto database senza psql
"""

import psycopg2
from psycopg2.extras import RealDictCursor

print("=" * 80)
print("VERIFICA DATABASE - FILE PROCESSATI")
print("=" * 80)

try:
    conn = psycopg2.connect(
        host="srv778971.hstgr.cloud",
        port=5433,
        dbname="unified_memory",
        user="memory_user",
        password="MemoryDB2025!Sicura",
        cursor_factory=RealDictCursor
    )

    cur = conn.cursor()

    # Query file processati
    cur.execute("""
        SELECT
          s.source_id as filename,
          s.created_at,
          s.duration_seconds,
          t.word_count
        FROM sources s
        JOIN transcriptions t ON t.source_id = s.id
        ORDER BY s.created_at DESC;
    """)

    rows = cur.fetchall()

    print(f"\n📊 File processati nel database: {len(rows)}\n")

    for row in rows:
        duration_min = row['duration_seconds'] // 60
        duration_sec = row['duration_seconds'] % 60

        print(f"📁 Filename: {row['filename']}")
        print(f"   📅 Processato: {row['created_at']}")
        print(f"   ⏱️  Durata: {row['duration_seconds']}s ({duration_min}m {duration_sec}s)")
        print(f"   📝 Parole: {row['word_count']}")

        # Check if < 3 minutes
        if row['duration_seconds'] < 180:
            print(f"   ⚠️  PROBLEMA: File troppo corto (< 3 minuti)!")
            print(f"      Il workflow v2.1 NON crea summaries per file < 3 minuti")
        else:
            print(f"   ✅ Durata OK per creare summaries (> 3 minuti)")

        print()

    conn.close()

    print("=" * 80)
    print("CONCLUSIONE")
    print("=" * 80)

    if len(rows) == 0:
        print("❌ Nessun file processato nel database")
    else:
        all_short = all(r['duration_seconds'] < 180 for r in rows)
        if all_short:
            print("⚠️  Tutti i file sono < 3 minuti")
            print("   SOLUZIONE: Processa un file audio > 3 minuti!")
            print()
            print("   Opzioni:")
            print("   1. Carica file lungo (> 3 min) in Nextcloud/Audio_Riunioni/")
            print("   2. Esegui: python3 audio_processing_workflow_v2.py")
        else:
            print("❓ Almeno un file è > 3 minuti MA summaries = 0")
            print("   Possibili cause:")
            print("   - Ollama non era attivo durante processing")
            print("   - Errore durante creazione summary")
            print("   - Usato workflow vecchio (v1.0) invece di v2.1")
            print()
            print("   SOLUZIONE: Ri-processa il file con workflow v2.1")

    print("=" * 80)

except Exception as e:
    print(f"❌ Errore: {e}")
    import traceback
    traceback.print_exc()
