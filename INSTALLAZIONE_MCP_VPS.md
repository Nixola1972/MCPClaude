# Installazione MCP Server su VPS - Guida Rapida

## 🎯 Obiettivo

Installare il **MCP Server** sul VPS (srv778971.hstgr.cloud) come servizio systemd, accessibile da qualsiasi dispositivo via SSH.

---

## 📋 Prerequisiti

Sul VPS devono essere attivi:
- ✅ PostgreSQL (porta 5433)
- ✅ Qdrant (porta 6333)
- ✅ Ollama (Docker, porta 11434)

---

## 🚀 Installazione Rapida

### 1️⃣ SSH nel VPS

```bash
ssh sai@srv778971.hstgr.cloud
```

---

### 2️⃣ Vai nella directory MCPClaude

```bash
cd ~/MCPClaude

# Assicurati di avere l'ultima versione
git pull origin claude/analyze-server-rhapsody-011CUvAgxegbjcrF6JavPUgK
```

---

### 3️⃣ Rendi eseguibile lo script di installazione

```bash
chmod +x install_mcp_server_vps.sh
```

---

### 4️⃣ Esegui installazione (con sudo)

```bash
sudo ./install_mcp_server_vps.sh
```

Lo script:
- ✅ Copia file in `/opt/mcp_server_meetings/`
- ✅ Installa dipendenze Python
- ✅ Crea servizio systemd
- ✅ Avvia il servizio
- ✅ Configura auto-start al boot

---

### 5️⃣ Verifica installazione

```bash
# Status servizio
sudo systemctl status mcp-server-meetings

# Dovresti vedere:
# ● mcp-server-meetings.service - MCP Server for Meetings Transcriptions
#    Loaded: loaded
#    Active: active (running)
```

---

### 6️⃣ Verifica log

```bash
# Log in tempo reale
sudo journalctl -u mcp-server-meetings -f

# Oppure log file diretto
tail -f /var/log/mcp_server_meetings.log

# Dovresti vedere:
# MCP Server starting...
# PostgreSQL connection: OK
# Qdrant connection: OK
# MCP Server ready, waiting for requests...
```

---

## ✅ Test Funzionamento

### Test 1: Test locale sul VPS

```bash
# Crea file di test
echo '{"method": "tools/list"}' | python3 /opt/mcp_server_meetings/mcp_server_meetings.py
```

Dovrebbe rispondere con la lista dei tools disponibili.

---

### Test 2: Test da PC remoto (SSH)

Dal tuo PC locale:

```bash
# Test connessione SSH + esecuzione MCP
ssh sai@srv778971.hstgr.cloud "echo '{\"method\": \"tools/list\"}' | python3 /opt/mcp_server_meetings/mcp_server_meetings.py"
```

Dovrebbe stampare JSON con lista tools.

---

## 🔧 Configurazione Claude Desktop

Ora configura Claude Desktop sul tuo PC seguendo: **CLAUDE_DESKTOP_SSH_CONFIG.md**

