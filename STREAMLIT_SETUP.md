# 📊 Streamlit Dashboard Setup

## 🎯 Cos'è lo Streamlit Dashboard?

Web UI per visualizzare, cercare e caricare file audio delle riunioni!

**Funzionalità:**
- 🏠 Homepage con statistiche e grafici
- 📋 Elenco tutte le riunioni
- 🔍 Ricerca semantica
- 📤 Upload audio drag & drop
- ⚙️ Configurazione scheduler
- 📄 Visualizzazione trascrizioni complete

---

## 🚀 Installazione

### Step 1: Installa dipendenze

```bash
# Sul tuo server
cd ~/whisper_env
source bin/activate

# Installa Streamlit e dipendenze visualizzazione
pip install streamlit plotly pandas

# Verifica installazione
streamlit --version
```

### Step 2: Test locale

```bash
# Avvia dashboard
cd ~/MCPClaude
streamlit run streamlit_dashboard.py

# Output atteso:
#   Local URL: http://localhost:8501
#   Network URL: http://192.168.x.x:8501
```

### Step 3: Accesso remoto

Se vuoi accedere da un altro computer sulla rete:

```bash
# Opzione A: SSH Tunnel (sicuro)
# Sul tuo computer locale:
ssh -L 8501:localhost:8501 sai@srv778971.hstgr.cloud

# Poi apri browser: http://localhost:8501


# Opzione B: Expose su rete (meno sicuro)
streamlit run streamlit_dashboard.py --server.address 0.0.0.0 --server.port 8501

# Apri browser: http://srv778971.hstgr.cloud:8501
```

---

## 📱 Pagine Disponibili

### 🏠 **Home**
- Statistiche totali (n° riunioni, durata, parole)
- Grafico riunioni per settimana
- Ultime 5 riunioni con TL;DR

### 📋 **Riunioni**
- Lista completa riunioni
- Filtri per nome e data
- Visualizzazione card con metriche qualità
- Accesso dettaglio riunione

### 🎙️ **Dettaglio Riunione**
- Metadata completi (data, durata, parole, qualità)
- TL;DR e riassunto dettagliato
- Partecipanti, argomenti, decisioni
- Action items strutturati
- Numeri chiave
- Trascrizione completa (espandibile)
- Download trascrizione TXT

### 🔍 **Ricerca**
- Input query linguaggio naturale
- Ricerca semantica in Qdrant
- Risultati con punteggio rilevanza
- Preview TL;DR e argomenti
- Accesso rapido al dettaglio

### 📤 **Upload**
- Drag & drop file audio
- Formati supportati: WAV, M4A, MP3, FLAC
- Preview info file
- Processing immediato (in sviluppo)

### ⚙️ **Impostazioni**
- Configurazione scheduler automatico
- Orario personalizzabile
- Test connessione database
- Test connessione Qdrant
- Statistiche sistema

---

## 🎨 Screenshots

### Home Dashboard
```
┌─────────────────────────────────────────────────────┐
│ 🎙️ Meetings Dashboard                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📊 42        ⏱️ 85.5h      📝 12,450      📅 5    │
│  Totale      Durata        Parole         Settimana│
│  Riunioni    Totale        Totali                  │
│                                                     │
│  📈 Riunioni per Settimana                         │
│  [Grafico a barre + linea]                         │
│                                                     │
│  📋 Ultime 5 Riunioni                              │
│  ┌──────────────────────────────────────────────┐  │
│  │ 🎙️ Senza nome.m4a - 10/11/2025 09:15       │  │
│  │ ⏱️ 114min  📝 561 words  👥 Marco, Claudia  │  │
│  │ TL;DR: Discussione su avanzamento...        │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Configurazione

### Personalizza config

Modifica `streamlit_dashboard.py`:

```python
# Cambia database host
POSTGRES_HOST = "tuo-server.com"

