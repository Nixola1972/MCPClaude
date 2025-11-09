# AGGIORNAMENTO WORKFLOW - Nuove Funzionalità

## 🆕 Modifiche Applicate

### 1. Fix Bug UUID Qdrant (CRITICO)
- **Problema:** Ogni run sovascriveva i dati precedenti
- **Soluzione:** Ora usa UUID univoci invece di ID sequenziali
- **Impatto:** I dati si accumulano invece di sovrascriversi

### 2. Spostamento Automatico File Processati
- **Nuova feature:** Dopo il processing, i file vengono spostati in cartella `Audio_Processati` su Nextcloud
- **Beneficio:** Evita di riprocessare sempre gli stessi file
- **Funzionamento:**
  - Crea automaticamente cartella `Audio_Processati` su Nextcloud
  - Sposta file da `Audio_Riunioni` a `Audio_Processati` dopo successo
  - Download controlla entrambe le cartelle e salta file già processati

### 3. Download Intelligente
- **Miglioria:** Controlla se file già in `Audio_Processati` prima di scaricare
- **Beneficio:** Risparmia banda e tempo
- **Output:** Mostra quanti file saltati e quanti scaricati

---

## 📝 Modifiche al Codice

### Aggiunte alla Configurazione
```python
PROCESSED_FOLDER = "/remote.php/dav/files/{user}/Audio_Processati/"
```

### Nuove Funzioni

#### `download_new_audio()` - Modificata
- Controlla lista file in `Audio_Processati`
- Salta file già processati
- Scarica solo file nuovi

#### `move_processed_files(transcriptions)` - NUOVA
- Crea cartella `Audio_Processati` se non esiste
- Sposta file processati da `Audio_Riunioni` a `Audio_Processati`
- Gestisce errori senza bloccare il workflow

### Workflow Aggiornato
```
Step 1: Download audio (solo nuovi) ✅
Step 2: Trascrizione Whisper         ✅
Step 3: Entity extraction            ✅
Step 4: Embeddings                   ✅
Step 5: Upload PostgreSQL             ✅
Step 6: Upload Qdrant                 ✅
Step 7: Sposta file processati        ✅ NUOVO!
```

---

## 🚀 Come Aggiornare

### OPZIONE A: Download da Git (consigliato)
```bash
cd ~/
git clone https://github.com/Nixola1972/MCPClaude.git temp_update
cp ~/audio_processing_workflow.py ~/audio_processing_workflow.py.backup
cp temp_update/audio_processing_workflow.py ~/audio_processing_workflow.py
rm -rf temp_update

# Verifica
diff ~/audio_processing_workflow.py.backup ~/audio_processing_workflow.py
```

### OPZIONE B: Copia Manuale
Incolla il codice completo nel file `~/audio_processing_workflow.py`

### OPZIONE C: Script Automatico
```bash
# Crea script aggiornamento
cat > ~/update_workflow.sh << 'SCRIPT_EOF'
#!/bin/bash

echo "🔄 AGGIORNAMENTO WORKFLOW"
echo "========================="

# Backup
echo "📦 Backup file esistente..."
cp ~/audio_processing_workflow.py ~/audio_processing_workflow.py.backup_$(date +%Y%m%d_%H%M%S)

# Scarica nuova versione
echo "⬇️  Download nuova versione..."
curl -o ~/audio_processing_workflow.py https://raw.githubusercontent.com/Nixola1972/MCPClaude/claude/analyze-server-rhapsody-011CUvAgxegbjcrF6JavPUgK/audio_processing_workflow.py

echo "✅ Aggiornamento completato!"
echo ""
echo "Prossimi step:"
echo "1. Verifica configurazione (credenziali, host, ecc.)"
echo "2. (Opzionale) Reset Qdrant: python3 ~/reset_qdrant_collection.py"
echo "3. Test workflow: python3 ~/audio_processing_workflow.py"
SCRIPT_EOF

chmod +x ~/update_workflow.sh
~/update_workflow.sh
```

