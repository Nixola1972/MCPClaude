#!/usr/bin/env python3
"""
Script di diagnosi completa per identificare il problema del sistema v2.1
"""

import sys
import requests
import json

print("=" * 80)
print("DIAGNOSI SISTEMA AUDIO TRANSCRIPTION v2.1")
print("=" * 80)

# ===== TEST 1: OLLAMA =====
print("\n" + "=" * 80)
print("TEST 1: OLLAMA")
print("=" * 80)

try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        print("✅ Ollama è ATTIVO")
        models = response.json().get('models', [])
        print(f"   Modelli disponibili: {len(models)}")
        for model in models:
            print(f"   - {model['name']}")

        # Check if gemma3:12b is available
        if any('gemma3:12b' in m['name'] for m in models):
            print("   ✅ gemma3:12b DISPONIBILE")
        else:
            print("   ⚠️  gemma3:12b NON TROVATO!")
            print("      Esegui: ollama pull gemma3:12b")
    else:
        print(f"❌ Ollama risponde ma con errore: {response.status_code}")
except requests.exceptions.ConnectionError:
    print("❌ Ollama NON è attivo!")
    print("   Avvialo con: ollama serve")
    print("   Oppure: systemctl start ollama")
except Exception as e:
    print(f"❌ Errore: {e}")

# ===== TEST 2: POSTGRESQL =====
print("\n" + "=" * 80)
print("TEST 2: POSTGRESQL REMOTO")
print("=" * 80)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(
        host="srv778971.hstgr.cloud",
        port=5433,
        dbname="unified_memory",
        user="memory_user",
        password="MemoryDB2025!Sicura",
        cursor_factory=RealDictCursor
    )
    print("✅ Connessione PostgreSQL OK")

    cur = conn.cursor()

    # Check table counts
    cur.execute("SELECT COUNT(*) as count FROM sources")
    sources_count = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) as count FROM transcriptions")
    trans_count = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) as count FROM summaries")
    summ_count = cur.fetchone()['count']

    print(f"   📊 Tabelle:")
    print(f"      - sources: {sources_count} record")
    print(f"      - transcriptions: {trans_count} record")
    print(f"      - summaries: {summ_count} record")

    if summ_count == 0:
        print("\n   ⚠️  PROBLEMA: Nessun summary nel database!")
        print("      Questo spiega perché non vedi partecipanti, topics, ecc.")
        print("      Causa possibile: workflow non ha mai creato summaries")

    # Check if file_hash column exists
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'sources' AND column_name = 'file_hash'
    """)
    if cur.fetchone():
        print("   ✅ Colonna file_hash esiste")
    else:
        print("   ⚠️  Colonna file_hash NON esiste!")
        print("      Esegui: python3 upgrade_database_v2_1.py")

    # Check latest summary structure
    if summ_count > 0:
        print("\n   🔍 Esempio ultimo summary:")
        cur.execute("""
            SELECT
                s.source_id as filename,
                su.summary_type,
                su.participants,
                su.topics,
                ARRAY_LENGTH(su.decisions, 1) as decisions_count,
                ARRAY_LENGTH(su.action_items, 1) as actions_count,
                ARRAY_LENGTH(su.key_numbers, 1) as numbers_count,
                LENGTH(su.content) as content_length
            FROM sources s
            JOIN summaries su ON su.source_id = s.id
            ORDER BY s.created_at DESC
            LIMIT 1
        """)

        row = cur.fetchone()
        if row:
            print(f"      File: {row['filename']}")
            print(f"      Type: {row['summary_type']}")
            print(f"      Participants: {row['participants']}")
            print(f"      Topics: {row['topics']}")
            print(f"      Decisions: {row['decisions_count']} items")
            print(f"      Actions: {row['actions_count']} items")
            print(f"      Numbers: {row['numbers_count']} items")
            print(f"      Content length: {row['content_length']} chars")

            # Analyze the problem
            if not row['participants'] or len(row['participants']) == 0:
                print("\n      ❌ PROBLEMA: participants è VUOTO!")
            if not row['topics'] or len(row['topics']) == 0:
                print("      ❌ PROBLEMA: topics è VUOTO!")
            if row['decisions_count'] is None or row['decisions_count'] == 0:
                print("      ❌ PROBLEMA: decisions è VUOTO!")

    conn.close()

except ImportError:
    print("❌ psycopg2 non installato!")
    print("   Installa con: pip install psycopg2-binary")
except Exception as e:
    print(f"❌ Errore connessione database: {e}")

# ===== TEST 3: QUICK JSON GENERATION TEST =====
print("\n" + "=" * 80)
print("TEST 3: GENERAZIONE JSON CON OLLAMA")
print("=" * 80)

try:
    test_prompt = """IMPORTANTE: Rispondi SOLO con JSON valido.