# Cambia porta Streamlit
# Esegui con:
streamlit run streamlit_dashboard.py --server.port 8080
```

### Tema custom

Crea `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

---

## 🐛 Troubleshooting

### Errore: "Address already in use"

**Causa:** Porta 8501 già occupata

**Soluzione:**
```bash
# Usa porta diversa
streamlit run streamlit_dashboard.py --server.port 8502

# O killa processo esistente
lsof -ti:8501 | xargs kill -9
```

### Errore: "Connection to PostgreSQL failed"

**Causa:** Database non raggiungibile

**Soluzione:**
1. Verifica che PostgreSQL sia raggiungibile
2. Controlla credenziali in `streamlit_dashboard.py`
3. Usa pulsante "Test Connessione" nella pagina Settings

### Grafico non si carica

**Causa:** Plotly non installato

**Soluzione:**
```bash
pip install plotly
```

### Cache troppo vecchia

**Causa:** Streamlit cache non aggiornata

**Soluzione:**
```bash
# Clear cache
streamlit cache clear

# O premi 'C' nella UI
```

---

## 🚀 Deploy Produzione

### Opzione 1: Systemd Service (sempre attivo)

```bash
# Crea service file
sudo nano /etc/systemd/system/streamlit-dashboard.service
```

Contenuto:
```ini
[Unit]
Description=Streamlit Meetings Dashboard
After=network.target

[Service]
Type=simple
User=sai
WorkingDirectory=/home/sai/MCPClaude
Environment="PATH=/home/sai/whisper_env/bin"
ExecStart=/home/sai/whisper_env/bin/streamlit run streamlit_dashboard.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

Abilita:
```bash
sudo systemctl daemon-reload
sudo systemctl enable streamlit-dashboard
sudo systemctl start streamlit-dashboard

# Verifica
sudo systemctl status streamlit-dashboard
```

### Opzione 2: Docker (isolato)

```bash
# TODO: Dockerfile per containerizzazione
```

### Opzione 3: Reverse Proxy (Nginx)

Se vuoi accesso su dominio personalizzato:

```nginx
# /etc/nginx/sites-available/meetings-dashboard
server {
    listen 80;
    server_name meetings.tuodominio.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## 📊 Performance

### Tempi Caricamento

| Pagina | Caricamento | Note |
|--------|-------------|------|
| Home | ~1s | Con cache |
| Riunioni | ~2s | Lista completa |
| Dettaglio | ~0.5s | Singola query |
| Ricerca | ~3s | Include embedding |

### Ottimizzazioni

```python
# Cache viene gestito automaticamente con:
@st.cache_resource  # Per connessioni
@st.cache_data      # Per dati

# Per forzare refresh, premi 'R' nella UI
```

---

## 🔒 Sicurezza

### Autenticazione (opzionale)

Installa streamlit-authenticator:

```bash
pip install streamlit-authenticator
```

Aggiungi a `streamlit_dashboard.py`:

```python
import streamlit_authenticator as stauth

# Configura users
names = ['Admin']
usernames = ['admin']
passwords = ['password123']  # usa hashed!

authenticator = stauth.Authenticate(
    names, usernames, passwords,
    'cookie_name', 'signature_key', cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status:
    # Show dashboard
    main()
elif authentication_status == False:
    st.error('Username/password is incorrect')
```

---

## 🎯 Prossimi Sviluppi

- [ ] Upload con processing real-time
- [ ] Export PDF riassunti
- [ ] Notifiche email per nuove riunioni
- [ ] Dashboard personalizzabile
- [ ] Dark mode
- [ ] Multi-language support
- [ ] Integrazione calendario

---

## 📞 Help

Se hai problemi:
1. Check logs Streamlit (nel terminale)
2. Premi 'C' per clear cache
3. Premi 'R' per reload
4. Verifica connessioni DB nella pagina Settings

---

**Versione:** 1.0
**Port:** 8501 (default)
**Status:** Production Ready ✅
