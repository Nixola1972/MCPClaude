#!/usr/bin/env python3
"""
Audio Processing Workflow v2.0 - MCP-Optimized
Features:
- Smart summaries (only for audio >5 min)
- Multi-layer context (TL;DR, Detailed, Structured)
- Optimized embeddings (summary-based instead of chunks)
- Beautiful formatted output
- New schema: transcriptions + summaries tables
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import requests
import uuid

# ===== CONFIGURATION =====
NEXTCLOUD_URL = "http://srv778971.hstgr.cloud:8082"
NEXTCLOUD_USER = "admin"
NEXTCLOUD_PASS = "AdminNext2025!Safe"
AUDIO_FOLDER = "/remote.php/dav/files/{user}/Audio_Riunioni/"
PROCESSED_FOLDER = "/remote.php/dav/files/{user}/Audio_Processati/"

LOCAL_AUDIO_DIR = Path("/home/sai/audio_queue")
PROCESSED_DIR = Path("/home/sai/audio_processed")
WHISPER_MODEL = "large-v3"

POSTGRES_HOST = "srv778971.hstgr.cloud"
POSTGRES_PORT = 5433
POSTGRES_DB = "unified_memory"
POSTGRES_USER = "memory_user"
POSTGRES_PASS = "MemoryDB2025!Sicura"

QDRANT_HOST = "srv778971.hstgr.cloud"
QDRANT_PORT = 6333

OLLAMA_API = "http://localhost:11434/api/generate"
OLLAMA_EMBED_API = "http://localhost:11434/api/embeddings"

# Thresholds
SUMMARY_MIN_DURATION = 180  # 3 minutes in seconds

# ===== UTILITY: FILE HASH =====
def get_file_hash(file_path):
    """Calcola hash MD5 del contenuto file per identificazione univoca."""
    import hashlib
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()

# ===== STEP 1: DOWNLOAD AUDIO =====
def download_new_audio():
    """Download new audio files from Nextcloud with hash-based duplicate detection."""
    print("📥 Step 1: Download audio from Nextcloud...")

    # Clean local queue
    import shutil
    if LOCAL_AUDIO_DIR.exists():
        shutil.rmtree(LOCAL_AUDIO_DIR)
    LOCAL_AUDIO_DIR.mkdir(exist_ok=True)

    import webdav3.client as wc
    import psycopg2

    # Get processed file hashes from database
    processed_hashes = set()
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST, port=POSTGRES_PORT,
            dbname=POSTGRES_DB, user=POSTGRES_USER,
            password=POSTGRES_PASS
        )
        cur = conn.cursor()
        cur.execute("SELECT file_hash FROM sources WHERE file_hash IS NOT NULL")
        processed_hashes = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()
        print(f"  ℹ️  Found {len(processed_hashes)} already processed files (by hash)")
    except Exception as e:
        print(f"  ⚠️  Could not connect to database for hash check: {e}")
        print(f"  ℹ️  Continuing with name-based check...")

    options = {
        'webdav_hostname': NEXTCLOUD_URL,
        'webdav_login': NEXTCLOUD_USER,
        'webdav_password': NEXTCLOUD_PASS
    }

    client = wc.Client(options)

    # Fallback: get processed files by name
    processed_files = set()
    try:
        processed_folder = PROCESSED_FOLDER.format(user=NEXTCLOUD_USER)
        processed_files = set(client.list(processed_folder))
        print(f"  ℹ️  Found {len(processed_files)} files in processed folder")
    except Exception:
        print(f"  ℹ️  Processed folder not yet created (first run)")

    # Download new files
    audio_folder = AUDIO_FOLDER.format(user=NEXTCLOUD_USER)
    remote_files = client.list(audio_folder)

    downloaded = 0
    skipped = 0
    file_metadata = {}  # Store hash for each downloaded file

    for remote_file in remote_files:
        if remote_file.endswith(('.wav', '.m4a', '.mp3', '.flac')):
            local_path = LOCAL_AUDIO_DIR / Path(remote_file).name

            # Download temporarily to check hash
            print(f"  ⬇️  Downloading: {remote_file}")
            client.download_sync(
                remote_path=f"{audio_folder}{remote_file}",
                local_path=str(local_path)
            )

            # Calculate hash
            file_hash = get_file_hash(str(local_path))

            # Check if already processed (by hash or name)
            if file_hash in processed_hashes:
                print(f"  ⏭️  Skipped (duplicate content detected by hash): {remote_file}")
                local_path.unlink()  # Delete duplicate
                skipped += 1
                continue
            elif remote_file in processed_files:
                print(f"  ⏭️  Skipped (already in processed folder): {remote_file}")
                local_path.unlink()  # Delete duplicate
                skipped += 1
                continue

            # New file! Store metadata
            file_metadata[str(local_path)] = {
                'hash': file_hash,
                'original_name': remote_file
            }
            downloaded += 1
            print(f"  ✅ New file: {remote_file} (hash: {file_hash[:8]}...)")

    print(f"✅ Downloaded {downloaded} new files (skipped {skipped} duplicates)")

    # Return both files and metadata
    audio_files = list(LOCAL_AUDIO_DIR.glob("*.wav")) + list(LOCAL_AUDIO_DIR.glob("*.m4a")) + list(LOCAL_AUDIO_DIR.glob("*.mp3"))
    return audio_files, file_metadata


# ===== STEP 2: TRANSCRIPTION =====
def transcribe_audio_batch(audio_files, file_metadata):
    """Transcribe audio files with faster-whisper (optimized) with VAD and quality checks."""
    print(f"\n🎤 Step 2: Transcribing {len(audio_files)} files with faster-whisper...")

    from faster_whisper import WhisperModel
    import torch

    # Auto-detect GPU or fallback to CPU
    try:
        if torch.cuda.is_available():
            device = "cuda"
            compute_type = "float16"
            print(f"  Device: {device} (compute_type: {compute_type})")
            print(f"  🚀 GPU detected: {torch.cuda.get_device_name(0)}")
            print(f"  💾 VRAM available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            device = "cpu"
            compute_type = "int8"
            print(f"  Device: {device} (compute_type: {compute_type})")
            print("  ⚠️  GPU not available, using CPU")
    except Exception as e:
        print(f"  ⚠️  GPU detection failed ({e}), falling back to CPU")
        device = "cpu"
        compute_type = "int8"

    # Load faster-whisper model
    model = WhisperModel(WHISPER_MODEL, device=device, compute_type=compute_type)

    transcriptions = []

    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n  [{i}/{len(audio_files)}] Transcribing: {audio_file.name}")

        try:
            # Faster-whisper with VAD enabled
            segments, info = model.transcribe(
                str(audio_file),
                language="it",
                task="transcribe",
                word_timestamps=True,
                initial_prompt="Riunione aziendale professionale.",
                vad_filter=True,  # VAD now works!
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=2000
                )
            )

            # Convert generator to list and build text
            segments_list = list(segments)
            full_text = " ".join([seg.text for seg in segments_list])

            # Calculate duration and quality metrics
            duration_seconds = segments_list[-1].end if segments_list else 0
            word_count = len(full_text.split())

            # Calculate words per minute
            words_per_minute = (word_count / (duration_seconds / 60)) if duration_seconds > 0 else 0

            # Calculate average confidence
            avg_confidence = 0.0
            if segments_list:
                confidences = []
                for seg in segments_list:
                    if hasattr(seg, 'words') and seg.words:
                        for word in seg.words:
                            if hasattr(word, 'probability'):
                                confidences.append(word.probability)
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)

            # Get file hash from metadata
            file_hash = file_metadata.get(str(audio_file), {}).get('hash', None)

            # Convert segments to dict format for storage
            segments_dict = [
                {
                    'start': seg.start,
                    'end': seg.end,
                    'text': seg.text
                }
                for seg in segments_list
            ]

            transcription = {
                'filename': audio_file.name,
                'file_hash': file_hash,
                'text': full_text.strip(),
                'segments': segments_dict,
                'language': info.language,
                'duration_seconds': int(duration_seconds),
                'word_count': word_count,
                'words_per_minute': round(words_per_minute, 1),
                'avg_confidence': round(avg_confidence, 3),
                'timestamp': datetime.now().isoformat()
            }

            transcriptions.append(transcription)

            print(f"    ✅ Transcribed: {word_count} words, {int(duration_seconds)}s, {words_per_minute:.1f} w/min")

            # Quality warnings
            if words_per_minute < 30 and duration_seconds > 60:
                print(f"    ⚠️  LOW QUALITY: Only {words_per_minute:.1f} words/min")
                print(f"       Possible low audio quality or long silences")

            if avg_confidence > 0 and avg_confidence < 0.7:
                print(f"    ⚠️  LOW CONFIDENCE: {avg_confidence:.2%}")
                print(f"       Audio might be unclear or noisy")

        except Exception as e:
            print(f"    ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n✅ Transcriptions completed: {len(transcriptions)}/{len(audio_files)}")
    return transcriptions


# ===== STEP 3: SUMMARIES (NEW!) =====
def create_single_summary(trans):
    """Create summary for a single transcription."""
    duration = trans['duration_seconds']
    filename = trans['filename']

    # Decision: summary or not?
    if duration < SUMMARY_MIN_DURATION:
        return {
            'filename': filename,
            'has_summary': False
        }

    # Improved prompt with better instructions
    prompt = f"""IMPORTANTE: Rispondi ESCLUSIVAMENTE in lingua ITALIANA. Tutti i testi devono essere in italiano.