Analizza questa breve trascrizione:

Marco: Investiamo 1000 euro in Google Ads per 6 mesi.
Sara: Ok, io contatto il cliente Rossi entro lunedì.

ESTRAI in formato JSON:
{
  "participants": ["Marco", "Sara"],
  "topics": ["Budget marketing"],
  "decisions": [{"decision": "Investire 1000 euro in Google Ads per 6 mesi", "by": "Marco", "date": "Immediato"}],
  "action_items": [{"task": "Contattare cliente Rossi", "owner": "Sara", "deadline": "Lunedì"}],
  "tldr": "Decisione di investire in Google Ads e contattare cliente"
}

Rispondi SOLO con JSON, nessun altro testo."""

    print("📤 Invio richiesta a Ollama gemma3:12b...")
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "gemma3:12b",
        "prompt": test_prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3}
    }, timeout=60)

    if response.status_code == 200:
        result = response.json()
        raw_json = result['response']

        print("📥 Risposta ricevuta, parsing JSON...")

        try:
            parsed = json.loads(raw_json)
            print("✅ JSON parsing SUCCESSFUL!")
            print(f"   Participants: {parsed.get('participants', [])}")
            print(f"   Topics: {parsed.get('topics', [])}")
            print(f"   Decisions: {len(parsed.get('decisions', []))} items")
            print(f"   Actions: {len(parsed.get('action_items', []))} items")

            if not parsed.get('participants'):
                print("\n   ❌ PROBLEMA: Ollama non estrae participants!")
            if not parsed.get('topics'):
                print("   ❌ PROBLEMA: Ollama non estrae topics!")

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing FAILED: {e}")
            print(f"   Raw response: {raw_json[:200]}...")
            print("\n   PROBLEMA: Ollama non genera JSON valido!")
            print("   Possibile soluzione: provare altro modello (llama3.1, mistral)")
    else:
        print(f"❌ Ollama error: {response.status_code}")

except Exception as e:
    print(f"❌ Errore: {e}")

# ===== CONCLUSIONI =====
print("\n" + "=" * 80)
print("RIEPILOGO DIAGNOSI")
print("=" * 80)

print("""
POSSIBILI CAUSE DEL PROBLEMA:

1. ❌ Database VUOTO o senza summaries
   → I file sono stati processati ma le summaries non sono state create
   → Soluzione: ri-processare i file audio con workflow v2.1

2. ❌ Ollama genera JSON VUOTI o MALFORMATI
   → gemma3:12b non segue il prompt correttamente
   → Soluzione: provare modello diverso (llama3.1:8b, mistral:7b)

3. ❌ Dashboard legge dati da TABELLA SBAGLIATA
   → Forse legge da vecchia struttura database
   → Soluzione: verificare query SQL nel dashboard

4. ❌ Colonna file_hash MANCANTE
   → Upgrade database non eseguito
   → Soluzione: python3 upgrade_database_v2_1.py

PROSSIMI PASSI:

A. Se summaries_count = 0:
   → Ri-processa almeno UN file audio di test
   → Verifica che crei record in tabella summaries

B. Se Ollama genera JSON vuoti:
   → Testa con modello diverso
   → Modifica prompt per essere più specifico

C. Se database OK ma dashboard vuoto:
   → Problema nelle query SQL del dashboard
   → Verificare streamlit_dashboard.py

Esegui questo script e inviami l'OUTPUT COMPLETO!
""")

print("=" * 80)
