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
SUMMARY_MIN_DURATION = 300  # 5 minutes in seconds

# ===== STEP 1: DOWNLOAD AUDIO =====
def download_new_audio():
    """Download new audio files from Nextcloud."""
    print("📥 Step 1: Download audio from Nextcloud...")
    
    # Clean local queue
    import shutil
    if LOCAL_AUDIO_DIR.exists():
        shutil.rmtree(LOCAL_AUDIO_DIR)
    LOCAL_AUDIO_DIR.mkdir(exist_ok=True)
    
    import webdav3.client as wc
    
    options = {
        'webdav_hostname': NEXTCLOUD_URL,
        'webdav_login': NEXTCLOUD_USER,
        'webdav_password': NEXTCLOUD_PASS
    }
    
    client = wc.Client(options)
    
    # Get processed files list
    processed_files = set()
    try:
        processed_folder = PROCESSED_FOLDER.format(user=NEXTCLOUD_USER)
        processed_files = set(client.list(processed_folder))
        print(f"  ℹ️  Found {len(processed_files)} already processed files")
    except Exception:
        print(f"  ℹ️  Processed folder not yet created (first run)")
    
    # Download new files
    audio_folder = AUDIO_FOLDER.format(user=NEXTCLOUD_USER)
    remote_files = client.list(audio_folder)
    
    downloaded = 0
    skipped = 0
    for remote_file in remote_files:
        if remote_file.endswith(('.wav', '.m4a', '.mp3', '.flac')):
            if remote_file in processed_files:
                print(f"  ⏭️  Skipped (already processed): {remote_file}")
                skipped += 1
                continue
            
            local_path = LOCAL_AUDIO_DIR / Path(remote_file).name
            print(f"  ⬇️  Downloading: {remote_file}")
            client.download_sync(
                remote_path=f"{audio_folder}{remote_file}",
                local_path=str(local_path)
            )
            downloaded += 1
    
    print(f"✅ Downloaded {downloaded} new files (skipped {skipped} already processed)")
    return list(LOCAL_AUDIO_DIR.glob("*.wav")) + list(LOCAL_AUDIO_DIR.glob("*.m4a")) + list(LOCAL_AUDIO_DIR.glob("*.mp3"))


# ===== STEP 2: TRANSCRIPTION =====
def transcribe_audio_batch(audio_files):
    """Transcribe audio files with Whisper."""
    print(f"\n🎤 Step 2: Transcribing {len(audio_files)} files with Whisper...")
    
    import whisper
    import torch
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Device: {device}")
    
    if device == "cpu":
        print("⚠️  WARNING: GPU not available, using CPU (very slow!)")
    
    model = whisper.load_model(WHISPER_MODEL, device=device)
    
    transcriptions = []
    
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n  [{i}/{len(audio_files)}] Transcribing: {audio_file.name}")
        
        try:
            result = model.transcribe(
                str(audio_file),
                language="it",
                task="transcribe",
                word_timestamps=False,
                initial_prompt="Riunione aziendale professionale."
            )
            
            # Calculate duration (approximate from file size or use Whisper segments)
            duration_seconds = sum(seg['end'] for seg in result['segments']) if result['segments'] else 0
            
            transcription = {
                'filename': audio_file.name,
                'text': result['text'].strip(),
                'segments': result['segments'],
                'language': result['language'],
                'duration_seconds': int(duration_seconds),
                'word_count': len(result['text'].split()),
                'timestamp': datetime.now().isoformat()
            }
            
            transcriptions.append(transcription)
            
            print(f"    ✅ Transcribed: {len(transcription['text'])} chars, {transcription['word_count']} words, {transcription['duration_seconds']}s")
        
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
    
    print(f"\n✅ Transcriptions completed: {len(transcriptions)}/{len(audio_files)}")
    return transcriptions