Analizza questa trascrizione di riunione italiana e crea un riassunto strutturato in ITALIANO.

TRASCRIZIONE ({trans['word_count']} parole, {duration}s):
{trans['text']}

ESTRAI (in formato JSON, TUTTO in italiano):
1. participants: lista SOLO nomi delle persone PRESENTI alla riunione (che parlano o partecipano attivamente). NON includere clienti, progetti o persone solo menzionate. Esempi: ["Marco", "Sara", "Claudia"]

2. mentioned_people: nomi di persone, clienti, fornitori o aziende MENZIONATE ma NON presenti alla riunione. Esempi: ["Cliente Rossi", "Fornitore XYZ", "Azienda ABC"]

3. topics: argomenti principali discussi in ITALIANO (massimo 8 argomenti). Esempi: ["Avanzamento progetti fotovoltaici", "Budget marketing", "Problemi autorizzazioni"]

4. decisions: decisioni CONCRETE prese durante la riunione, scritte in ITALIANO. Ogni decisione deve avere:
   - decision: cosa è stato deciso (in italiano)
   - by: chi ha deciso (nome persona o "Team")
   - date: quando implementare (o "Immediato" se non specificato)
   Esempi: [
     {{"decision": "Investire 1000 euro al mese in Google Ads per 6 mesi", "by": "Marco", "date": "Immediato"}},
     {{"decision": "Completare installazione entro metà novembre", "by": "Team", "date": "15 novembre"}}
   ]

