# Configurazione Claude Desktop per MCP Server Remoto via SSH

## 📋 Panoramica

Il **MCP Server** gira sul VPS remoto (srv778971.hstgr.cloud) dove risiedono i dati.
Claude Desktop si connette al server **via SSH tunnel sicuro** da qualsiasi PC.

---

## 🏗️ Architettura

```
┌─────────────────────┐
│   Claude Desktop    │
│   (Tuo PC/Laptop)   │
│                     │
│  Legge da stdin:    │
│  ssh -i ~/.ssh/key  │◄────┐
│  user@vps           │     │ SSH Tunnel
│  python3 mcp.py     │     │ (Sicuro, Criptato)
└─────────────────────┘     │
                            │
                            ▼
┌────────────────────────────────────┐
│         VPS Server                 │
│   (srv778971.hstgr.cloud)         │
│                                    │
│  ┌──────────────────────┐         │
│  │  MCP Server          │         │
│  │  /opt/mcp_server/    │         │
│  └──────────────────────┘         │
│           │                        │
│           ▼                        │
│  ┌──────────────────────┐         │
│  │  PostgreSQL          │         │
│  │  Qdrant              │         │
│  │  Ollama (Docker)     │         │
│  └──────────────────────┘         │
└────────────────────────────────────┘
```

---

## 🔧 Setup - Passo per Passo

### 1️⃣ Generare chiave SSH (sul tuo PC)

Se non hai già una chiave SSH:

```bash
# Genera chiave SSH (sul tuo PC)
ssh-keygen -t ed25519 -C "mcp-server-access"

# Salva in: ~/.ssh/mcp_server_key
# Premi INVIO per password vuota (o inserisci password)
```

---

### 2️⃣ Copiare chiave pubblica sul VPS

```bash
# Copia chiave pubblica sul server
ssh-copy-id -i ~/.ssh/mcp_server_key.pub sai@srv778971.hstgr.cloud

# Test connessione SSH
ssh -i ~/.ssh/mcp_server_key sai@srv778971.hstgr.cloud "echo Connessione OK"
```

---

### 3️⃣ Configurare Claude Desktop

**File da modificare**: `~/.config/Claude/claude_desktop_config.json` (Linux/macOS)
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Contenuto**:

```json
{
  "mcpServers": {
    "meetings": {
      "command": "ssh",
      "args": [
        "-i",
        "/home/TUO_USERNAME/.ssh/mcp_server_key",
        "sai@srv778971.hstgr.cloud",
        "python3 /opt/mcp_server_meetings/mcp_server_meetings.py"
      ]
    }
  }
}
```

**IMPORTANTE**: Cambia `/home/TUO_USERNAME/` con il tuo percorso home!

**Per Windows**:
```json
{
  "mcpServers": {
    "meetings": {
      "command": "ssh",
      "args": [
        "-i",
        "C:\\Users\\TUO_USERNAME\\.ssh\\mcp_server_key",
        "sai@srv778971.hstgr.cloud",
        "python3 /opt/mcp_server_meetings/mcp_server_meetings.py"
      ]
    }
  }
}
```

---

### 4️⃣ Test Connessione Manuale

Prima di usare Claude Desktop, testa che il comando funzioni:

```bash
# Test SSH + MCP Server
ssh -i ~/.ssh/mcp_server_key sai@srv778971.hstgr.cloud "python3 /opt/mcp_server_meetings/mcp_server_meetings.py"

# Dovrebbe stampare:
# MCP Server starting...
# PostgreSQL connection: OK
# Qdrant connection: OK
# MCP Server ready, waiting for requests...
```

Se vedi errori, verifica:
- ✅ SSH key corretta
- ✅ MCP server installato su VPS
- ✅ Servizi PostgreSQL, Qdrant, Ollama attivi

---

### 5️⃣ Riavvia Claude Desktop

```bash
# Linux/macOS
killall Claude
# Poi riavvia Claude Desktop dall'icona

# Windows
# Chiudi Claude Desktop dal Task Manager e riavvia
```

---

### 6️⃣ Verifica Tools Disponibili

In Claude Desktop, apri una chat e scrivi:

```
Quali tools MCP hai disponibili?
```

Dovresti vedere:
- ✅ `search_meetings` - Cerca riunioni
- ✅ `get_transcription` - Ottieni trascrizione
- ✅ `get_summary` - Ottieni riassunto
- ✅ `list_recent_meetings` - Lista riunioni recenti
- ✅ `get_action_items` - Ottieni azioni
- ✅ `get_decisions` - Ottieni decisioni

---

## 🧪 Test Funzionalità

Prova questi comandi in Claude Desktop:

### Test 1: Lista riunioni recenti
```
Mostrami le riunioni recenti
```

### Test 2: Cerca riunioni
```
Cerca riunioni che parlano di "budget marketing"
```