# ===== STEP 3: SUMMARIES (NEW!) =====
def create_summaries_ollama(transcriptions):
    """Create intelligent summaries (only for audio >5 min)."""
    print(f"\n📝 Step 3: Creating summaries...")
    
    all_summaries = []
    
    for trans in transcriptions:
        duration = trans['duration_seconds']
        filename = trans['filename']
        
        print(f"\n  Processing: {filename} ({duration}s)")
        
        # Decision: summary or not?
        if duration < SUMMARY_MIN_DURATION:
            print(f"    ⏭️  Skipped (too short, <{SUMMARY_MIN_DURATION}s)")
            all_summaries.append({
                'filename': filename,
                'has_summary': False
            })
            continue
        
        print(f"    🧠 Generating summaries...")
        
        # Prompt for structured summary
        prompt = f"""Analizza questa trascrizione e crea un riassunto strutturato.

TRASCRIZIONE ({trans['word_count']} parole):
{trans['text']}

ESTRAI (in formato JSON):
1. participants: lista nomi persone menzionate ["Marco", "Sara"]
2. topics: argomenti principali discussi ["budget Q1", "cloud migration"]
3. decisions: decisioni prese [{"decision": "...", "by": "...", "date": "..."}]
4. action_items: azioni da fare [{"task": "...", "owner": "...", "deadline": "..."}]
5. key_numbers: numeri importanti [{"amount": "50k", "type": "budget", "context": "..."}]
6. detailed_summary: riassunto dettagliato (300-500 parole)
7. tldr: riassunto ultra-conciso (1-2 frasi, max 50 parole)

Rispondi SOLO in JSON valido, niente altro testo.
"""
        
        try:
            response = requests.post(OLLAMA_API, json={
                "model": "gemma3:12b",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.3}
            }, timeout=180)
            
            if response.status_code == 200:
                result = response.json()
                summary_json = json.loads(result['response'])
                
                all_summaries.append({
                    'filename': filename,
                    'has_summary': True,
                    'participants': summary_json.get('participants', []),
                    'topics': summary_json.get('topics', []),
                    'decisions': summary_json.get('decisions', []),
                    'action_items': summary_json.get('action_items', []),
                    'key_numbers': summary_json.get('key_numbers', []),
                    'detailed_summary': summary_json.get('detailed_summary', ''),
                    'tldr': summary_json.get('tldr', '')
                })
                
                print(f"    ✅ Summaries created")
                print(f"       - Participants: {len(summary_json.get('participants', []))}")
                print(f"       - Topics: {len(summary_json.get('topics', []))}")
                print(f"       - Decisions: {len(summary_json.get('decisions', []))}")
                print(f"       - Action items: {len(summary_json.get('action_items', []))}")
            else:
                print(f"    ❌ Ollama error: {response.status_code}")
                all_summaries.append({'filename': filename, 'has_summary': False})
        
        except Exception as e:
            print(f"    ❌ Error creating summary: {e}")
            all_summaries.append({'filename': filename, 'has_summary': False})
    
    print(f"\n✅ Summaries completed: {sum(1 for s in all_summaries if s['has_summary'])}/{len(all_summaries)}")
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
    """Upload to PostgreSQL using new schema v2.0."""
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
        
        # 1. Create source
        cur.execute("""
            INSERT INTO sources (source_type, source_id, source_date, duration_seconds, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            'audio',
            filename,
            trans['timestamp'],
            trans['duration_seconds'],
            Json({'word_count': trans['word_count'], 'language': trans['language']})
        ))
        source_id = cur.fetchone()[0]
        sources_created += 1
        
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
    """Display beautiful formatted output."""
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
            
            if summary.get('topics'):
                print("\n🏷️  TOPICS:")
                for t in summary['topics']:
                    print(f"  • {t}")
            
            if summary.get('decisions'):
                print("\n🎯 DECISIONS:")
                for d in summary['decisions']:
                    print(f"  • {d}")
            
            if summary.get('action_items'):
                print("\n✅ ACTION ITEMS:")
                for a in summary['action_items']:
                    print(f"  • {a}")
            
            if summary.get('key_numbers'):
                print("\n💰 KEY NUMBERS:")
                for n in summary['key_numbers']:
                    print(f"  • {n}")
        else:
            print("\n📄 FULL TRANSCRIPTION:")
            print(trans['text'][:500] + ("..." if len(trans['text']) > 500 else ""))
        
        print("\n" + "═" * 60)


# ===== MAIN WORKFLOW =====
def main():
    print("=" * 60)
    print("🚀 AUDIO PROCESSING WORKFLOW v2.0 - MCP-OPTIMIZED")
    print("=" * 60)
    print(f"Started: {datetime.now()}\n")
    
    try:
        # Step 1: Download
        audio_files = download_new_audio()
        
        if not audio_files:
            print("\n✅ No new files to process. Exit.")
            return
        
        # Step 2: Transcription
        transcriptions = transcribe_audio_batch(audio_files)
        
        if not transcriptions:
            print("\n❌ No transcriptions completed. Exit.")
            return
        
        # Step 3: Summaries (NEW!)
        summaries = create_summaries_ollama(transcriptions)
        
        # Step 4: Embeddings (OPTIMIZED!)
        embeddings = create_embeddings_ollama(transcriptions, summaries)
        
        # Step 5: Upload PostgreSQL (NEW SCHEMA!)
        upload_to_postgres(transcriptions, summaries)
        
        # Step 6: Upload Qdrant
        upload_to_qdrant(embeddings)
        
        # Step 7: Move files
        move_processed_files(transcriptions)
        
        # Display results (NEW!)
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
