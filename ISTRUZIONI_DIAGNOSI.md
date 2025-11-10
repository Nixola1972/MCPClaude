# 🔍 DIAGNOSI PROBLEMA: Partecipanti e Dati Strutturati Mancanti

## 🎯 Il Problema

Il dashboard Streamlit mostra:
- ❌ NO partecipanti
- ❌ NO topics/argomenti
- ❌ NO decisioni
- ❌ NO action items
- ✅ Solo trascrizione (che sembra un riassunto)

## 🧪 DIAGNOSI - Esegui questi comandi

### Metodo 1: Script Python Completo (CONSIGLIATO)

```bash
cd ~/MCPClaude
python3 DIAGNOSI_COMPLETA.py
```

Questo script testerà:
1. ✅ Ollama attivo e modelli disponibili
2. ✅ Connessione PostgreSQL remoto
3. ✅ Contenuto database (quanti record, struttura)
4. ✅ Generazione JSON con Ollama (test veloce)
5. ✅ Identificazione problema specifico

**IMPORTANTE**: Inviami l'OUTPUT COMPLETO di questo comando!

---

### Metodo 2: Test Separati

Se preferisci testare componente per componente:

#### A. Test Ollama
```bash
cd ~/MCPClaude
bash TEST_OLLAMA.sh
```

#### B. Test Database
```bash
cd ~/MCPClaude
bash TEST_DATABASE.sh
```

---

## 🔍 POSSIBILI CAUSE E SOLUZIONI

### Causa 1: Database vuoto (summaries_count = 0)

**Sintomo**: Il database non contiene record nella tabella `summaries`

**Perché succede**:
- Il workflow v2.1 NON ha mai generato summaries
- Ollama non era attivo durante processing
- File audio troppo corti (< 5 minuti)

**Soluzione**:
```bash
# Ri-processa almeno UN file di test
cd ~/MCPClaude
source ~/whisper_env/bin/activate

# Sposta un file da Processati a Meetings
# (O carica nuovo file)

python3 audio_processing_workflow_v2.py
```

---

### Causa 2: Ollama genera JSON vuoti

**Sintomo**:
```
participants: []
topics: []
decisions: []
```

**Perché succede**:
- gemma3:12b non segue bene il prompt
- Temperatura troppo alta
- Prompt in italiano confonde il modello

**Soluzione A - Prova modello diverso**:
```bash
# Scarica llama3.1:8b (migliore per italiano)
ollama pull llama3.1:8b

# Modifica audio_processing_workflow_v2.py
# Linea 346: cambia "gemma3:12b" → "llama3.1:8b"
nano ~/MCPClaude/audio_processing_workflow_v2.py
# Trova: "model": "gemma3:12b"
# Cambia in: "model": "llama3.1:8b"
```

**Soluzione B - Usa Mistral (ottimo per italiano)**:
```bash
ollama pull mistral:7b

# Modifica workflow per usare mistral
```

---

### Causa 3: Dashboard legge tabella sbagliata

**Sintomo**: Database ha dati MA dashboard li mostra vuoti

**Verifica**:
```bash
# Connessione diretta al database
PGPASSWORD="MemoryDB2025!Sicura" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory

# Query per vedere summaries
SELECT
  source_id,
  summary_type,
  participants,
  topics,
  ARRAY_LENGTH(decisions, 1) as decisions_count
FROM summaries
ORDER BY created_at DESC
LIMIT 3;

# Esci con \q
```

Se vedi dati qui MA non nel dashboard → problema query Streamlit

---

### Causa 4: Colonna file_hash mancante

**Sintomo**: Errore durante workflow

**Soluzione**:
```bash
cd ~/MCPClaude
python3 upgrade_database_v2_1.py
```

---

## 📋 CHECKLIST RAPIDA

Esegui in sequenza:

```bash
# 1. Ollama attivo?
curl -s http://localhost:11434/api/tags | head -5

# 2. gemma3:12b disponibile?
ollama list | grep gemma3

# 3. Database accessibile?
PGPASSWORD="MemoryDB2025!Sicura" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory -c "SELECT COUNT(*) FROM summaries;"

# 4. Ultimo file processato ha summaries?
PGPASSWORD="MemoryDB2025!Sicura" psql -h srv778971.hstgr.cloud -p 5433 -U memory_user -d unified_memory -c "
SELECT
  s.source_id,
  su.participants,
  su.topics,
  ARRAY_LENGTH(su.decisions, 1)
FROM sources s
JOIN summaries su ON su.source_id = s.id
ORDER BY s.created_at DESC
LIMIT 1;
"
```

---

## 🆘 PROSSIMI PASSI

1. **ESEGUI**: `python3 DIAGNOSI_COMPLETA.py`
2. **COPIA**: L'output completo
3. **INVIA**: L'output qui per analisi
4. **ATTENDI**: Identificherò la causa esatta e ti darò il fix

---

## 💡 TEST RAPIDO MANUALE

Se vuoi testare Ollama manualmente:

```bash
# Test interattivo con gemma3:12b
ollama run gemma3:12b

# Poi scrivi questo prompt:
```
Analizza questa trascrizione e rispondi SOLO con JSON:

Marco: Dobbiamo investire 1000 euro in marketing.
Sara: Io contatto il cliente Rossi entro lunedì.

JSON:
{
  "participants": ["Marco", "Sara"],
  "topics": ["Budget marketing"],
  "decisions": [{"decision": "Investire 1000 euro", "by": "Marco"}],
  "action_items": [{"task": "Contattare Rossi", "owner": "Sara", "deadline": "Lunedì"}]
}
```

**Cosa aspettarsi**:
- ✅ **BUONO**: Risponde con JSON valido e strutturato
- ❌ **MALE**: Risponde con testo descrittivo o JSON incompleto
- ❌ **PESSIMO**: Non estrae participants/topics

Se NON genera JSON corretto → causa trovata: **cambia modello!**

---

## 📞 Supporto

Dopo aver eseguito la diagnosi, inviami:
1. Output di `DIAGNOSI_COMPLETA.py`
2. Screenshot dashboard Streamlit (cosa vedi esattamente)
3. Nome dell'ultimo file audio processato

Ti dirò ESATTAMENTE qual è il problema e come risolverlo!
