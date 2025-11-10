# 🚨 PROBLEMI CRITICI IDENTIFICATI - RISOLUZIONE URGENTE

## Situazione Attuale

Il sistema v2.1 **NON PUÒ FUNZIONARE** perché i servizi essenziali sono spenti:

1. ❌ **PostgreSQL è SPENTO** (database dove salvare i dati)
2. ❌ **Ollama è SPENTO** (AI per generare summaries)

Questo spiega perché:
- Non vedi partecipanti, topics, decisioni
- Vedi solo "trascrizione" che sembra un riassunto
- Il dashboard non mostra dati strutturati

---

## 🔧 RISOLUZIONE - PASSO PER PASSO

### 1️⃣ FIX POSTGRESQL (PRIORITÀ MASSIMA)

**Problema**: PostgreSQL non si avvia per errore permessi SSL

**Soluzione**:

```bash
# Fix permessi file SSL
sudo chmod 640 /etc/ssl/private/ssl-cert-snakeoil.key
sudo chown root:ssl-cert /etc/ssl/private/ssl-cert-snakeoil.key

# Avvia PostgreSQL
sudo service postgresql start

# Verifica che sia attivo
pg_isready
# Dovrebbe rispondere: "/var/run/postgresql:5432 - accepting connections"
```

**Se ancora non funziona**, prova a disabilitare SSL temporaneamente:

```bash
# Modifica config PostgreSQL
sudo nano /etc/postgresql/16/main/postgresql.conf

# Cerca la riga:
# ssl = on

# Cambia in:
ssl = off

# Salva (CTRL+O, ENTER, CTRL+X)

# Riavvia PostgreSQL
sudo service postgresql restart

# Verifica
pg_isready
```

---

### 2️⃣ AVVIA OLLAMA (PRIORITÀ MASSIMA)

**Problema**: Ollama non è in esecuzione

**Soluzione**:

```bash
# Avvia Ollama in background
ollama serve &

# Oppure in una sessione tmux separata
tmux new -s ollama
ollama serve
# Poi premi CTRL+B seguito da D per detach

# Verifica che sia attivo
curl http://localhost:11434/api/tags
# Dovrebbe rispondere con lista modelli
```

**Verifica che gemma3:12b sia disponibile**:

```bash
ollama list
# Dovresti vedere gemma3:12b nella lista

# Se non c'è, scaricalo:
ollama pull gemma3:12b
```

---

### 3️⃣ TEST GENERAZIONE JSON

Dopo aver avviato Ollama, testa se genera correttamente i JSON:

```bash
cd ~/MCPClaude
python3 test_ollama_summary.py
```

**Output atteso**:
- ✅ JSON PARSING SUCCESSFUL
- Dovresti vedere partecipanti, topics, decisioni estratti

**Se fallisce**:
- Il prompt potrebbe non funzionare con gemma3:12b
- Potremmo dover cambiare modello (es. llama3.1:8b o mistral)

---

### 4️⃣ VERIFICA DATABASE

Dopo aver avviato PostgreSQL, controlla i dati esistenti:

```bash
psql -U ai_user -d audio_analysis -c "SELECT filename, created_at, participants, topics FROM summaries ORDER BY created_at DESC LIMIT 3;"
```

**Se non ci sono dati**:
- Significa che tutti i file processati precedentemente NON hanno salvato i dati
- Devi ri-processare i file audio

---

### 5️⃣ RI-PROCESSA FILE AUDIO (se database vuoto)

```bash
cd ~/MCPClaude
source ~/whisper_env/bin/activate

# Ri-processa i file (che ora sono in "Processati")
# Opzione A: Spostali manualmente di nuovo in "Meetings"
# Opzione B: Modifica temporaneamente il workflow per leggere da "Processati"

python3 audio_processing_workflow_v2.py
```

---

## 🔍 VERIFICA DASHBOARD

Dopo aver risolto i problemi sopra, verifica il dashboard:

```bash
cd ~/MCPClaude
source ~/whisper_env/bin/activate
streamlit run streamlit_dashboard.py
```

Apri browser e controlla se ora vedi:
- ✅ Partecipanti con badge colorati
- ✅ Topics
- ✅ Decisioni
- ✅ Action items
- ✅ Key numbers
- ✅ Trascrizione completa nel tab dedicato

---

## 📋 CHECKLIST RISOLUZIONE

- [ ] PostgreSQL avviato e funzionante (`pg_isready`)
- [ ] Ollama avviato (`curl localhost:11434/api/tags`)
- [ ] gemma3:12b disponibile (`ollama list`)
- [ ] Test JSON generazione funziona (`python3 test_ollama_summary.py`)
- [ ] Database contiene dati (`psql -U ai_user -d audio_analysis -c "SELECT COUNT(*) FROM summaries;"`)
- [ ] Dashboard mostra tutti i dati strutturati

---

## ❓ PROSSIMI PASSI

**Dopo aver risolto i servizi**, fammi sapere:

1. Hai avviato PostgreSQL e Ollama con successo?
2. Il test JSON (`test_ollama_summary.py`) funziona?
3. Il database contiene già dati strutturati o è vuoto?
4. Il dashboard ora mostra partecipanti, topics, ecc?

**Se qualcosa non funziona**, inviami l'output completo dei comandi in modo che posso aiutarti a risolvere!

---

## 🆘 COMANDI RAPIDI

```bash
# STATUS CHECK COMPLETO
echo "=== POSTGRESQL ===" && pg_isready
echo "=== OLLAMA ===" && curl -s localhost:11434/api/tags | head -1
echo "=== DATABASE ===" && psql -U ai_user -d audio_analysis -c "SELECT COUNT(*) FROM summaries;"
echo "=== DONE ==="
```

Copia e incolla questo comando per un check veloce di tutti i servizi.
