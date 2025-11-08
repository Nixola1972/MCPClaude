#!/usr/bin/env python3
"""
Query completa di tutti i dati salvati nel sistema
Esegui sul PC con GPU dove hai il workflow
"""

import psycopg2
from qdrant_client import QdrantClient
from datetime import datetime

# ===== CONFIGURAZIONE =====
POSTGRES_HOST = "srv778971.hstgr.cloud"
POSTGRES_PORT = 5433
POSTGRES_DB = "unified_memory"
POSTGRES_USER = "memory_user"
POSTGRES_PASS = "MemoryDB2025!Sicura"

QDRANT_HOST = "srv778971.hstgr.cloud"
QDRANT_PORT = 6333

print("=" * 80)
print(f"🔍 QUERY COMPLETA UNIFIED MEMORY SYSTEM - {datetime.now()}")
print("=" * 80)

# ===== POSTGRESQL =====
print("\n🐘 POSTGRESQL - unified_memory")
print("-" * 80)

try:
    conn = psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        dbname=POSTGRES_DB, user=POSTGRES_USER,
        password=POSTGRES_PASS
    )
    cur = conn.cursor()

    # Statistiche generali
    cur.execute("SELECT * FROM database_stats")
    stats = cur.fetchone()
    print(f"\n📊 STATISTICHE DATABASE:")
    print(f"  Total entities: {stats[0]}")
    print(f"  Total observations: {stats[1]}")
    print(f"  Total relations: {stats[2]}")
    print(f"  Total sources: {stats[3]}")
    print(f"  Unique source types: {stats[4]}")

    # Tutte le sources
    cur.execute("""
        SELECT id, source_type, source_id, source_date, created_at
        FROM sources
        ORDER BY created_at DESC
    """)
    sources = cur.fetchall()
    print(f"\n📁 SOURCES ({len(sources)} totali):")
    for i, row in enumerate(sources, 1):
        print(f"\n  [{i}] ID:{row[0]}")
        print(f"      Type: {row[1]}")
        print(f"      File: {row[2]}")
        print(f"      Source Date: {row[3]}")
        print(f"      Created At: {row[4]}")

    # Tutte le entities (escluso General_Context)
    cur.execute("""
        SELECT e.id, e.name, e.entity_type, e.created_at, e.metadata,
               COUNT(o.id) as obs_count
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        WHERE e.name != 'General_Context'
        GROUP BY e.id, e.name, e.entity_type, e.created_at, e.metadata
        ORDER BY e.created_at DESC
    """)
    entities = cur.fetchall()
    print(f"\n👥 ENTITIES ({len(entities)} totali, escluso General_Context):")
    for i, row in enumerate(entities, 1):
        print(f"\n  [{i}] ID:{row[0]} | {row[1]} ({row[2]})")
        print(f"      Created: {row[3]}")
        print(f"      Metadata: {row[4]}")
        print(f"      Observations: {row[5]}")

    # Tutte le observations per entity
    cur.execute("""
        SELECT e.name, e.entity_type, o.content, s.source_id, o.confidence, o.created_at
        FROM observations o
        JOIN entities e ON o.entity_id = e.id
        JOIN sources s ON o.source_id = s.id
        WHERE e.name != 'General_Context'
        ORDER BY o.created_at DESC
    """)
    observations = cur.fetchall()
    print(f"\n💭 OBSERVATIONS ({len(observations)} totali):")
    for i, row in enumerate(observations, 1):
        print(f"\n  [{i}] Entity: {row[0]} ({row[1]})")
        print(f"      Content: {row[2]}")
        print(f"      Source: {row[3]}")
        print(f"      Confidence: {row[4]}")
        print(f"      Created: {row[5]}")

    conn.close()
    print("\n✅ PostgreSQL query completata")

except Exception as e:
    print(f"\n❌ Errore PostgreSQL: {e}")
    import traceback
    traceback.print_exc()

# ===== QDRANT =====
print("\n" + "=" * 80)
print("🔍 QDRANT - unified_memory_audio")
print("-" * 80)

try:
    client = QdrantClient(host=QDRANT_HOST, port=6333)

    # Info collection
    collection_info = client.get_collection("unified_memory_audio")
    print(f"\n📊 Collection Info:")
    print(f"  Total vectors: {collection_info.points_count}")
    print(f"  Vector size: {collection_info.config.params.vectors.size}")
    print(f"  Distance: {collection_info.config.params.vectors.distance}")

    # Recupera TUTTI i points (non solo 10!)
    results = client.scroll(
        collection_name="unified_memory_audio",
        limit=1000,  # Aumentato da 10 a 1000
        with_payload=True,
        with_vectors=False
    )

    points = results[0]
    print(f"\n📝 TRASCRIZIONI ({len(points)} chunks recuperati):")

    # Raggruppa per source_file
    files_dict = {}
    for point in points:
        source_file = point.payload.get('source_file')
        if source_file not in files_dict:
            files_dict[source_file] = []
        files_dict[source_file].append(point)

    print(f"\n📂 File unici: {len(files_dict)}")

    for file_name, file_points in files_dict.items():
        print(f"\n{'=' * 60}")
        print(f"🎤 FILE: {file_name}")
        print(f"{'=' * 60}")
        print(f"Chunks: {len(file_points)}")
        print(f"Data: {file_points[0].payload.get('source_date')}")

        # Ordina per chunk_index
        file_points_sorted = sorted(file_points, key=lambda p: p.payload.get('chunk_index', 0))

        print(f"\nTesto completo ricostruito:")
        print("-" * 60)
        for chunk in file_points_sorted:
            chunk_text = chunk.payload.get('text', '')
            chunk_idx = chunk.payload.get('chunk_index', 0)
            print(f"[Chunk {chunk_idx}] {chunk_text}")
        print("-" * 60)

    # Mostra anche gli IDs dei points per debug
    print(f"\n🔢 DEBUG - Point IDs in Qdrant:")
    for point in points:
        print(f"  ID: {point.id} | File: {point.payload.get('source_file')} | Chunk: {point.payload.get('chunk_index')}")

    print("\n✅ Qdrant query completata")

except Exception as e:
    print(f"\n❌ Errore Qdrant: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print(f"✅ QUERY COMPLETATA - {datetime.now()}")
print("=" * 80)
