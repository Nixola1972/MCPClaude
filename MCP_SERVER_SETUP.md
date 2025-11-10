# 🔌 MCP Server Setup - Meetings & Transcriptions

## 📋 Cos'è l'MCP Server?

L'MCP (Model Context Protocol) Server espone i dati delle riunioni a **Claude Desktop**, permettendoti di fare query direttamente nella chat!

**Esempi di comandi:**
```
"Claude, cerca riunioni su fotovoltaico"
"Claude, mostrami tutte le azioni assegnate a Claudia"
"Claude, quali decisioni sono state prese questa settimana?"
"Claude, dammi il riassunto dell'ultima riunione"
```

---

## 🎯 Tools Disponibili

L'MCP Server espone **6 tools**:

### 1. **search_meetings**(query, limit=5)
Ricerca semantica nelle riunioni
```python
query: "riunioni su impianti fotovoltaici"
limit: 5  # max risultati
```

### 2. **get_transcription**(filename)
Trascrizione completa parola per parola
```python
filename: "Senza nome.m4a"
```

### 3. **get_summary**(filename)
Riassunto AI (TL;DR + dettagliato + structured data)
```python
filename: "Senza nome.m4a"
```

### 4. **list_recent_meetings**(limit=10)
Lista ultime riunioni con TL;DR
```python
limit: 10  # ultime N riunioni
```

### 5. **get_action_items**(owner=None)
Tutte le azioni da fare, filtrabili per persona
```python
owner: "Claudia"  # opzionale
```

### 6. **get_decisions**(date_from=None)
Decisioni prese, filtrabili per data
```python
date_from: "2025-11-01"  # opzionale, formato ISO
```

---

## 🚀 Installazione

### Step 1: Sul tuo server

```bash
# Il file è già nel repository
cd ~/MCPClaude

# Verifica che sia presente
ls -lh mcp_server_meetings.py

# Test manuale (opzionale)
python3 mcp_server_meetings.py
# (poi Ctrl+C per uscire)
```

### Step 2: Su Claude Desktop (il tuo computer locale)

**macOS/Linux:**
```bash
# Crea directory config se non esiste
mkdir -p ~/.config/claude

# Copia il file di configurazione
# NOTA: Devi copiare dal server al tuo computer!
scp sai@srv778971.hstgr.cloud:~/MCPClaude/claude_desktop_config.json ~/.config/claude/

# IMPORTANTE: Modifica il path se necessario
nano ~/.config/claude/claude_desktop_config.json

# Assicurati che il path punti al file sul SERVER remoto
# O se Claude Desktop gira localmente, usa path locale
```

**Windows:**
```
Copia in: %APPDATA%\Claude\claude_desktop_config.json
```

**Contenuto del file:**
```json
{
  "mcpServers": {
    "meetings": {
      "command": "python3",
      "args": [
        "/home/sai/MCPClaude/mcp_server_meetings.py"
      ],
      "env": {
        "PYTHONPATH": "/home/sai/whisper_env/lib/python3.11/site-packages"
      }
    }
  }
}
```

### Step 3: Restart Claude Desktop

```bash
# Chiudi completamente Claude Desktop
# Riapri Claude Desktop

# Verifica che l'MCP server sia connesso:
# Dovresti vedere "meetings" nei tools disponibili
```

---

## 🧪 Test

### Test 1: Da terminale (debugging)

```bash
# Test diretto da terminale
cd ~/MCPClaude

# Crea file test
cat > test_request.json << 'EOF'
{"id": 1, "method": "list_recent_meetings", "params": {"limit": 3}}
EOF

# Esegui test
python3 mcp_server_meetings.py < test_request.json

# Output atteso: JSON con lista riunioni
```

### Test 2: Da Claude Desktop

Una volta configurato, prova questi comandi:

```
1. "Mostrami le ultime 5 riunioni"
   → Usa list_recent_meetings

2. "Cerca riunioni su fotovoltaico"
   → Usa search_meetings con query semantica

3. "Quali sono le azioni assegnate a Claudia?"
   → Usa get_action_items filtrato per "Claudia"

4. "Mostrami il riassunto dell'ultima riunione"
   → Usa list_recent_meetings + get_summary

5. "Quali decisioni abbiamo preso negli ultimi 7 giorni?"
   → Usa get_decisions con date_from
```

---

## 📊 Esempio Output

### search_meetings("fotovoltaico")
```json
{
  "query": "fotovoltaico",
  "results_count": 2,
  "results": [
    {
      "filename": "Senza nome.m4a",
      "relevance_score": 0.89,
      "date": "2025-11-10T09:15:30",
      "duration_minutes": 114,
      "word_count": 561,
      "tldr": "Discussione su avanzamento impianti fotovoltaici...",
      "participants": ["Marco", "Claudia", "Nicola"],
      "topics": ["Impianti fotovoltaici", "Autorizzazioni", "Budget"],
      "action_items": [...]
    }
  ]
}
```

### get_action_items(owner="Claudia")
```json
{
  "filter_owner": "Claudia",
  "total_actions": 3,
  "actions": [
    {
      "meeting": "Senza nome.m4a",
      "date": "2025-11-10T09:15:30",
      "task": "Ottenere risposta dal comune su autorizzazione",
      "owner": "Claudia",
      "deadline": "Lunedì"
    },
    {
      "meeting": "Senza nome.m4a",
      "date": "2025-11-10T09:15:30",
      "task": "Monitorare avviso PNNR per Salvetti Pietro",
      "owner": "Claudia",
      "deadline": "Continuo"
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Errore: "MCP server not connected"

**Causa:** Claude Desktop non riesce a eseguire lo script

**Soluzione:**
```bash
# Verifica permessi
chmod +x ~/MCPClaude/mcp_server_meetings.py

# Verifica path Python
which python3

# Verifica dipendenze
pip install psycopg2-binary qdrant-client requests
```

### Errore: "Connection to PostgreSQL failed"

**Causa:** Database non raggiungibile

**Soluzione:**
```bash
# Test connessione manuale
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='srv778971.hstgr.cloud',
    port=5433,
    dbname='unified_memory',
    user='memory_user',
    password='MemoryDB2025!Sicura'
)
print('✅ Connected!')
"
```

### Errore: "Ollama embedding API not available"

**Causa:** Ollama non in esecuzione

**Soluzione:**
```bash
# Avvia Ollama
ollama serve

# Verifica
curl http://localhost:11434/api/tags
```

---

## 🔒 Sicurezza

⚠️  **IMPORTANTE:** Il file contiene credenziali database!

**Best practices:**
```bash
# Limita permessi
chmod 600 ~/MCPClaude/mcp_server_meetings.py

# Opzionale: usa variabili ambiente invece
export POSTGRES_PASSWORD="MemoryDB2025!Sicura"
# E modifica script per leggere da env
```

---

## 🎯 Prossimi Step

Dopo aver configurato MCP Server:

1. ✅ **Test da Claude Desktop** - Prova tutti i comandi
2. ⏭️  **Streamlit Dashboard** - UI web per visualizzare
3. ⏭️  **Scheduler** - Automazione notturna

---

## 📞 Help

Se hai problemi:
1. Verifica log Claude Desktop (Help → View Logs)
2. Test script manualmente: `python3 mcp_server_meetings.py`
3. Controlla connessione DB e Qdrant
4. Verifica path nel config file

---

**Versione:** 1.0
**Data:** 2025-11-10
**Tools:** 6 disponibili
**Status:** Production Ready ✅