5. action_items: azioni concrete da fare, scritte in ITALIANO. Ogni azione deve avere:
   - task: cosa fare (descrizione chiara in italiano)
   - owner: chi deve farlo (nome specifico, NON "Sconosciuto")
   - deadline: quando (data o periodo, es. "Lunedì", "15 novembre", "Fine mese")
   Esempi: [
     {{"task": "Ottenere risposta dal comune su autorizzazione", "owner": "Claudia", "deadline": "Lunedì"}},
     {{"task": "Pianificare installazione con Lorandi", "owner": "Marco", "deadline": "Fine novembre"}}
   ]

6. key_numbers: numeri e cifre importanti menzionate. Ogni numero deve avere:
   - amount: il numero/cifra (solo cifre, es. "1000", "6")
   - type: tipo in ITALIANO (es. "budget", "durata", "quantità", "percentuale")
   - context: cosa rappresenta in ITALIANO (breve descrizione)
   Esempi: [
     {{"amount": "1000", "type": "budget", "context": "Budget mensile Google Ads in euro"}},
     {{"amount": "6", "type": "durata", "context": "Durata campagna marketing in mesi"}}
   ]

7. detailed_summary: riassunto dettagliato narrativo in ITALIANO (200-400 parole) che spiega cosa è stato discusso, quali problemi sono emersi, quali soluzioni proposte, e prossimi passi

