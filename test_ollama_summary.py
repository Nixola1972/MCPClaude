#!/usr/bin/env python3
"""
Test script to verify Ollama is generating structured JSON correctly.
"""

import requests
import json

OLLAMA_API = "http://localhost:11434/api/generate"

# Test with a short sample transcription in Italian
test_transcription = """
Marco: Buongiorno a tutti. Oggi dobbiamo discutere del progetto fotovoltaico per il cliente Rossi.
Sara: Sì, abbiamo ricevuto l'autorizzazione dal comune. Possiamo procedere con l'installazione.
Marco: Perfetto. Qual è la tempistica?
Sara: Entro fine novembre. Ho già contattato Lorandi per fissare la data.
Marco: Ottimo. Per quanto riguarda il budget marketing, propongo di investire 1000 euro al mese in Google Ads per 6 mesi.
Claudia: Sono d'accordo. Dobbiamo però monitorare i risultati ogni mese.
Marco: Perfetto, allora è deciso. Claudia, tu ti occupi di ottenere la risposta definitiva dal comune entro lunedì?
Claudia: Sì, lo farò.
"""

prompt = f"""IMPORTANTE: Rispondi ESCLUSIVAMENTE in lingua ITALIANA. Tutti i testi devono essere in italiano.

Analizza questa trascrizione di riunione italiana e crea un riassunto strutturato in ITALIANO.

TRASCRIZIONE (150 parole, 60s):
{test_transcription}

ESTRAI (in formato JSON, TUTTO in italiano):
1. participants: lista SOLO nomi delle persone PRESENTI alla riunione (che parlano o partecipano attivamente). NON includere clienti, progetti o persone solo menzionate. Esempi: ["Marco", "Sara", "Claudia"]

2. mentioned_people: nomi di persone, clienti, fornitori o aziende MENZIONATE ma NON presenti alla riunione. Esempi: ["Cliente Rossi", "Fornitore XYZ", "Azienda ABC"]

3. topics: argomenti principali discussi in ITALIANO (massimo 8 argomenti). Esempi: ["Avanzamento progetti fotovoltaici", "Budget marketing", "Problemi autorizzazioni"]

4. decisions: decisioni CONCRETE prese durante la riunione, scritte in ITALIANO. Ogni decisione deve avere:
   - decision: cosa è stato deciso (in italiano)
   - by: chi ha deciso (nome persona o "Team")
   - date: quando implementare (o "Immediato" se non specificato)
   Esempi: [
     {{"decision": "Investire 1000 euro al mese in Google Ads per 6 mesi", "by": "Marco", "date": "Immediato"}},
     {{"decision": "Completare installazione entro metà novembre", "by": "Team", "date": "15 novembre"}}
   ]

5. action_items: azioni concrete da fare, scritte in ITALIANO. Ogni azione deve avere:
   - task: cosa fare (descrizione chiara in italiano)
   - owner: chi deve farlo (nome specifico, NON "Sconosciuto")
   - deadline: quando (data o periodo, es. "Lunedì", "15 novembre", "Fine mese")
   Esempi: [
     {{"task": "Ottenere risposta dal comune su autorizzazione", "owner": "Claudia", "deadline": "Lunedì"}},
     {{"task": "Pianificare installazione con Lorandi", "owner": "Marco", "deadline": "Fine novembre"}}
   ]

6. key_numbers: numeri e cifre importanti menzionate. Ogni numero deve avere:
   - amount: il numero/cifra (solo cifre, es. "1000", "6")
   - type: tipo in ITALIANO (es. "budget", "durata", "quantità", "percentuale")
   - context: cosa rappresenta in ITALIANO (breve descrizione)
   Esempi: [
     {{"amount": "1000", "type": "budget", "context": "Budget mensile Google Ads in euro"}},
     {{"amount": "6", "type": "durata", "context": "Durata campagna marketing in mesi"}}
   ]

7. detailed_summary: riassunto dettagliato narrativo in ITALIANO (200-400 parole) che spiega cosa è stato discusso, quali problemi sono emersi, quali soluzioni proposte, e prossimi passi

8. tldr: riassunto ultra-conciso in ITALIANO (1-2 frasi, massimo 40 parole) che cattura l'essenza della riunione

REGOLE FONDAMENTALI:
- Rispondi SOLO con JSON valido, nessun altro testo
- TUTTO il contenuto deve essere in lingua ITALIANA (decisions, action_items, topics, summaries, ecc.)
- Se non trovi informazioni per una sezione, usa array vuoto [] o stringa vuota ""
- Sii preciso e specifico, evita generalizzazioni
- NON usare inglese, SOLO italiano
"""

