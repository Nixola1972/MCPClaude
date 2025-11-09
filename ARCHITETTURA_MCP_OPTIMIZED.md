# 🏗️ Architettura MCP-Optimized per Massimo Contesto

## 🎯 Obiettivo
Fornire a Claude via MCP il **massimo contesto utile** nel **minimo spazio**, con retrieval intelligente e multi-layer.

---

## 📊 Principio Chiave: Piramide del Contesto

```
                    ┌─────────────┐
                    │  TL;DR      │  ← MCP mostra PRIMA (2-3 frasi)
                    │  (50 token) │
                    └──────┬──────┘
                           │
                  ┌────────▼─────────┐
                  │   RIASSUNTO      │  ← Se Claude chiede dettagli
                  │   DETTAGLIATO    │
                  │   (500 token)    │
                  └────────┬─────────┘
                           │
              ┌────────────▼──────────────┐
              │   TRASCRIZIONE COMPLETA   │  ← Solo se esplicitamente richiesto
              │   (18.000 token)          │
              └───────────────────────────┘
```

**Vantaggio:** Claude vede subito l'essenziale, approfondisce solo se necessario.

---

## 🗄️ Schema Storage Multi-Layer

### PostgreSQL: 4 Tabelle Principali

#### 1. `sources` (già esistente)
```sql
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50),        -- 'audio', 'email', 'chat'
    source_id VARCHAR(500),          -- filename
    source_date TIMESTAMP,
    duration_seconds INTEGER,        -- NUOVO: durata audio
    metadata JSONB
);
```

#### 2. `transcriptions` (NUOVA)
```sql
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    full_text TEXT,                  -- Trascrizione completa
    word_count INTEGER,
    language VARCHAR(10),            -- 'it', 'en'
    created_at TIMESTAMP
);
```

#### 3. `summaries` (NUOVA - CORE PER MCP!)
```sql
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    summary_type VARCHAR(50),        -- 'tldr', 'detailed', 'action_items'
    content TEXT,

    -- Structured metadata per MCP query
    participants JSONB,              -- ["Marco", "Sara", "Tech Team"]
    topics JSONB,                    -- ["budget", "cloud migration"]
    decisions JSONB,                 -- [{"decision": "...", "by": "Marco"}]
    action_items JSONB,              -- [{"task": "...", "owner": "Marco", "deadline": "..."}]
    key_numbers JSONB,               -- [{"amount": "50k", "context": "budget Q1"}]

    created_at TIMESTAMP
);
```

#### 4. `entities` + `observations` (già esistenti, ottimizzate)
```sql
-- Entities: persone, progetti, aziende
-- Observations: fatti estratti collegati a entities
-- Relations: collegamenti tra entities
```

---

## 🔍 Qdrant: 2 Collection Strategiche

### Collection 1: `memory_summaries` (PRINCIPALE)
**Cosa:** Embedding dei riassunti dettagliati
**Quando:** Tutti gli audio >5 min

```python
{
    "vector": [0.234, -0.123, ...],  # 768 dim
    "payload": {
        "summary": "Riunione budget Q1 2025. Approvati €50k...",
        "tldr": "Budget Q1: €50k approvati, deadline marzo",
        "source_file": "Riunione_10marzo.m4a",
        "source_date": "2025-03-10T14:30:00",
        "duration_min": 135,
        "participants": ["Marco", "Sara"],
        "topics": ["budget", "cloud"],
        "has_decisions": true,
        "has_action_items": true,
        "key_numbers": [{"amount": "50k", "type": "budget"}]
    }
}
```

**Vantaggio:** 1 vector per audio (invece di 90!) → ricerca veloce e precisa

### Collection 2: `memory_transcripts` (SECONDARIA)
**Cosa:** Embedding chunks trascrizione (con timestamp)
**Quando:** Solo se audio ha info temporali importanti

```python
{
    "vector": [...],
    "payload": {
        "text": "Discusso fornitori AWS vs Azure...",
        "source_file": "Riunione_10marzo.m4a",
        "timestamp_start": "01:23:45",
        "timestamp_end": "01:28:30",
        "chunk_index": 15
    }
}
```

**Uso:** Quando Claude chiede "a che minuto hanno parlato di AWS?"

---

## 🤖 Workflow Processing Intelligente

### Logica Decision Tree

