#!/usr/bin/env python3
"""
Script per CANCELLARE TUTTI I DATI dal database e ricominciare da zero
ATTENZIONE: Questa operazione è IRREVERSIBILE!
"""

import psycopg2
from psycopg2.extras import RealDictCursor

print("=" * 80)
print("⚠️  RESET COMPLETO DATABASE ⚠️")
print("=" * 80)
print("\nQuesta operazione cancellerà TUTTI i dati:")
print("  - Tutte le sources")
print("  - Tutte le transcriptions")
print("  - Tutte le summaries")
print("\n❗ ATTENZIONE: Operazione IRREVERSIBILE!")
print("\nLe tabelle rimarranno intatte (solo i dati verranno cancellati)")
print("=" * 80)

# Ask for confirmation
print("\n⏳ Procedendo con la cancellazione in 3 secondi...")
print("   (Premi CTRL+C per annullare)")

import time
try:
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\n❌ Operazione ANNULLATA dall'utente")
    exit(0)

print("\n🔥 Inizio cancellazione...\n")

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

    # Count before deletion
    cur.execute("SELECT COUNT(*) as count FROM sources")
    sources_before = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) as count FROM transcriptions")
    trans_before = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) as count FROM summaries")
    summ_before = cur.fetchone()['count']

    print(f"📊 PRIMA della cancellazione:")
    print(f"   - sources: {sources_before}")
    print(f"   - transcriptions: {trans_before}")
    print(f"   - summaries: {summ_before}")
    print()

    # Delete in correct order (foreign keys!)
    print("🗑️  Cancellazione summaries...")
    cur.execute("DELETE FROM summaries")
    summ_deleted = cur.rowcount
    print(f"   ✅ Cancellati {summ_deleted} record")

    print("🗑️  Cancellazione transcriptions...")
    cur.execute("DELETE FROM transcriptions")
    trans_deleted = cur.rowcount
    print(f"   ✅ Cancellati {trans_deleted} record")

    print("🗑️  Cancellazione sources...")
    cur.execute("DELETE FROM sources")
    sources_deleted = cur.rowcount
    print(f"   ✅ Cancellati {sources_deleted} record")

    # Commit changes
    conn.commit()

    # Verify deletion
    cur.execute("SELECT COUNT(*) as count FROM sources")
    sources_after = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) as count FROM transcriptions")
    trans_after = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) as count FROM summaries")
    summ_after = cur.fetchone()['count']

    print()
    print(f"📊 DOPO la cancellazione:")
    print(f"   - sources: {sources_after}")
    print(f"   - transcriptions: {trans_after}")
    print(f"   - summaries: {summ_after}")

    conn.close()

    print("\n" + "=" * 80)
    print("✅ RESET COMPLETATO CON SUCCESSO!")
    print("=" * 80)
    print("\n📋 PROSSIMI PASSI:")
    print("\n1. Assicurati che i file audio siano in Nextcloud/Audio_Riunioni/")
    print("   (Sposta i file da Audio_Processati/ se necessario)")
    print()
    print("2. Verifica che Ollama sia attivo:")
    print("   curl http://localhost:11434/api/tags")
    print()
    print("3. Esegui il workflow per ri-processare TUTTI i file:")
    print("   cd ~/MCPClaude")
    print("   source ~/whisper_env/bin/activate")
    print("   python3 audio_processing_workflow_v2.py")
    print()
    print("4. Verifica che le summaries vengano create:")
    print("   python3 DIAGNOSI_COMPLETA.py")
    print()
    print("5. Testa il dashboard:")
    print("   streamlit run streamlit_dashboard.py")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ ERRORE durante la cancellazione: {e}")
    import traceback
    traceback.print_exc()
    print("\n⚠️  Il database potrebbe essere in uno stato inconsistente!")
    print("   Verifica manualmente lo stato delle tabelle.")