print("=" * 80)
print("TEST OLLAMA SUMMARY GENERATION")
print("=" * 80)
print("\n📤 Sending request to Ollama...")
print(f"Model: gemma3:12b")
print(f"Transcription length: {len(test_transcription)} chars")

try:
    response = requests.post(OLLAMA_API, json={
        "model": "gemma3:12b",
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3, "num_ctx": 8192}
    }, timeout=240)

    print(f"\n📥 Response status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        raw_response = result['response']

        print("\n" + "=" * 80)
        print("RAW RESPONSE FROM OLLAMA:")
        print("=" * 80)
        print(raw_response)
        print("=" * 80)

        print("\n🔍 Attempting to parse JSON...")
        try:
            summary_json = json.loads(raw_response)

            print("\n✅ JSON PARSING SUCCESSFUL!")
            print("\n" + "=" * 80)
            print("PARSED STRUCTURED DATA:")
            print("=" * 80)

            print(f"\n👥 PARTICIPANTS ({len(summary_json.get('participants', []))}):")
            for p in summary_json.get('participants', []):
                print(f"   - {p}")

            print(f"\n👤 MENTIONED PEOPLE ({len(summary_json.get('mentioned_people', []))}):")
            for m in summary_json.get('mentioned_people', []):
                print(f"   - {m}")

            print(f"\n📋 TOPICS ({len(summary_json.get('topics', []))}):")
            for t in summary_json.get('topics', []):
                print(f"   - {t}")

            print(f"\n🎯 DECISIONS ({len(summary_json.get('decisions', []))}):")
            for d in summary_json.get('decisions', []):
                print(f"   - {d}")

            print(f"\n✅ ACTION ITEMS ({len(summary_json.get('action_items', []))}):")
            for a in summary_json.get('action_items', []):
                print(f"   - {a}")

            print(f"\n🔢 KEY NUMBERS ({len(summary_json.get('key_numbers', []))}):")
            for n in summary_json.get('key_numbers', []):
                print(f"   - {n}")

            print(f"\n📝 TL;DR:")
            print(f"   {summary_json.get('tldr', 'N/A')}")

            print(f"\n📖 DETAILED SUMMARY:")
            print(f"   {summary_json.get('detailed_summary', 'N/A')[:200]}...")

            print("\n" + "=" * 80)
            print("✅ TEST COMPLETED SUCCESSFULLY!")
            print("=" * 80)

            # Check if data is actually populated
            if not summary_json.get('participants'):
                print("\n⚠️  WARNING: No participants extracted!")
            if not summary_json.get('topics'):
                print("⚠️  WARNING: No topics extracted!")
            if not summary_json.get('decisions'):
                print("⚠️  WARNING: No decisions extracted!")

        except json.JSONDecodeError as e:
            print(f"\n❌ JSON PARSING FAILED!")
            print(f"Error: {e}")
            print(f"\nThis means Ollama is not generating valid JSON format.")
            print("The workflow will fail silently and return empty data.")

    else:
        print(f"\n❌ OLLAMA REQUEST FAILED!")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

except requests.exceptions.Timeout:
    print("\n❌ REQUEST TIMEOUT! Ollama took too long to respond.")
except requests.exceptions.ConnectionError:
    print("\n❌ CONNECTION ERROR! Is Ollama running?")
    print("Start it with: ollama serve")
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