```
Audio File
    ↓
Durata < 5 min?
    ↓ YES
    ├─ Trascrizione → PostgreSQL
    ├─ Embedding trascrizione → Qdrant
    └─ Entities → PostgreSQL

    ↓ NO (>5 min)
    ├─ Trascrizione → PostgreSQL
    ├─ LLM: Riassunto Dettagliato → PostgreSQL
    ├─ LLM: TL;DR → PostgreSQL
    ├─ LLM: Structured extraction → PostgreSQL
    │   ├─ Participants
    │   ├─ Topics
    │   ├─ Decisions
    │   ├─ Action items
    │   └─ Key numbers
    ├─ Embedding RIASSUNTO (non trascrizione!) → Qdrant
    └─ Entities + Relations → PostgreSQL
```

---

## 🔎 MCP Query Interface (Come Claude Interroga)

### Scenario 1: Query Generica
**User:** "Cosa abbiamo deciso sul cloud?"

**MCP fa:**
1. Semantic search su `memory_summaries` collection
2. Trova: "Riunione budget Q1..." (cosine similarity 0.92)
3. Carica payload Qdrant → vede `has_decisions: true`
4. Query PostgreSQL: `SELECT * FROM summaries WHERE source_id=X AND summary_type='detailed'`
5. Restituisce a Claude:

```
📄 Riunione Budget Q1 (10/03/2025, 2h 15m)
👥 Marco, Sara, Tech Team

🎯 TL;DR:
Budget Q1: approvati €50k per migrazione cloud, deadline marzo 2025

📋 Dettagli:
• Decisione: migrazione cloud approvata con budget €50k
• Fornitori: da valutare AWS vs Azure
• Responsabile: Marco
• Deadline: completamento entro 31 marzo 2025

✅ Action Items:
• Marco: proposal tecnico entro 15/03
• Sara: analisi costi dettagliata entro 20/03

[Trascrizione completa disponibile su richiesta]
```

**Token usati:** ~150 invece di 18.000! 💰

---

### Scenario 2: Temporal Query
**User:** "Cosa abbiamo discusso nelle ultime 2 settimane?"

**MCP fa:**
1. Query PostgreSQL: `SELECT * FROM summaries WHERE created_at > NOW() - INTERVAL '14 days' ORDER BY created_at DESC`
2. Restituisce lista TL;DR:

```
📅 Ultimi 14 giorni:

10/03 - Riunione Budget Q1
  └─ Budget €50k cloud, deadline marzo

05/03 - Standup Team
  └─ Progress Sprint 12, review giovedì

01/03 - Client Call Acme Corp
  └─ Requirements feature X, demo 15/03
```

---

### Scenario 3: Entity-based Query
**User:** "Cosa ha detto Marco ultimamente?"

**MCP fa:**
1. Query: `SELECT DISTINCT s.id FROM summaries s WHERE s.participants @> '["Marco"]'`
2. Recupera tutti i riassunti dove Marco era presente
3. Restituisce timeline:

```
👤 Marco - Ultime menzioni:

10/03 - Riunione Budget Q1
  └─ Responsabile migrazione cloud, proposal entro 15/03

08/03 - Planning Sprint 13
  └─ Assegnato task API refactoring

05/03 - Standup
  └─ Completato feature authentication
```

---

## 💾 Ottimizzazione Token MCP

### Senza Riassunti (Attuale)
```
Query: "budget cloud"
→ Trova 90 chunks di trascrizione
→ Claude riceve: 18.000 token di trascrizione grezza
→ Deve processare tutto per capire
→ Context window pieno subito
```

### Con Riassunti (Proposta)
```
Query: "budget cloud"
→ Trova 1 riassunto
→ Claude riceve: 150 token (TL;DR + dettagli)
→ Capisce subito, context disponibile per altro
→ Se serve dettagli → chiede trascrizione specifica
```

**Risparmio:** 99.2% token! 🚀

---

## 📊 Prompt LLM per Riassunti

### Prompt per Riassunto Dettagliato
```
Analizza questa trascrizione di riunione e crea un riassunto strutturato.

TRASCRIZIONE:
{full_text}

ESTRAI:
1. Partecipanti (nomi persone menzionate)
2. Argomenti principali discussi
3. Decisioni prese (chi, cosa, quando)
4. Action items (task, owner, deadline)
5. Numeri chiave (budget, date, metriche)

FORMATO OUTPUT JSON:
{
  "participants": ["Marco", "Sara"],
  "topics": ["budget Q1", "cloud migration"],
  "decisions": [
    {"decision": "Approvato budget €50k", "by": "Team", "date": "2025-03-10"}
  ],
  "action_items": [
    {"task": "Proposal tecnico", "owner": "Marco", "deadline": "2025-03-15"}
  ],
  "key_numbers": [
    {"amount": "50k", "type": "budget", "context": "migrazione cloud"}
  ],
  "detailed_summary": "Testo riassunto 300-500 parole...",
  "tldr": "Frase ultra-concisa 1-2 righe"
}
```