---

## ✅ Verifica Post-Aggiornamento

### 1. Controlla che il file sia aggiornato
```bash
grep -n "PROCESSED_FOLDER" ~/audio_processing_workflow.py
grep -n "move_processed_files" ~/audio_processing_workflow.py
grep -n "uuid.uuid4()" ~/audio_processing_workflow.py
```

Dovresti vedere:
- Riga con `PROCESSED_FOLDER = "/remote.php/dav/files/{user}/Audio_Processati/"`
- Funzione `move_processed_files` definita
- `point_id = str(uuid.uuid4())` nella funzione upload_to_qdrant

### 2. (Opzionale) Reset Qdrant
Se vuoi ripartire pulito senza dati vecchi sovrascritti:
```bash
source ~/whisper_env/bin/activate
python3 ~/reset_qdrant_collection.py
```

### 3. Test Workflow
```bash
source ~/whisper_env/bin/activate
python3 ~/audio_processing_workflow.py
```

Output atteso:
```
📥 Step 1: Download audio da Nextcloud...
  ℹ️  Trovati X file già processati (verranno saltati)
  ⬇️  Downloading: NuovoFile.m4a
✅ Downloaded 1 new files (saltati X già processati)

[... processing ...]

📦 Step 7: Sposta 1 file processati su Nextcloud...
  ✅ Creata cartella: /remote.php/dav/files/admin/Audio_Processati/
  ✅ Spostato: NuovoFile.m4a
✅ Spostati 1/1 file in Audio_Processati
```

### 4. Verifica su Nextcloud
Apri app Nextcloud e controlla:
- ✅ Nuova cartella `Audio_Processati` creata
- ✅ File processati spostati dentro
- ✅ Cartella `Audio_Riunioni` vuota (o con solo nuovi file)

### 5. Query Dati
```bash
source ~/whisper_env/bin/activate
python3 ~/query_all_data.py
```

Verifica che:
- Numero di vectors in Qdrant aumenta ad ogni run (non rimane sempre 1!)
- IDs dei points sono UUID (non più 0,1,2...)

---

## 🎯 Workflow Completo Futuro

### Ogni Giorno (automatico con cron)
1. ⏰ 23:00 - Cron lancia workflow
2. 📥 Scarica nuovi audio da Nextcloud (salta già processati)
3. 🎤 Trascrizione GPU Whisper
4. 🧠 Entity extraction Ollama
5. 📊 Salva PostgreSQL + Qdrant
6. 📦 Sposta file in `Audio_Processati`

### Prossimo Run
1. Trova cartella `Audio_Riunioni` vuota o solo con nuovi file
2. Salta tutti i file già in `Audio_Processati`
3. Processa solo file nuovi
4. Accumula dati (non sovrascrive!)

---

## 🐛 Troubleshooting

### Errore "move_processed_files not found"
File non aggiornato. Riprova OPZIONE A o B sopra.

### File vengono ancora riprocessati
Verifica che:
```bash
grep "processed_files = set()" ~/audio_processing_workflow.py
```
Deve esistere nella funzione download_new_audio.

### Cartella Processati non creata
Normale al primo run. Verrà creata automaticamente.

---

## 📊 Statistiche Risparmiate

Con 8h audio/giorno, 20 giorni/mese:

**PRIMA (con bug):**
- 160 trascrizioni al mese
- Ma solo 1 vector salvato (sovrascritto!)
- Database inutile

**DOPO (con fix):**
- 160 trascrizioni al mese
- ~1600 vector chunks accumulati
- Knowledge graph completo e interrogabile

**Risparmio riprocessing:**
- Senza spostamento: 160 file riprocessati ogni notte = 4800 trascrizioni/mese inutili
- Con spostamento: 0 riprocessing = 30x più efficiente

---

**Data:** 2025-11-09
**Branch:** claude/analyze-server-rhapsody-011CUvAgxegbjcrF6JavPUgK
**Commit:** 9b64dc7 + nuovo commit in arrivo