### Test 3: Ottieni summary
```
Dammi il riassunto della riunione "Senza nome.m4a"
```

### Test 4: Action items
```
Quali sono le azioni da fare?
```

### Test 5: Decisioni
```
Quali decisioni sono state prese nelle riunioni?
```

---

## 🔒 Sicurezza

✅ **Connessione SSH criptata** (chiave privata)
✅ **Nessuna porta esposta** pubblicamente
✅ **MCP Server** accessibile solo via SSH
✅ **Log centralizzati** sul VPS

**Best practices**:
1. Usa **chiave SSH con password** per maggiore sicurezza
2. Limita accesso SSH solo a IP fidati (opzionale)
3. Monitora log server: `tail -f /var/log/mcp_server_meetings.log`

---

## 🐛 Troubleshooting

### Problema: "Connection refused"

```bash
# Verifica che servizio sia attivo sul VPS
ssh sai@srv778971.hstgr.cloud
sudo systemctl status mcp-server-meetings

# Se non attivo, avvialo:
sudo systemctl start mcp-server-meetings
```

---

### Problema: "Permission denied (publickey)"

```bash
# Verifica chiave SSH
ls -la ~/.ssh/mcp_server_key

# Verifica permessi (devono essere 600)
chmod 600 ~/.ssh/mcp_server_key

# Testa connessione SSH
ssh -i ~/.ssh/mcp_server_key -v sai@srv778971.hstgr.cloud
```

---

### Problema: "Python module not found"

```bash
# SSH nel server
ssh sai@srv778971.hstgr.cloud

# Installa dipendenze
sudo pip3 install psycopg2-binary qdrant-client requests

# Verifica installazione
python3 -c "import psycopg2; import qdrant_client; print('OK')"
```

---

### Problema: Claude Desktop non vede tools

1. Verifica config JSON syntax: https://jsonlint.com/
2. Controlla percorso chiave SSH sia assoluto
3. Riavvia Claude Desktop completamente
4. Controlla log Claude: `~/.config/Claude/logs/`

---

## 📊 Monitoraggio

### Vedere log MCP Server in tempo reale

```bash
# SSH nel VPS
ssh sai@srv778971.hstgr.cloud

# Log systemd
sudo journalctl -u mcp-server-meetings -f

# Log file diretto
tail -f /var/log/mcp_server_meetings.log
```

---

## 🎯 Vantaggi Soluzione

✅ **Accessibile da ovunque**: Qualsiasi PC con Claude Desktop
✅ **Dati centralizzati**: Tutto sul VPS
✅ **Bassa latenza**: Server e database sullo stesso VPS
✅ **Sicuro**: SSH tunnel criptato
✅ **Sempre attivo**: Systemd auto-restart
✅ **Scalabile**: Facile aggiungere altri tools MCP

---

## 🚀 Uso Quotidiano

Una volta configurato, **non devi fare NULLA**:

1. Apri Claude Desktop
2. Scrivi richieste in linguaggio naturale
3. Claude usa automaticamente MCP tools per:
   - Cercare riunioni
   - Leggere trascrizioni
   - Estrarre action items
   - Trovare decisioni

**Esempio conversazione**:

> **Tu**: Quali sono le azioni assegnate a Marco?
>
> **Claude**: *[Usa tool `get_action_items` con owner="Marco"]*
> Marco ha 3 azioni da completare:
> 1. Contattare cliente Rossi entro lunedì
> 2. Pianificare installazione con Lorandi
> 3. Preparare report budget Q1

---

## 📱 Multi-Dispositivo

Puoi usare **lo stesso MCP server da più dispositivi**:

- 💻 **PC ufficio**: Configura SSH key
- 🏠 **PC casa**: Configura SSH key
- 💼 **Laptop**: Configura SSH key

Ogni dispositivo ha la sua chiave SSH ma tutti accedono allo stesso server!

---

## 🔄 Aggiornamenti

Per aggiornare MCP Server sul VPS:

```bash
# 1. SSH nel server
ssh sai@srv778971.hstgr.cloud

# 2. Pull modifiche
cd ~/MCPClaude
git pull

# 3. Aggiorna file
sudo cp mcp_server_meetings_vps.py /opt/mcp_server_meetings/mcp_server_meetings.py

# 4. Riavvia servizio
sudo systemctl restart mcp-server-meetings

# 5. Verifica
sudo systemctl status mcp-server-meetings
```

---

## 📧 Support

Se hai problemi, controlla:

1. **Log MCP Server**: `tail -f /var/log/mcp_server_meetings.log`
2. **Status servizio**: `sudo systemctl status mcp-server-meetings`
3. **Test SSH**: `ssh -i ~/.ssh/key sai@srv778971.hstgr.cloud echo OK`
4. **Test Python**: `python3 /opt/mcp_server_meetings/mcp_server_meetings.py`