### Prompt per TL;DR
```
Riassumi in 1-2 frasi (max 50 token) l'essenza di questa riunione:

{full_text}

Rispondi solo con il riassunto, niente altro.
```

---

## 🎨 Visualizzazione Output Processing

### Dopo Processing, Stampa a Schermo:
```
╔══════════════════════════════════════════════════════════╗
║  ✅ PROCESSATO: Riunione_Budget_Q1.m4a                  ║
╚══════════════════════════════════════════════════════════╝

⏱️  DURATA: 2h 15m (8100 secondi)
📝 TRASCRIZIONE: 18.234 parole

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 TL;DR:
Budget Q1 2025: approvati €50k per migrazione cloud,
deadline 31 marzo. Marco responsabile.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 RIASSUNTO DETTAGLIATO:

Riunione dedicata alla pianificazione budget Q1 2025 con
focus su migrazione cloud. Discussi pro/contro AWS vs Azure.
Team ha approvato budget di €50k. Marco nominato project
leader con deadline completamento 31 marzo. Sara gestirà
analisi costi. Action items assegnati con scadenze precise.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 PARTECIPANTI:
• Marco (PM)
• Sara (Finance)
• Tech Team

🏷️  ARGOMENTI:
• Budget Q1 2025
• Cloud Migration
• Vendor Selection

🎯 DECISIONI:
• Budget €50k approvato (Team, 10/03/2025)
• Vendor selection entro 15/03 (Marco)

✅ ACTION ITEMS:
• [Marco] Proposal tecnico → 📅 15/03/2025
• [Sara] Analisi costi → 📅 20/03/2025

💰 NUMERI CHIAVE:
• €50k - Budget migrazione cloud
• 31/03 - Deadline completamento

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 ENTITIES ESTRATTE:
• Marco (person)
• Sara (person)
• Progetto_Cloud_Migration (project)
• AWS (organization)
• Azure (organization)

🔗 RELATIONS:
• Marco → responsabile → Progetto_Cloud_Migration
• Sara → gestisce → Budget_Analysis

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💾 SALVATO:
✅ PostgreSQL: 1 source, 1 transcription, 3 summaries, 5 entities
✅ Qdrant: 1 summary embedding (invece di 90 chunks!)

╚══════════════════════════════════════════════════════════╝
```

---

## 🔧 Implementazione Tecnica

### Modifiche al Workflow

1. **Calcolo durata audio**
2. **Decision: riassunto SI/NO** (soglia 5 min)
3. **LLM: generazione riassunti** (detailed + tldr + structured)
4. **Salvataggio multi-layer** (transcriptions + summaries)
5. **Embedding intelligente** (su summary se >5min, altrimenti su trascrizione)
6. **Visualizzazione formattata**

### Nuovi File da Creare

- `audio_processing_workflow.py` - MODIFICATO con logica riassunti
- `init-db-v2.sql` - Schema aggiornato con nuove tabelle
- `mcp_server.py` - Server MCP per query intelligenti
- `query_mcp_style.py` - Query ottimizzate per contesto

---

## 📈 Benefici Architettura MCP-Optimized

| Aspetto | Prima | Dopo | Miglioramento |
|---------|-------|------|--------------|
| Token per query | 18.000 | 150 | **99.2%** |
| Tempo ricerca | Lento (90 chunks) | Veloce (1 summary) | **90x** |
| Contesto Claude | 1 audio = context pieno | 100+ audio = context libero | **100x** |
| Precisione risultati | Medio (chunks misti) | Alta (riassunti mirati) | **3x** |
| Costo embedding | Alto (90 embed/audio) | Basso (1 embed/audio) | **90x** |

---

## 🎯 Prossimi Step Implementazione

1. ✅ Database pulito
2. ⏳ Aggiornare schema PostgreSQL
3. ⏳ Modificare workflow con riassunti
4. ⏳ Implementare visualizzazione
5. ⏳ Testare con audio reale
6. ⏳ Creare MCP server

---

**Autore:** Claude + Nicola
**Data:** 2025-11-09
**Versione:** 1.0 - MCP Context-Optimized Architecture