8. tldr: riassunto ultra-conciso in ITALIANO (1-2 frasi, massimo 40 parole) che cattura l'essenza della riunione

REGOLE FONDAMENTALI:
- Rispondi SOLO con JSON valido, nessun altro testo
- TUTTO il contenuto deve essere in lingua ITALIANA (decisions, action_items, topics, summaries, ecc.)
- Se non trovi informazioni per una sezione, usa array vuoto [] o stringa vuota ""
- Sii preciso e specifico, evita generalizzazioni
- NON usare inglese, SOLO italiano
"""

    try:
        response = requests.post(OLLAMA_API, json={
            "model": "gemma3:12b",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.3, "num_ctx": 8192}
        }, timeout=240)

        if response.status_code == 200:
            result = response.json()
            summary_json = json.loads(result['response'])

            return {
                'filename': filename,
                'has_summary': True,
                'participants': summary_json.get('participants', []),
                'mentioned_people': summary_json.get('mentioned_people', []),
                'topics': summary_json.get('topics', []),
                'decisions': summary_json.get('decisions', []),
                'action_items': summary_json.get('action_items', []),
                'key_numbers': summary_json.get('key_numbers', []),
                'detailed_summary': summary_json.get('detailed_summary', ''),
                'tldr': summary_json.get('tldr', '')
            }
        else:
            return {'filename': filename, 'has_summary': False, 'error': f"Ollama error: {response.status_code}"}

    except Exception as e:
        return {'filename': filename, 'has_summary': False, 'error': str(e)}


def create_summaries_ollama(transcriptions):
    """Create intelligent summaries with parallel processing."""
    print(f"\n📝 Step 3: Creating summaries (parallel processing)...")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_summaries = []

    # Use thread pool for parallel processing (max 3 concurrent requests)
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all tasks
        future_to_trans = {executor.submit(create_single_summary, trans): trans for trans in transcriptions}

        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_trans), 1):
            trans = future_to_trans[future]
            filename = trans['filename']
            duration = trans['duration_seconds']

            print(f"\n  [{i}/{len(transcriptions)}] {filename} ({duration}s)")

            try:
                summary = future.result()
                all_summaries.append(summary)

                if summary.get('has_summary'):
                    print(f"    ✅ Summary created")
                    print(f"       - Participants: {len(summary.get('participants', []))}")
                    print(f"       - Mentioned: {len(summary.get('mentioned_people', []))}")
                    print(f"       - Topics: {len(summary.get('topics', []))}")
                    print(f"       - Decisions: {len(summary.get('decisions', []))}")
                    print(f"       - Actions: {len(summary.get('action_items', []))}")
                    print(f"       - Numbers: {len(summary.get('key_numbers', []))}")
                elif 'error' in summary:
                    print(f"    ❌ Error: {summary['error']}")
                else:
                    print(f"    ⏭️  Skipped (too short)")

            except Exception as e:
                print(f"    ❌ Exception: {e}")
                all_summaries.append({'filename': filename, 'has_summary': False})

    # Sort summaries to match original order
    summary_dict = {s['filename']: s for s in all_summaries}
    all_summaries = [summary_dict.get(t['filename'], {'filename': t['filename'], 'has_summary': False}) for t in transcriptions]

    print(f"\n✅ Summaries completed: {sum(1 for s in all_summaries if s.get('has_summary'))}/{len(all_summaries)}")
    return all_summaries


# ===== STEP 4: EMBEDDINGS (OPTIMIZED!) =====
def create_embeddings_ollama(transcriptions, summaries):
    """Create embeddings (summary-based for long audio, transcription-based for short)."""
    print(f"\n🔢 Step 4: Creating embeddings...")
    
    all_embeddings = []
    
    for trans in transcriptions:
        filename = trans['filename']
        
        # Find corresponding summary
        summary = next((s for s in summaries if s['filename'] == filename), None)
        
        if summary and summary.get('has_summary'):
            # Use summary for embedding (optimal!)
            text_to_embed = f"{summary['tldr']}\n\n{summary['detailed_summary']}"
            embed_type = "summary"
        else:
            # Use transcription for embedding (short audio)
            text_to_embed = trans['text']
            embed_type = "transcription"
        
        print(f"\n  {filename}: embedding {embed_type} ({len(text_to_embed)} chars)")
        
        try:
            response = requests.post(OLLAMA_EMBED_API, json={
                "model": "nomic-embed-text",
                "prompt": text_to_embed
            }, timeout=60)
            
            if response.status_code == 200:
                embedding_vector = response.json()['embedding']
                
                all_embeddings.append({
                    'filename': filename,
                    'embedding': embedding_vector,
                    'text': text_to_embed,
                    'embed_type': embed_type,
                    'source_date': trans['timestamp'],
                    'duration_seconds': trans['duration_seconds']
                })
                
                print(f"    ✅ Created 1 embedding (768-dim, type: {embed_type})")
            else:
                print(f"    ❌ Ollama error: {response.status_code}")
        
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    print(f"\n✅ Embeddings total: {len(all_embeddings)}")
    return all_embeddings


# ===== STEP 5: UPLOAD TO POSTGRESQL (NEW SCHEMA!) =====
def upload_to_postgres(transcriptions, summaries):
    """Upload to PostgreSQL using new schema v2.1 with file_hash and quality metrics."""
    print(f"\n🐘 Step 5: Uploading to PostgreSQL...")

    import psycopg2
    from psycopg2.extras import Json

    conn = psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        dbname=POSTGRES_DB, user=POSTGRES_USER,
        password=POSTGRES_PASS
    )
    cur = conn.cursor()

    sources_created = 0
    transcriptions_created = 0
    summaries_created = 0

    for trans in transcriptions:
        filename = trans['filename']

        # Build enhanced metadata with quality metrics
        metadata = {
            'word_count': trans['word_count'],
            'language': trans['language'],
            'quality_metrics': {
                'words_per_minute': trans.get('words_per_minute', 0),
                'avg_confidence': trans.get('avg_confidence', 0)
            }
        }

        # 1. Create source with file_hash
        try:
            cur.execute("""
                INSERT INTO sources (source_type, source_id, source_date, duration_seconds, metadata, file_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                'audio',
                filename,
                trans['timestamp'],
                trans['duration_seconds'],
                Json(metadata),
                trans.get('file_hash')
            ))
            source_id = cur.fetchone()[0]
            sources_created += 1
        except psycopg2.errors.UniqueViolation:
            # File hash already exists (duplicate content)
            print(f"  ⚠️  Skipping {filename} - duplicate hash detected in database")
            conn.rollback()
            continue
        except Exception as e:
            print(f"  ❌ Error inserting source {filename}: {e}")
            conn.rollback()
            continue

        # 2. Create transcription
        cur.execute("""
            INSERT INTO transcriptions (source_id, full_text, word_count, language)
            VALUES (%s, %s, %s, %s)
        """, (
            source_id,
            trans['text'],
            trans['word_count'],
            trans['language']
        ))
        transcriptions_created += 1

        # 3. Create summaries (if available)
        summary = next((s for s in summaries if s['filename'] == filename), None)

        if summary and summary.get('has_summary'):
            # TL;DR summary
            cur.execute("""
                INSERT INTO summaries (source_id, summary_type, content, participants, topics, decisions, action_items, key_numbers)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                source_id,
                'tldr',
                summary['tldr'],
                Json(summary.get('participants', [])),
                Json(summary.get('topics', [])),
                Json(summary.get('decisions', [])),
                Json(summary.get('action_items', [])),
                Json(summary.get('key_numbers', []))
            ))

            # Detailed summary
            cur.execute("""
                INSERT INTO summaries (source_id, summary_type, content, participants, topics, decisions, action_items, key_numbers)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                source_id,
                'detailed',
                summary['detailed_summary'],
                Json(summary.get('participants', [])),
                Json(summary.get('topics', [])),
                Json(summary.get('decisions', [])),
                Json(summary.get('action_items', [])),
                Json(summary.get('key_numbers', []))
            ))

            summaries_created += 2

    conn.commit()
    conn.close()

    print(f"✅ Uploaded: {sources_created} sources, {transcriptions_created} transcriptions, {summaries_created} summaries")


