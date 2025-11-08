# 🚀 UNIFIED MEMORY SYSTEM - Guida Setup Completa

## 📋 Indice
1. [Architettura Sistema](#architettura)
2. [Analisi Costi](#costi)
3. [Prerequisiti](#prerequisiti)
4. [Setup Web Server](#setup-web-server)
5. [Setup PC Locale (GPU)](#setup-pc-locale)
6. [Setup Mobile](#setup-mobile)
7. [Test e Verifica](#test)
8. [Manutenzione](#manutenzione)

---

## 🏗️ Architettura Sistema <a name="architettura"></a>

### Overview
```
📱 MOBILE (Registrazione)
    ↓ Auto-sync via Nextcloud
🌐 WEB SERVER (Storage + API)
    ├─ PostgreSQL (dati strutturati)
    ├─ Qdrant (vector embeddings)
    ├─ Nextcloud (file sync)
    └─ Memory MCP API (accesso Claude)
    ↓ Download + Processing
💻 PC LOCALE (2x RTX 3060)
    ├─ Whisper Large-v3 (trascrizione GPU)
    ├─ Ollama (embeddings + entity extraction)
    └─ Workflow automatizzato (cron notturno)
    ↓ Upload risultati
🌐 WEB SERVER (Storage centralizzato)
```

### Flusso Dati
1. **Registrazione Mobile** → Nextcloud (auto-upload)
2. **PC Locale** scarica nuovi audio (notte)
3. **Whisper GPU** trascrizione batch
4. **Ollama** entity extraction + embeddings
5. **Upload** a PostgreSQL + Qdrant
6. **Accesso** via Claude Desktop (MCP)

---

## 💰 Analisi Costi <a name="costi"></a>

### Confronto Cloud vs Self-Hosted

#### ☁️ Soluzione Cloud (EVITATA)
```
Whisper API (OpenAI):
  160h audio/mese × 60 min × $0.006 = $576/mese

Embeddings API (OpenAI):
  ~500k tokens/mese × $0.02/1M = $10/mese

Vector DB (Pinecone):
  $70/mese (piano base)

PostgreSQL Cloud:
  $20/mese (DigitalOcean/Heroku)

TOTALE CLOUD: $676/mese = €8.112/anno ❌
```

#### 🏠 Soluzione Self-Hosted (IMPLEMENTATA)

```
Hardware (già disponibile):
  ✅ 2x RTX 3060 12GB
  ✅ Server web con Docker
  ✅ PC Linux

Software (tutto open-source):
  ✅ Whisper (gratis)
  ✅ Ollama (gratis)
  ✅ PostgreSQL (gratis)
  ✅ Qdrant (gratis)
  ✅ Nextcloud (gratis)

Costi ricorrenti:
  Energia elettrica:
    - 2x RTX 3060: 340W
    - Processing: ~5h/notte
    - 340W × 5h × 30 giorni = 51 kWh/mese
    - 51 kWh × €0.30 = €15.30/mese

  Server web (se non già disponibile):
    - VPS base: €5-10/mese
    - Oppure €0 se usi server esistente

TOTALE SELF-HOSTED: €15-25/mese = €180-300/anno ✅

RISPARMIO: €7.800/anno! 💰
```

### ROI (Return on Investment)
```
Investimento iniziale: €0 (hardware già disponibile)
Risparmio mensile: €650
Break-even: Immediato
Risparmio 1 anno: €7.800
Risparmio 3 anni: €23.400
```

---

## ✅ Prerequisiti <a name="prerequisiti"></a>

### Web Server
- [x] Docker + docker-compose installato
- [x] Porte disponibili: 5432 (PostgreSQL), 6333 (Qdrant), 8080 (Nextcloud), 8000 (API)
- [x] Spazio disco: ~20GB per PostgreSQL + Qdrant + Nextcloud
- [x] RAM: minimo 4GB

### PC Locale (GPU)
- [x] 2x NVIDIA RTX 3060 12GB
- [x] Driver NVIDIA 535+ installato
- [x] Docker con nvidia-docker runtime
- [x] Python 3.11+
- [x] Spazio disco: ~50GB per audio + modelli Whisper

### Mobile
- [x] Android 8+ o iOS 12+
- [x] App Nextcloud installata
- [x] Connessione internet

---

## 🌐 Setup Web Server <a name="setup-web-server"></a>

### Step 1: Preparazione File

Sul tuo server web, crea directory:
```bash
mkdir -p ~/unified-memory-stack
cd ~/unified-memory-stack
```

Copia i file dal repository:
```bash
# docker-compose-memory-stack.yml
# init-db.sql
```

### Step 2: Configurazione Environment

Crea file `.env`:
```bash
nano .env
```

Contenuto:
```env
# PostgreSQL
POSTGRES_PASSWORD=TuaPasswordSicura123!

# Nextcloud Database
NEXTCLOUD_DB_PASSWORD=NextcloudDBPass456!
NEXTCLOUD_DB_ROOT_PASSWORD=RootPass789!

# Nextcloud Admin
NEXTCLOUD_ADMIN_PASSWORD=AdminPass000!
NEXTCLOUD_DOMAIN=your-domain.com  # o IP pubblico

# pgAdmin (opzionale)
PGADMIN_PASSWORD=PgAdminPass111!
```

**IMPORTANTE**: Cambia tutte le password!

### Step 3: Avvio Stack

```bash
# Avvia tutti i servizi
docker-compose -f docker-compose-memory-stack.yml up -d

# Verifica che siano partiti
docker-compose -f docker-compose-memory-stack.yml ps

# Dovresti vedere:
# ✅ memory_postgres     - healthy
# ✅ memory_qdrant       - healthy
# ✅ nextcloud           - healthy
# ✅ nextcloud_mariadb   - healthy
# ✅ memory_mcp_api      - running
```

### Step 4: Verifica Database

```bash
# Connetti a PostgreSQL
docker exec -it memory_postgres psql -U memory_user -d unified_memory

# Esegui query test
SELECT * FROM database_stats;

# Output atteso:
# total_entities | total_observations | total_relations | total_sources
# --------------------------------------------------------------
#       3        |          1          |        1        |      2

# Esci
\q
```

### Step 5: Verifica Qdrant

```bash
# Test API Qdrant
curl http://localhost:6333/

# Output atteso: {"title":"qdrant - vector search engine","version":"1.x.x"}
```

### Step 6: Configura Nextcloud

1. Apri browser: `http://your-server-ip:8080`
2. Login con credenziali admin (da `.env`)
3. Crea cartella `Audio_Riunioni`
4. Vai in Impostazioni → Condivisione esterna
5. Genera App Password per sync mobile

---

## 💻 Setup PC Locale (GPU) <a name="setup-pc-locale"></a>

### Step 1: Riavvia Ollama

Sul tuo PC locale:
```bash
# Riavvia container Ollama
docker start ollama

# Verifica
docker ps | grep ollama

# Pull modelli necessari
docker exec -it ollama ollama pull llama3.2:3b
docker exec -it ollama ollama pull nomic-embed-text

# Test
docker exec -it ollama ollama run llama3.2:3b "Ciao, funzioni?"
```

### Step 2: Installa Dipendenze Python

```bash
# Crea ambiente virtuale
cd ~
python3 -m venv whisper_env
source whisper_env/bin/activate

# Installa PyTorch con CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Installa Whisper
pip install openai-whisper

# Installa altre dipendenze
pip install psycopg2-binary qdrant-client webdav3-client requests tqdm

# Test GPU
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.device_count()}')"
# Output atteso: CUDA: True, GPU: 2
```

### Step 3: Configurazione Script Workflow

```bash
# Copia script workflow
cp audio_processing_workflow.py ~/whisper_env/

# Modifica configurazione
nano ~/whisper_env/audio_processing_workflow.py
```

Aggiorna queste righe:
```python
NEXTCLOUD_URL = "http://your-server-ip:8080/nextcloud"
NEXTCLOUD_USER = "admin"  # o il tuo user
NEXTCLOUD_PASS = "la_tua_app_password"

POSTGRES_HOST = "your-server-ip"
POSTGRES_PASS = "TuaPasswordPostgreSQL"

QDRANT_HOST = "your-server-ip"
```

### Step 4: Test Manuale Workflow

```bash
# Attiva ambiente
source ~/whisper_env/bin/activate

# Test workflow (crea file audio fittizio prima)
mkdir -p ~/audio_queue
# ... copia un file audio di test in ~/audio_queue

# Esegui
cd ~/whisper_env
python3 audio_processing_workflow.py

# Output atteso:
# 🚀 AUDIO PROCESSING WORKFLOW
# 📥 Step 1: Download audio...
# 🎤 Step 2: Trascrizione...
# 🧠 Step 3: Entity extraction...
# ...
# ✅ WORKFLOW COMPLETATO
```

### Step 5: Setup Cron Job (Processing Notturno)

```bash
# Modifica crontab
crontab -e

# Aggiungi questa riga (esecuzione alle 23:00 ogni notte)
0 23 * * * /home/sai/whisper_env/bin/python3 /home/sai/whisper_env/audio_processing_workflow.py >> /home/sai/whisper_logs/workflow_$(date +\%Y\%m\%d).log 2>&1

# Crea directory log
mkdir -p ~/whisper_logs

# Verifica cron
crontab -l
```

**Workflow automatico**:
- Alle 23:00 ogni notte
- Scarica nuovi audio da Nextcloud
- Trascrizione Whisper (4-5 ore)
- Entity extraction
- Upload a PostgreSQL + Qdrant
- Logs in `~/whisper_logs/`

---

## 📱 Setup Mobile <a name="setup-mobile"></a>

### Android

1. **Installa Nextcloud** da Play Store
2. **Connetti all'account**:
   - Server: `http://your-server-ip:8080`
   - Username: `admin` (o tuo user)
   - Password: usa App Password generata

3. **Configura Auto-Upload**:
   - Impostazioni → Auto upload
   - Abilita "Auto upload"
   - Cartella locale: seleziona dove salvi le registrazioni
   - Cartella remota: `/Audio_Riunioni`
   - Solo WiFi: consigliato (per non consumare dati)

4. **App Registrazione Consigliata**:
   - **RecForge II** (gratis, alta qualità)
   - Imposta output: WAV 48kHz 16bit
   - Cartella output: quella configurata in Nextcloud auto-upload

### iOS

1. **Installa Nextcloud** da App Store
2. Configurazione identica ad Android
3. **App Registrazione**:
   - **Just Press Record** (integrazione iCloud)
   - Imposta export automatico alla cartella Nextcloud

### Workflow Mobile
```
1. Riunione → Premi record
2. Fine riunione → Stop → Salva
3. Nextcloud auto-upload (background)
4. File arriva su server
5. Notte: PC scarica e processa
6. Mattina: trascrizione disponibile!
```

---

## 🧪 Test e Verifica <a name="test"></a>

### Test 1: Registrazione Mobile → Server

```bash
# Sul server, monitora cartella Nextcloud
docker exec -it nextcloud ls -lh /var/www/html/data/admin/files/Audio_Riunioni/

# Registra 30 secondi audio dal mobile
# Attendi sync
# Verifica che il file appaia
```

### Test 2: Trascrizione GPU

```bash
# Sul PC locale
source ~/whisper_env/bin/activate

# Test Whisper su file singolo
python3 << EOF
import whisper
model = whisper.load_model("base", device="cuda")
result = model.transcribe("/path/to/test_audio.wav", language="it")
print(result['text'])
EOF
```

### Test 3: Database Query

```bash
# Sul server
docker exec -it memory_postgres psql -U memory_user -d unified_memory

# Query entities
SELECT * FROM entities LIMIT 10;

# Query observations
SELECT e.name, o.content, s.source_type
FROM observations o
JOIN entities e ON o.entity_id = e.id
JOIN sources s ON o.source_id = s.id
ORDER BY o.created_at DESC
LIMIT 20;

# Consensus score
SELECT * FROM entity_consensus ORDER BY consensus_score DESC LIMIT 10;
```

### Test 4: Semantic Search (Qdrant)

```bash
# Test API Qdrant
curl -X POST http://your-server-ip:6333/collections/unified_memory_audio/points/search \
  -H 'Content-Type: application/json' \
  -d '{
    "vector": [0.1, 0.2, ...],  # embedding di test
    "limit": 5
  }'
```

---

## 🔧 Manutenzione <a name="manutenzione"></a>

### Backup Database (Settimanale)

```bash
# Script backup PostgreSQL
cat > ~/backup_postgres.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/backups/postgres
mkdir -p $BACKUP_DIR

docker exec memory_postgres pg_dump -U memory_user unified_memory | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Mantieni solo ultimi 30 giorni
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

echo "✅ Backup completato: $BACKUP_DIR/backup_$DATE.sql.gz"
EOF

chmod +x ~/backup_postgres.sh

# Aggiungi a cron (ogni domenica alle 3:00)
crontab -e
# 0 3 * * 0 /home/sai/backup_postgres.sh
```

### Backup Qdrant

```bash
# Qdrant salva automaticamente su volume Docker
# Per backup manuale:
docker run --rm -v qdrant_storage:/data -v ~/backups/qdrant:/backup alpine tar czf /backup/qdrant_$(date +%Y%m%d).tar.gz /data
```

### Pulizia Audio Processati (Mensile)

```bash
# Elimina audio processati più vecchi di 90 giorni
find ~/audio_processed -name "*.wav" -mtime +90 -delete
find ~/audio_processed -name "*.m4a" -mtime +90 -delete

# Mantieni trascrizioni JSON (leggere)
```

### Monitoring

```bash
# Check spazio disco
df -h

# Check RAM container
docker stats --no-stream

# Check GPU utilizzo
nvidia-smi

# Check logs workflow
tail -f ~/whisper_logs/workflow_$(date +%Y%m%d).log
```

### Aggiornamenti

```bash
# Aggiorna immagini Docker (mensile)
cd ~/unified-memory-stack
docker-compose pull
docker-compose up -d

# Aggiorna Whisper
source ~/whisper_env/bin/activate
pip install --upgrade openai-whisper

# Aggiorna Ollama models
docker exec -it ollama ollama pull llama3.2:3b
docker exec -it ollama ollama pull nomic-embed-text
```

---

## 📊 Statistiche Previste

Con 160h audio/mese (8h × 20 giorni):

```
Storage PostgreSQL:
  - Entities: ~500-1000 (persone, org, progetti)
  - Observations: ~10.000-20.000
  - Relations: ~2.000-5.000
  - Dimensione DB: ~500MB-1GB

Storage Qdrant:
  - Vectors: ~100.000-200.000 (chunks da 500 char)
  - Dimensione: ~1-2GB

Storage Audio:
  - Audio originali (90 giorni): ~50GB
  - Trascrizioni JSON: ~500MB

Processing Time:
  - Trascrizione (large-v3): ~4-5 ore/notte
  - Entity extraction: ~30-60 minuti
  - Embeddings: ~30-60 minuti
  - Upload DB: ~10 minuti

TOTALE PROCESSING: ~5-6 ore/notte
```

---

## 🎯 Prossimi Passi

1. ✅ Deploy stack web server
2. ✅ Setup PC locale workflow
3. ✅ Configura mobile sync
4. ⬜ Test completo end-to-end
5. ⬜ Integrazione Email MCP
6. ⬜ Memory MCP v2.0 API
7. ⬜ Dashboard visualizzazione (opzionale)

---

## 🆘 Troubleshooting

### Problema: Whisper lento su GPU

```bash
# Verifica GPU usage durante trascrizione
nvidia-smi -l 1

# Se GPU usage < 80%, controlla:
# 1. CUDA version compatibile
# 2. PyTorch installato con GPU support
python3 -c "import torch; print(torch.version.cuda)"
```

### Problema: Nextcloud sync non funziona

```bash
# Check logs Nextcloud
docker logs nextcloud --tail 100

# Check connettività mobile
# Prova accesso web da browser mobile
```

### Problema: PostgreSQL out of space

```bash
# Check dimensione DB
docker exec memory_postgres du -sh /var/lib/postgresql/data

# Aumenta volume Docker o pulisci dati vecchi
```

---

## 📚 Risorse

- [Whisper Docs](https://github.com/openai/whisper)
- [Ollama Docs](https://ollama.ai/docs)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Qdrant Docs](https://qdrant.tech/documentation/)
- [Nextcloud Docs](https://docs.nextcloud.com/)

---

**Versione**: 1.0
**Data**: 2025-01-08
**Autore**: Claude + Sai
**Licenza**: MIT