Steps principali:
1. Genera chiave SSH (se non l'hai)
2. Copia chiave pubblica su VPS
3. Modifica `claude_desktop_config.json`
4. Riavvia Claude Desktop
5. Testa tools MCP

---

## 📊 Gestione Servizio

### Comandi utili

```bash
# Vedere status
sudo systemctl status mcp-server-meetings

# Fermare servizio
sudo systemctl stop mcp-server-meetings

# Avviare servizio
sudo systemctl start mcp-server-meetings

# Riavviare servizio
sudo systemctl restart mcp-server-meetings

# Disabilitare auto-start
sudo systemctl disable mcp-server-meetings

# Riabilitare auto-start
sudo systemctl enable mcp-server-meetings

# Vedere log (ultimi 100 righe)
sudo journalctl -u mcp-server-meetings -n 100

# Seguire log in tempo reale
sudo journalctl -u mcp-server-meetings -f
```

---

## 🐛 Troubleshooting

### Problema: Servizio non si avvia

```bash
# Verifica errori
sudo journalctl -u mcp-server-meetings -n 50

# Verifica file Python
python3 /opt/mcp_server_meetings/mcp_server_meetings.py

# Verifica dipendenze
python3 -c "import psycopg2, qdrant_client, requests; print('OK')"
```

---

### Problema: Connessione database fallisce

```bash
# Test PostgreSQL
PGPASSWORD='MemoryDB2025!Sicura' psql -h localhost -p 5433 -U memory_user -d unified_memory -c "SELECT 1;"

# Se fallisce, verifica che PostgreSQL sia attivo
# Nota: PostgreSQL potrebbe essere in Docker o locale
docker ps | grep postgres
```

---

### Problema: Ollama non risponde

```bash
# Verifica Ollama Docker
docker ps | grep ollama

# Se non attivo
docker start ollama

# Test embedding API
curl http://localhost:11434/api/embeddings -d '{"model": "nomic-embed-text", "prompt": "test"}'
```

---

## 🔄 Aggiornamento MCP Server

Quando c'è una nuova versione:

```bash
# 1. SSH nel VPS
ssh sai@srv778971.hstgr.cloud

# 2. Pull modifiche
cd ~/MCPClaude
git pull

# 3. Copia nuovo file
sudo cp mcp_server_meetings_vps.py /opt/mcp_server_meetings/mcp_server_meetings.py

# 4. Riavvia servizio
sudo systemctl restart mcp-server-meetings

# 5. Verifica
sudo systemctl status mcp-server-meetings
tail -f /var/log/mcp_server_meetings.log
```

---

## 📁 Struttura File sul VPS

```
/opt/mcp_server_meetings/
├── mcp_server_meetings.py          # Script MCP Server

/etc/systemd/system/
├── mcp-server-meetings.service     # Systemd service file

/var/log/
├── mcp_server_meetings.log         # Log file
```

---

## 🎯 Cosa Succede Dopo l'Installazione

1. **Servizio sempre attivo**: MCP Server gira in background
2. **Auto-start al riavvio**: Si riavvia automaticamente se il VPS riavvia
3. **Log centralizzati**: Tutti i log in `/var/log/mcp_server_meetings.log`
4. **Accessibile via SSH**: Da qualsiasi PC con Claude Desktop configurato

---

## 🔐 Sicurezza

✅ **Nessuna porta pubblica**: MCP accessibile solo via SSH
✅ **Connessione criptata**: Tutto tramite SSH tunnel
✅ **Chiavi SSH**: Autenticazione con chiave privata
✅ **Log audit**: Tutte le richieste loggato

**Raccomandazioni**:
- Usa chiave SSH **con password**
- Cambia password database periodicamente
- Monitora log per attività sospette

---

## 📱 Accesso Multi-Dispositivo

Una volta installato sul VPS, puoi accedere da:

- 💻 **PC Ufficio**: Configura SSH + Claude Desktop
- 🏠 **PC Casa**: Configura SSH + Claude Desktop
- 💼 **Laptop**: Configura SSH + Claude Desktop
- 📱 **Altri dispositivi**: Qualsiasi con SSH + Claude Desktop

**Ogni dispositivo** usa la stessa installazione MCP sul VPS!

---

## 🚀 Performance

Con MCP Server sul VPS:
- ✅ **Latenza minima**: Server e dati sullo stesso VPS
- ✅ **GPU disponibile**: Usa Ollama con GPU per embeddings veloci
- ✅ **Sempre disponibile**: 24/7 uptime
- ✅ **Scalabile**: Facile aggiungere risorse al VPS

---

## ✨ Prossimi Passi

Dopo aver installato MCP Server sul VPS:

1. ✅ **Configura Claude Desktop** (vedi CLAUDE_DESKTOP_SSH_CONFIG.md)
2. ✅ **Testa tools MCP** in Claude Desktop
3. ✅ **Inizia a usare** con linguaggio naturale!

Esempi:
- "Mostrami le ultime riunioni"
- "Cerca riunioni che parlano di budget"
- "Quali azioni devo fare questa settimana?"
- "Dammi tutte le decisioni prese negli ultimi 30 giorni"

---

## 📧 Support

In caso di problemi:

1. Controlla log: `sudo journalctl -u mcp-server-meetings -f`
2. Verifica servizi: PostgreSQL, Qdrant, Ollama
3. Test manuale: `python3 /opt/mcp_server_meetings/mcp_server_meetings.py`
4. Verifica connessione SSH dal PC

---

🎉 **Buon utilizzo del tuo MCP Server!**
