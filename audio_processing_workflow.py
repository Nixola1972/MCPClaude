#!/usr/bin/env python3
"""
Audio Processing Workflow - Automated Pipeline
Esegui come cron job: 0 23 * * * /path/to/audio_processing_workflow.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import requests
import uuid

# ===== CONFIGURAZIONE =====
NEXTCLOUD_URL = "https://your-server.com/nextcloud"
NEXTCLOUD_USER = "your-user"
NEXTCLOUD_PASS = "your-pass"
AUDIO_FOLDER = "/remote.php/dav/files/{user}/Audio_Riunioni/"
PROCESSED_FOLDER = "/remote.php/dav/files/{user}/Audio_Processati/"

LOCAL_AUDIO_DIR = Path("/home/sai/audio_queue")
PROCESSED_DIR = Path("/home/sai/audio_processed")
WHISPER_MODEL = "large-v3"

POSTGRES_HOST = "your-server.com"
POSTGRES_PORT = 5432
POSTGRES_DB = "unified_memory"
POSTGRES_USER = "memory_user"
POSTGRES_PASS = "your-pass"

QDRANT_HOST = "your-server.com"
QDRANT_PORT = 6333

# ===== STEP 1: DOWNLOAD NUOVI AUDIO DA NEXTCLOUD =====
def download_new_audio():
    """Scarica nuovi file audio da Nextcloud (solo file non ancora processati)."""
    print("📥 Step 1: Download audio da Nextcloud...")

    LOCAL_AUDIO_DIR.mkdir(exist_ok=True)

    # WebDAV list files
    import webdav3.client as wc

    options = {
        'webdav_hostname': NEXTCLOUD_URL,
        'webdav_login': NEXTCLOUD_USER,
        'webdav_password': NEXTCLOUD_PASS
    }

    client = wc.Client(options)

    # Ottieni lista file già processati
    processed_files = set()
    try:
        processed_folder = PROCESSED_FOLDER.format(user=NEXTCLOUD_USER)
        processed_files = set(client.list(processed_folder))
        print(f"  ℹ️  Trovati {len(processed_files)} file già processati (verranno saltati)")
    except Exception:
        # Cartella Processati non esiste ancora
        print(f"  ℹ️  Cartella Processati non ancora creata (primo run)")

    # Scarica solo file nuovi (non ancora processati)
    audio_folder = AUDIO_FOLDER.format(user=NEXTCLOUD_USER)
    remote_files = client.list(audio_folder)

    downloaded = 0
    skipped = 0
    for remote_file in remote_files:
        if remote_file.endswith(('.wav', '.m4a', '.mp3', '.flac')):
            # Salta se già processato
            if remote_file in processed_files:
                print(f"  ⏭️  Saltato (già processato): {remote_file}")
                skipped += 1
                continue

            local_path = LOCAL_AUDIO_DIR / Path(remote_file).name

            if not local_path.exists():
                print(f"  ⬇️  Downloading: {remote_file}")
                client.download_sync(
                    remote_path=f"{audio_folder}{remote_file}",
                    local_path=str(local_path)
                )
                downloaded += 1

    print(f"✅ Downloaded {downloaded} new files (saltati {skipped} già processati)")
    return list(LOCAL_AUDIO_DIR.glob("*.wav")) + list(LOCAL_AUDIO_DIR.glob("*.m4a"))


# ===== STEP 2: TRASCRIZIONE WHISPER (GPU) =====
def transcribe_audio_batch(audio_files):
    """Trascrizione batch con Whisper."""
    print(f"\n🎤 Step 2: Trascrizione {len(audio_files)} file con Whisper...")

    import whisper
    import torch

    # Carica modello su GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Device: {device}")

    if device == "cpu":
        print("⚠️  WARNING: GPU non disponibile, usando CPU (molto lento!)")

    model = whisper.load_model(WHISPER_MODEL, device=device)

    transcriptions = []

    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n  [{i}/{len(audio_files)}] Transcribing: {audio_file.name}")

        try:
            result = model.transcribe(
                str(audio_file),
                language="it",
                task="transcribe",
                word_timestamps=True,
                initial_prompt="Riunione aziendale professionale."
            )

            transcription = {
                'filename': audio_file.name,
                'text': result['text'],
                'segments': result['segments'],
                'language': result['language'],
                'duration': audio_file.stat().st_size / (16000 * 2),  # stima
                'timestamp': datetime.now().isoformat()
            }

            transcriptions.append(transcription)

            # Salva trascrizione locale
            output_file = PROCESSED_DIR / f"{audio_file.stem}_transcript.json"
            PROCESSED_DIR.mkdir(exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(transcription, f, ensure_ascii=False, indent=2)

            print(f"    ✅ Trascritto: {len(result['text'])} caratteri")

            # Sposta file processato
            audio_file.rename(PROCESSED_DIR / audio_file.name)

        except Exception as e:
            print(f"    ❌ Errore: {e}")
            continue

    print(f"\n✅ Trascrizioni completate: {len(transcriptions)}/{len(audio_files)}")
    return transcriptions


# ===== STEP 3: ENTITY EXTRACTION (Ollama locale) =====
def extract_entities_ollama(transcriptions):
    """Estrae entities usando Ollama."""
    print(f"\n🧠 Step 3: Entity extraction con Ollama...")

    import requests

    OLLAMA_API = "http://localhost:11434/api/generate"

    all_entities = []

    for trans in transcriptions:
        print(f"\n  Processing: {trans['filename']}")

        prompt = f"""Analizza questa trascrizione di riunione aziendale ed estrai:
1. Persone menzionate (nome completo)
2. Aziende/Organizzazioni
3. Progetti/Prodotti
4. Date importanti e deadline
5. Decisioni chiave
6. Action items con responsabili

Trascrizione:
{trans['text'][:3000]}

Rispondi SOLO in JSON valido:
{{
  "people": [{{"name": "Nome Cognome", "role": "ruolo se menzionato"}}],
  "organizations": ["nome azienda"],
  "projects": ["nome progetto"],
  "dates": [{{"date": "YYYY-MM-DD", "event": "descrizione"}}],
  "decisions": ["decisione presa"],
  "action_items": [{{"assignee": "persona", "task": "cosa fare", "deadline": "quando"}}]
}}
"""

        try:
            response = requests.post(OLLAMA_API, json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }, timeout=120)

            if response.status_code == 200:
                result = response.json()
                entities = json.loads(result['response'])
                entities['source_file'] = trans['filename']
                entities['source_date'] = trans['timestamp']

                all_entities.append(entities)
                print(f"    ✅ Estratti: {len(entities.get('people', []))} persone, "
                      f"{len(entities.get('organizations', []))} org")
            else:
                print(f"    ❌ Ollama error: {response.status_code}")

        except Exception as e:
            print(f"    ❌ Errore extraction: {e}")
            continue

    print(f"\n✅ Entity extraction completata: {len(all_entities)} file")
    return all_entities


# ===== STEP 4: EMBEDDINGS (Ollama nomic-embed) =====
def create_embeddings_ollama(transcriptions):
    """Crea embeddings con Ollama."""
    print(f"\n🔢 Step 4: Creazione embeddings...")

    import requests

    OLLAMA_EMBED_API = "http://localhost:11434/api/embeddings"

    all_embeddings = []

    for trans in transcriptions:
        # Chunk trascrizione (500 caratteri con overlap)
        text = trans['text']
        chunk_size = 500
        overlap = 50

        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if len(chunk) > 50:  # Minimo 50 char
                chunks.append(chunk)

        print(f"\n  {trans['filename']}: {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            try:
                response = requests.post(OLLAMA_EMBED_API, json={
                    "model": "nomic-embed-text",
                    "prompt": chunk
                }, timeout=30)

                if response.status_code == 200:
                    embedding = response.json()['embedding']

                    all_embeddings.append({
                        'text': chunk,
                        'embedding': embedding,
                        'source_file': trans['filename'],
                        'source_date': trans['timestamp'],
                        'chunk_index': i
                    })

            except Exception as e:
                print(f"    ❌ Embedding error chunk {i}: {e}")
                continue

        print(f"    ✅ Created {len(chunks)} embeddings")

    print(f"\n✅ Embeddings totali: {len(all_embeddings)}")
    return all_embeddings


# ===== STEP 5: UPLOAD A POSTGRESQL (Web Server) =====
def upload_to_postgres(entities_list, transcriptions):
    """Upload entities e transcriptions a PostgreSQL."""
    print(f"\n🐘 Step 5: Upload a PostgreSQL...")

    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASS
    )
    cur = conn.cursor()

    uploaded_entities = 0
    uploaded_observations = 0

    for entities in entities_list:
        source_file = entities['source_file']
        source_date = entities['source_date']

        # Inserisci source
        cur.execute("""
            INSERT INTO sources (source_type, source_id, source_date, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, ('audio', source_file, source_date, json.dumps(entities)))

        source_id = cur.fetchone()[0]

        # Inserisci entities (persone, org, progetti)
        for person in entities.get('people', []):
            cur.execute("""
                INSERT INTO entities (name, entity_type)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (person['name'], 'person'))

            entity_id = cur.fetchone()[0]
            uploaded_entities += 1

            # Aggiungi observation (ruolo)
            if person.get('role'):
                cur.execute("""
                    INSERT INTO observations (entity_id, content, source_id, confidence)
                    VALUES (%s, %s, %s, %s)
                """, (entity_id, f"Ruolo: {person['role']}", source_id, 0.9))
                uploaded_observations += 1

        # Organizations
        for org in entities.get('organizations', []):
            cur.execute("""
                INSERT INTO entities (name, entity_type)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (org, 'organization'))
            uploaded_entities += 1

        # Projects
        for project in entities.get('projects', []):
            cur.execute("""
                INSERT INTO entities (name, entity_type)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (project, 'project'))
            uploaded_entities += 1

        # Decisions come observations
        for decision in entities.get('decisions', []):
            # Collega alla source come observation generale
            cur.execute("""
                INSERT INTO observations (entity_id, content, source_id, confidence)
                SELECT id, %s, %s, %s FROM entities WHERE name = 'General_Context' LIMIT 1
            """, (f"Decisione: {decision}", source_id, 0.85))
            uploaded_observations += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Uploaded: {uploaded_entities} entities, {uploaded_observations} observations")


# ===== STEP 6: UPLOAD A QDRANT (Web Server) =====
def upload_to_qdrant(embeddings):
    """Upload embeddings a Qdrant."""
    print(f"\n🔍 Step 6: Upload a Qdrant...")

    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    collection_name = "unified_memory_audio"

    # Crea collection se non esiste
    try:
        client.get_collection(collection_name)
    except:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
        print(f"  Created collection: {collection_name}")

    # Upload points
    points = []
    for i, emb in enumerate(embeddings):
        # Genera UUID univoco per ogni chunk (evita sovrascritture tra run!)
        point_id = str(uuid.uuid4())

        points.append(PointStruct(
            id=point_id,
            vector=emb['embedding'],
            payload={
                'text': emb['text'],
                'source_file': emb['source_file'],
                'source_date': emb['source_date'],
                'chunk_index': emb['chunk_index']
            }
        ))

    client.upsert(collection_name=collection_name, points=points)

    print(f"✅ Uploaded {len(points)} vectors to Qdrant")


# ===== STEP 7: SPOSTA FILE PROCESSATI =====
def move_processed_files(transcriptions):
    """Sposta i file processati in cartella Processati su Nextcloud."""
    print(f"\n📦 Step 7: Sposta {len(transcriptions)} file processati su Nextcloud...")

    import webdav3.client as wc

    options = {
        'webdav_hostname': NEXTCLOUD_URL,
        'webdav_login': NEXTCLOUD_USER,
        'webdav_password': NEXTCLOUD_PASS
    }

    client = wc.Client(options)

    # Crea cartella Processati se non esiste
    processed_folder = PROCESSED_FOLDER.format(user=NEXTCLOUD_USER)
    try:
        client.mkdir(processed_folder)
        print(f"  ✅ Creata cartella: {processed_folder}")
    except Exception:
        # Cartella già esistente
        pass

    moved = 0
    for trans in transcriptions:
        filename = trans['filename']
        audio_folder = AUDIO_FOLDER.format(user=NEXTCLOUD_USER)

        remote_source = f"{audio_folder}{filename}"
        remote_dest = f"{processed_folder}{filename}"

        try:
            # Sposta file (move = copy + delete)
            client.move(remote_path=remote_source, remote_path2=remote_dest)
            print(f"  ✅ Spostato: {filename}")
            moved += 1
        except Exception as e:
            print(f"  ⚠️  Errore spostando {filename}: {e}")

    print(f"✅ Spostati {moved}/{len(transcriptions)} file in Audio_Processati")


# ===== MAIN WORKFLOW =====
def main():
    print("=" * 60)
    print("🚀 AUDIO PROCESSING WORKFLOW - AUTOMATED PIPELINE")
    print("=" * 60)
    print(f"Started: {datetime.now()}\n")

    try:
        # Step 1: Download
        audio_files = download_new_audio()

        if not audio_files:
            print("\n✅ Nessun nuovo file da processare. Exit.")
            return

        # Step 2: Trascrizione
        transcriptions = transcribe_audio_batch(audio_files)

        if not transcriptions:
            print("\n❌ Nessuna trascrizione completata. Exit.")
            return

        # Step 3: Entity extraction
        entities = extract_entities_ollama(transcriptions)

        # Step 4: Embeddings
        embeddings = create_embeddings_ollama(transcriptions)

        # Step 5: Upload PostgreSQL
        upload_to_postgres(entities, transcriptions)

        # Step 6: Upload Qdrant
        upload_to_qdrant(embeddings)

        # Step 7: Sposta file processati su Nextcloud
        move_processed_files(transcriptions)

        print("\n" + "=" * 60)
        print(f"✅ WORKFLOW COMPLETATO - {datetime.now()}")
        print(f"   Trascritti: {len(transcriptions)} file")
        print(f"   Entities: {sum(len(e.get('people', [])) + len(e.get('organizations', [])) for e in entities)}")
        print(f"   Embeddings: {len(embeddings)}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERRORE WORKFLOW: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