# ===== STEP 6: UPLOAD TO QDRANT =====
def upload_to_qdrant(embeddings):
    """Upload embeddings to Qdrant."""
    print(f"\n🔍 Step 6: Uploading to Qdrant...")
    
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
    
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    collection_name = "unified_memory_audio"
    
    # Ensure collection exists
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
    for emb in embeddings:
        point_id = str(uuid.uuid4())
        
        points.append(PointStruct(
            id=point_id,
            vector=emb['embedding'],
            payload={
                'text': emb['text'],
                'source_file': emb['filename'],
                'source_date': emb['source_date'],
                'embed_type': emb['embed_type'],
                'duration_seconds': emb['duration_seconds']
            }
        ))
    
    client.upsert(collection_name=collection_name, points=points)
    
    print(f"✅ Uploaded {len(points)} vectors to Qdrant")


# ===== STEP 7: MOVE PROCESSED FILES =====
def move_processed_files(transcriptions):
    """Move processed files to Processati folder."""
    print(f"\n📦 Step 7: Moving {len(transcriptions)} processed files to Nextcloud...")
    
    import webdav3.client as wc
    
    options = {
        'webdav_hostname': NEXTCLOUD_URL,
        'webdav_login': NEXTCLOUD_USER,
        'webdav_password': NEXTCLOUD_PASS
    }
    
    client = wc.Client(options)
    
    # Create Processati folder
    processed_folder = PROCESSED_FOLDER.format(user=NEXTCLOUD_USER)
    try:
        client.mkdir(processed_folder)
        print(f"  ✅ Created folder: {processed_folder}")
    except:
        pass
    
    moved = 0
    for trans in transcriptions:
        filename = trans['filename']
        audio_folder = AUDIO_FOLDER.format(user=NEXTCLOUD_USER)
        
        remote_source = f"{audio_folder}{filename}"
        remote_dest = f"{processed_folder}{filename}"
        
        try:
            client.move(remote_path_from=remote_source, remote_path_to=remote_dest)
            print(f"  ✅ Moved: {filename}")
            moved += 1
        except Exception as e:
            print(f"  ⚠️  Error moving {filename}: {e}")
    
    print(f"✅ Moved {moved}/{len(transcriptions)} files to Audio_Processati")


