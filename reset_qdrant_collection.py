#!/usr/bin/env python3
"""
Reset Qdrant collection - Elimina e ricrea collection pulita
Usa solo se vuoi ripartire da zero con Qdrant
"""

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

QDRANT_HOST = "srv778971.hstgr.cloud"
QDRANT_PORT = 6333
COLLECTION_NAME = "unified_memory_audio"

print("=" * 60)
print("🔄 RESET QDRANT COLLECTION")
print("=" * 60)

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Elimina collection esistente
try:
    client.delete_collection(COLLECTION_NAME)
    print(f"✅ Collection '{COLLECTION_NAME}' eliminata")
except Exception as e:
    print(f"ℹ️  Collection non esistente o errore: {e}")

# Ricrea collection pulita
client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

print(f"✅ Collection '{COLLECTION_NAME}' ricreata pulita")
print("\nAdesso puoi rieseguire il workflow e i dati non verranno più sovrascritti!")
print("=" * 60)
