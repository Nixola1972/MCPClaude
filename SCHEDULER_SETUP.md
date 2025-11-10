# ⏰ Scheduler Setup - Automatic Workflow Execution

## 🎯 Obiettivo

Configurare l'esecuzione automatica del workflow ogni notte (o orario personalizzato) per processare nuovi file audio da Nextcloud.

**Scenario:**
- Carichi file audio in Nextcloud durante il giorno
- Ogni notte alle 00:00 (configur bile) il workflow si avvia automaticamente
- Al mattino trovi tutte le trascrizioni e riassunti pronti!

---

## 🚀 Installazione Rapida

### Opzione 1: Script Automatico (Consigliato) ⭐

```bash
# Sul tuo server
cd ~/MCPClaude

# Rendi eseguibile
chmod +x setup_scheduler.sh

# Esegui setup
./setup_scheduler.sh

# Segui le istruzioni interattive:
# 1. Conferma paths
# 2. Scegli orario (es. 00:00)
# 3. Scegli metodo (Cron o Systemd)
```

**Output atteso:**
```
============================================================
🕐 SCHEDULER SETUP - Audio Processing Workflow
============================================================

📋 Configuration:
  Workflow: /home/sai/MCPClaude/audio_processing_workflow_v2.py
  Python: /home/sai/whisper_env/bin/python3
  Log: /home/sai/logs/workflow.log

Orario esecuzione (HH:MM, default 00:00): 00:00

⏰ Pianificato: Ogni giorno alle 0:0

Scegli metodo di scheduling:
  1) Cron (semplice, standard)
  2) Systemd Timer (avanzato, più controllo)

Scelta (1 o 2): 1

✅ Cron job creato!
```

---

## ⚙️ Configurazione Manuale

### Metodo 1: Cron (Semplice)

```bash
# Apri crontab
crontab -e

# Aggiungi questa riga per esecuzione alle 00:00
0 0 * * * cd ~/MCPClaude && ~/whisper_env/bin/python3 audio_processing_workflow_v2.py >> ~/logs/workflow.log 2>&1

# Salva e esci (Ctrl+X, poi Y, poi Enter)
```

**Formato cron:**
```
# ┌───────────── minuto (0 - 59)
# │ ┌─────────── ora (0 - 23)
# │ │ ┌───────── giorno del mese (1 - 31)
# │ │ │ ┌─────── mese (1 - 12)
# │ │ │ │ ┌───── giorno della settimana (0 - 6, Domenica=0)
# │ │ │ │ │
# * * * * * comando da eseguire
```

**Esempi:**
```bash
# Ogni giorno alle 00:00 (mezzanotte)
0 0 * * * [comando]

# Ogni giorno alle 02:00
0 2 * * * [comando]

# Ogni giorno alle 23:30
30 23 * * * [comando]

# Ogni Lunedì alle 08:00
0 8 * * 1 [comando]

# Ogni ora
0 * * * * [comando]
```

---

### Metodo 2: Systemd Timer (Avanzato)

**1. Crea Service File:**

```bash
sudo nano /etc/systemd/system/audio-workflow.service
```

Contenuto:
```ini
[Unit]
Description=Audio Processing Workflow
After=network.target

[Service]
Type=oneshot
User=sai
WorkingDirectory=/home/sai/MCPClaude
Environment="PATH=/home/sai/whisper_env/bin:/usr/bin:/bin"
ExecStart=/home/sai/whisper_env/bin/python3 audio_processing_workflow_v2.py
StandardOutput=append:/home/sai/logs/workflow.log
StandardError=append:/home/sai/logs/workflow.log

[Install]
WantedBy=multi-user.target
```

**2. Crea Timer File:**

```bash
sudo nano /etc/systemd/system/audio-workflow.timer
```

Contenuto:
```ini
[Unit]
Description=Audio Processing Workflow Timer
Requires=audio-workflow.service

[Timer]
OnCalendar=*-*-* 00:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**`OnCalendar` Syntax Examples:**
```ini
# Ogni giorno alle 00:00
OnCalendar=*-*-* 00:00:00

# Ogni giorno alle 02:30
OnCalendar=*-*-* 02:30:00

# Ogni Lunedì alle 08:00
OnCalendar=Mon *-*-* 08:00:00

# Ogni ora
OnCalendar=hourly

# Ogni 15 minuti
OnCalendar=*:0/15
```

**3. Abilita e Avvia:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Abilita timer (avvio automatico al boot)
sudo systemctl enable audio-workflow.timer

# Avvia timer
sudo systemctl start audio-workflow.timer

# Verifica status
sudo systemctl status audio-workflow.timer

# Lista tutti i timer
sudo systemctl list-timers
```

---

## 📊 Verifica Installazione

### Cron

```bash
# Verifica cron job installato
crontab -l

# View cron logs
grep CRON /var/log/syslog | tail -20

# Test manuale
cd ~/MCPClaude && ~/whisper_env/bin/python3 audio_processing_workflow_v2.py
```

### Systemd

```bash
# Status timer
sudo systemctl status audio-workflow.timer

# Lista prossime esecuzioni
sudo systemctl list-timers audio-workflow.timer

# Test manuale
sudo systemctl start audio-workflow.service

# View logs
sudo journalctl -u audio-workflow.service -f

# Logs workflow
tail -f ~/logs/workflow.log
```

---

## 📄 Gestione Logs

### Rotazione Logs

Evita che i log diventino troppo grandi:

```bash
# Crea logrotate config
sudo nano /etc/logrotate.d/audio-workflow
```

Contenuto:
```
/home/sai/logs/workflow.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 sai sai
}
```

### View Logs

```bash
# Ultimi log
tail -50 ~/logs/workflow.log

# Live logs
tail -f ~/logs/workflow.log

# Cerca errori
grep -i error ~/logs/workflow.log

# Logs di oggi
grep "$(date +%Y-%m-%d)" ~/logs/workflow.log
```

---

## 🔧 Troubleshooting

### Cron non esegue

**Problema:** Cron job non si avvia

**Verifica:**
```bash
# 1. Controlla se cron service è attivo
sudo systemctl status cron

# 2. Verifica cron job
crontab -l

# 3. Controlla logs
grep CRON /var/log/syslog

# 4. Test manuale
cd ~/MCPClaude && ~/whisper_env/bin/python3 audio_processing_workflow_v2.py
```

**Soluzioni comuni:**
- Assicurati path assoluti (no `~` in cron)
- Verifica permessi file
- Controlla che cron service sia running

---

### Systemd timer non attivo

**Problema:** Timer non parte

**Verifica:**
```bash
# Status
sudo systemctl status audio-workflow.timer

# Enable se disabilitato
sudo systemctl enable audio-workflow.timer
sudo systemctl start audio-workflow.timer
```

---

### Script va in errore

**Problema:** Workflow fallisce durante esecuzione

**Debug:**
```bash
# 1. View complete logs
tail -100 ~/logs/workflow.log

# 2. Test manuale
cd ~/MCPClaude
python3 audio_processing_workflow_v2.py

# 3. Verifica dipendenze
source ~/whisper_env/bin/activate
pip list | grep -E "faster-whisper|psycopg2|qdrant"

# 4. Verifica connessioni
python3 -c "import psycopg2; print('PostgreSQL OK')"
python3 -c "from qdrant_client import QdrantClient; print('Qdrant OK')"
```

---

### Nessun file da processare

**Problema:** "No new files to process"

**Verifica:**
```bash
# 1. Controlla Nextcloud cartella Audio_Riunioni
# Deve contenere file nuovi

# 2. Controlla hash in database
python3 -c "
import psycopg2
conn = psycopg2.connect(...)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM sources WHERE file_hash IS NOT NULL')
print(f'Hash in DB: {cur.fetchone()[0]}')
"
```

---

## 🎯 Best Practices

### 1. Notifiche Email (Opzionale)

Ricevi email quando workflow completa:

```bash
# Installa mailutils
sudo apt install mailutils

# Modifica cron per inviare email
0 0 * * * cd ~/MCPClaude && ~/whisper_env/bin/python3 audio_processing_workflow_v2.py >> ~/logs/workflow.log 2>&1 && echo "Workflow completato!" | mail -s "Audio Processing" tua@email.com
```

### 2. Telegram Bot (Opzionale)

Notifiche su Telegram:

```python
# Aggiungi a fine workflow
import requests

def send_telegram(message):
    bot_token = "TUO_BOT_TOKEN"
    chat_id = "TUO_CHAT_ID"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message})

# Chiama dopo processing
send_telegram("✅ Workflow completato! 3 file processati")
```

### 3. Retry su Fallimento

Riprova se fallisce:

```bash
# Cron con retry
0 0 * * * for i in 1 2 3; do cd ~/MCPClaude && ~/whisper_env/bin/python3 audio_processing_workflow_v2.py && break || sleep 300; done
```

### 4. Backup Logs

```bash
# Backup logs ogni settimana
0 0 * * 0 tar -czf ~/logs/backup/workflow_$(date +\%Y\%m\%d).tar.gz ~/logs/workflow.log
```

---

## 📅 Esempi Scheduling Comuni

### Ogni Notte alle 00:00
```bash
# Cron
0 0 * * * [comando]

# Systemd
OnCalendar=*-*-* 00:00:00
```

### Ogni Notte alle 02:00 (evita mezzanotte)
```bash
# Cron
0 2 * * * [comando]

# Systemd
OnCalendar=*-*-* 02:00:00
```

### Solo nei giorni lavorativi (Lun-Ven)
```bash
# Cron
0 0 * * 1-5 [comando]

# Systemd
OnCalendar=Mon,Tue,Wed,Thu,Fri *-*-* 00:00:00
```

### Due volte al giorno (00:00 e 12:00)
```bash
# Cron
0 0,12 * * * [comando]

# Systemd (crea 2 timer separati)
```

---

## ✅ Checklist Post-Installazione

- [ ] Scheduler configurato (cron o systemd)
- [ ] Test manuale eseguito con successo
- [ ] Log directory creata (`~/logs`)
- [ ] Prossima esecuzione verificata (`crontab -l` o `systemctl list-timers`)
- [ ] Logs monitorabili (`tail -f ~/logs/workflow.log`)
- [ ] Path corretti nel comando
- [ ] Permessi file corretti
- [ ] (Opzionale) Notifiche configurate
- [ ] (Opzionale) Log rotation configurato

---

## 🚀 Prossimi Step

Dopo scheduler configurato:

1. ✅ **MCP Server** - Accedi da Claude Desktop
2. ✅ **Streamlit Dashboard** - Visualizza nel browser
3. ✅ **Scheduler** - Automazione notturna

**Sistema completo e funzionante!** 🎉

---

**Versione:** 1.0
**Metodi:** Cron + Systemd
**Default Schedule:** 00:00 daily
**Status:** Production Ready ✅