# ===== DISPLAY RESULTS (NEW!) =====
def display_processing_results(transcriptions, summaries):
    """Display beautiful formatted output with properly formatted structured data."""
    for trans in transcriptions:
        filename = trans['filename']
        summary = next((s for s in summaries if s['filename'] == filename), None)

        print("\n" + "═" * 60)
        print(f"✅ PROCESSED: {filename}")
        print("═" * 60)

        # Duration and stats
        duration_min = trans['duration_seconds'] // 60
        duration_sec = trans['duration_seconds'] % 60
        print(f"\n⏱️  DURATION: {duration_min}m {duration_sec}s ({trans['duration_seconds']} seconds)")
        print(f"📝 TRANSCRIPTION: {trans['word_count']} words")

        # Quality metrics
        if trans.get('words_per_minute'):
            print(f"📊 QUALITY: {trans['words_per_minute']} words/min", end="")
            if trans.get('avg_confidence') and trans['avg_confidence'] > 0:
                print(f", confidence: {trans['avg_confidence']:.1%}")
            else:
                print()

        if summary and summary.get('has_summary'):
            print("\n" + "─" * 60)
            print("📊 TL;DR:")
            print(summary['tldr'])

            print("\n" + "─" * 60)
            print("📋 DETAILED SUMMARY:")
            print(summary['detailed_summary'])

            if summary.get('participants'):
                print("\n👥 PARTICIPANTS:")
                for p in summary['participants']:
                    print(f"  • {p}")

            if summary.get('mentioned_people'):
                print("\n🗣️  MENTIONED (not present):")
                for m in summary['mentioned_people']:
                    print(f"  • {m}")

            if summary.get('topics'):
                print("\n🏷️  TOPICS:")
                for t in summary['topics']:
                    print(f"  • {t}")

            # FIXED: Proper formatting for decisions
            if summary.get('decisions'):
                print("\n🎯 DECISIONS:")
                for d in summary['decisions']:
                    if isinstance(d, dict):
                        decision = d.get('decision', 'N/A')
                        by = d.get('by', 'Sconosciuto')
                        date = d.get('date', 'N/A')
                        print(f"  • {decision}")
                        print(f"    └─ Deciso da: {by} | Quando: {date}")
                    else:
                        print(f"  • {d}")

            # FIXED: Proper formatting for action items
            if summary.get('action_items'):
                print("\n✅ ACTION ITEMS:")
                for a in summary['action_items']:
                    if isinstance(a, dict):
                        task = a.get('task', 'N/A')
                        owner = a.get('owner', 'Sconosciuto')
                        deadline = a.get('deadline', 'Da definire')
                        print(f"  • [{owner}] {task}")
                        print(f"    └─ ⏰ Scadenza: {deadline}")
                    else:
                        print(f"  • {a}")

            # FIXED: Proper formatting for key numbers
            if summary.get('key_numbers'):
                print("\n💰 KEY NUMBERS:")
                for n in summary['key_numbers']:
                    if isinstance(n, dict):
                        amount = n.get('amount', 'N/A')
                        num_type = n.get('type', 'generic')
                        context = n.get('context', '')
                        print(f"  • {amount} ({num_type})")
                        if context:
                            print(f"    └─ {context}")
                    else:
                        print(f"  • {n}")
        else:
            print("\n📄 FULL TRANSCRIPTION:")
            print(trans['text'][:500] + ("..." if len(trans['text']) > 500 else ""))

        print("\n" + "═" * 60)


# ===== MAIN WORKFLOW =====
def main():
    print("=" * 60)
    print("🚀 AUDIO PROCESSING WORKFLOW v2.1 - FASTER-WHISPER")
    print("=" * 60)
    print(f"Started: {datetime.now()}")
    print("\nNEW in v2.1:")
    print("  ✅ Hash-based duplicate detection")
    print("  ✅ Faster-Whisper (3-5x faster + VAD)")
    print("  ✅ Quality metrics (words/min, confidence)")
    print("  ✅ Parallel summary processing")
    print("  ✅ Improved AI prompts (forced Italian)")
    print("  ✅ Beautiful formatted output\n")

    try:
        # Step 1: Download with hash-based tracking
        audio_files, file_metadata = download_new_audio()

        if not audio_files:
            print("\n✅ No new files to process. Exit.")
            return

        # Step 2: Transcription with quality checks
        transcriptions = transcribe_audio_batch(audio_files, file_metadata)

        if not transcriptions:
            print("\n❌ No transcriptions completed. Exit.")
            return

        # Step 3: Summaries with parallel processing
        summaries = create_summaries_ollama(transcriptions)

        # Step 4: Embeddings (optimized)
        embeddings = create_embeddings_ollama(transcriptions, summaries)

        # Step 5: Upload PostgreSQL with hash and quality metrics
        upload_to_postgres(transcriptions, summaries)

        # Step 6: Upload Qdrant
        upload_to_qdrant(embeddings)

        # Step 7: Move files to processed folder
        move_processed_files(transcriptions)

        # Display results with beautiful formatting
        display_processing_results(transcriptions, summaries)

        print("\n" + "=" * 60)
        print(f"✅ WORKFLOW COMPLETED - {datetime.now()}")
        print(f"   Transcribed: {len(transcriptions)} files")
        print(f"   Summaries: {sum(1 for s in summaries if s.get('has_summary'))} created")
        print(f"   Embeddings: {len(embeddings)}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ WORKFLOW ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
