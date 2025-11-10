#!/usr/bin/env python3
"""
MCP Server for Meetings Transcriptions
Exposes tools to search and query meeting data from PostgreSQL and Qdrant
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
import requests
from datetime import datetime
from typing import Optional

# Database config
POSTGRES_HOST = "srv778971.hstgr.cloud"
POSTGRES_PORT = 5433
POSTGRES_DB = "unified_memory"
POSTGRES_USER = "memory_user"
POSTGRES_PASS = "MemoryDB2025!Sicura"

QDRANT_HOST = "srv778971.hstgr.cloud"
QDRANT_PORT = 6333

OLLAMA_EMBED_API = "http://localhost:11434/api/embeddings"


def get_postgres_connection():
    """Create PostgreSQL connection."""
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASS,
        cursor_factory=RealDictCursor
    )


def create_embedding(text: str) -> list:
    """Create embedding vector for text using Ollama."""
    try:
        response = requests.post(OLLAMA_EMBED_API, json={
            "model": "nomic-embed-text",
            "prompt": text
        }, timeout=30)

        if response.status_code == 200:
            return response.json()['embedding']
    except Exception as e:
        print(f"Error creating embedding: {e}")

    return None


# ===== MCP TOOLS =====

def search_meetings(query: str, limit: int = 5) -> dict:
    """
    Semantic search across meeting transcriptions and summaries.

    Args:
        query: Natural language search query (e.g., "riunioni su fotovoltaico")
        limit: Maximum number of results (default: 5)

    Returns:
        Dictionary with search results including filename, relevance score, and summary
    """
    try:
        # Create embedding for query
        query_vector = create_embedding(query)
        if not query_vector:
            return {"error": "Failed to create query embedding"}

        # Search in Qdrant
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        results = client.search(
            collection_name="unified_memory_audio",
            query_vector=query_vector,
            limit=limit
        )

        # Fetch additional data from PostgreSQL
        conn = get_postgres_connection()
        cur = conn.cursor()

        output = []
        for result in results:
            filename = result.payload['source_file']
            score = result.score

            # Get full details from PostgreSQL
            cur.execute("""
                SELECT
                    s.source_id,
                    s.source_date,
                    s.duration_seconds,
                    s.metadata,
                    t.word_count,
                    sm.content as tldr,
                    sm.participants,
                    sm.topics,
                    sm.action_items
                FROM sources s
                LEFT JOIN transcriptions t ON s.id = t.source_id
                LEFT JOIN summaries sm ON s.id = sm.source_id AND sm.summary_type = 'tldr'
                WHERE s.source_id = %s
            """, (filename,))

            row = cur.fetchone()
            if row:
                output.append({
                    'filename': filename,
                    'relevance_score': round(score, 3),
                    'date': row['source_date'].isoformat() if row['source_date'] else None,
                    'duration_minutes': row['duration_seconds'] // 60 if row['duration_seconds'] else 0,
                    'word_count': row['word_count'],
                    'tldr': row['tldr'],
                    'participants': row['participants'] or [],
                    'topics': row['topics'] or [],
                    'action_items': row['action_items'] or []
                })

        cur.close()
        conn.close()

        return {
            'query': query,
            'results_count': len(output),
            'results': output
        }

    except Exception as e:
        return {"error": str(e)}


def get_transcription(filename: str) -> dict:
    """
    Get full transcription for a specific meeting.

    Args:
        filename: Audio filename (e.g., "Senza nome.m4a")

    Returns:
        Dictionary with complete transcription text and metadata
    """
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.source_id,
                s.source_date,
                s.duration_seconds,
                s.metadata,
                t.full_text,
                t.word_count,
                t.language
            FROM sources s
            JOIN transcriptions t ON s.id = t.source_id
            WHERE s.source_id = %s
        """, (filename,))

        row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            return {"error": f"Transcription not found for: {filename}"}

        result = {
            'filename': row['source_id'],
            'date': row['source_date'].isoformat() if row['source_date'] else None,
            'duration_minutes': row['duration_seconds'] // 60 if row['duration_seconds'] else 0,
            'word_count': row['word_count'],
            'language': row['language'],
            'quality_metrics': row['metadata'].get('quality_metrics', {}) if row['metadata'] else {},
            'full_transcription': row['full_text']
        }

        cur.close()
        conn.close()

        return result

    except Exception as e:
        return {"error": str(e)}


def get_summary(filename: str) -> dict:
    """
    Get AI-generated summary for a specific meeting.

    Args:
        filename: Audio filename (e.g., "Senza nome.m4a")

    Returns:
        Dictionary with TL;DR, detailed summary, and structured data
    """
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.source_id,
                s.source_date,
                s.duration_seconds,
                sm_tldr.content as tldr,
                sm_detailed.content as detailed_summary,
                sm_tldr.participants,
                sm_tldr.topics,
                sm_tldr.decisions,
                sm_tldr.action_items,
                sm_tldr.key_numbers
            FROM sources s
            LEFT JOIN summaries sm_tldr ON s.id = sm_tldr.source_id AND sm_tldr.summary_type = 'tldr'
            LEFT JOIN summaries sm_detailed ON s.id = sm_detailed.source_id AND sm_detailed.summary_type = 'detailed'
            WHERE s.source_id = %s
        """, (filename,))

        row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            return {"error": f"Summary not found for: {filename}"}

        result = {
            'filename': row['source_id'],
            'date': row['source_date'].isoformat() if row['source_date'] else None,
            'duration_minutes': row['duration_seconds'] // 60 if row['duration_seconds'] else 0,
            'tldr': row['tldr'],
            'detailed_summary': row['detailed_summary'],
            'participants': row['participants'] or [],
            'topics': row['topics'] or [],
            'decisions': row['decisions'] or [],
            'action_items': row['action_items'] or [],
            'key_numbers': row['key_numbers'] or []
        }

        cur.close()
        conn.close()

        return result

    except Exception as e:
        return {"error": str(e)}


def list_recent_meetings(limit: int = 10) -> dict:
    """
    List recent meetings ordered by date.

    Args:
        limit: Maximum number of meetings to return (default: 10)

    Returns:
        List of meetings with basic info and TL;DR
    """
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.source_id,
                s.source_date,
                s.duration_seconds,
                s.metadata,
                t.word_count,
                sm.content as tldr,
                sm.participants,
                sm.topics
            FROM sources s
            LEFT JOIN transcriptions t ON s.id = t.source_id
            LEFT JOIN summaries sm ON s.id = sm.source_id AND sm.summary_type = 'tldr'
            WHERE s.source_type = 'audio'
            ORDER BY s.source_date DESC
            LIMIT %s
        """, (limit,))

        rows = cur.fetchall()

        meetings = []
        for row in rows:
            meetings.append({
                'filename': row['source_id'],
                'date': row['source_date'].isoformat() if row['source_date'] else None,
                'duration_minutes': row['duration_seconds'] // 60 if row['duration_seconds'] else 0,
                'word_count': row['word_count'],
                'quality': row['metadata'].get('quality_metrics', {}) if row['metadata'] else {},
                'tldr': row['tldr'],
                'participants': row['participants'] or [],
                'topics': row['topics'] or []
            })

        cur.close()
        conn.close()

        return {
            'total_meetings': len(meetings),
            'meetings': meetings
        }

    except Exception as e:
        return {"error": str(e)}


def get_action_items(owner: Optional[str] = None) -> dict:
    """
    Get all action items, optionally filtered by owner.

    Args:
        owner: Filter by person name (e.g., "Claudia"). If None, returns all.

    Returns:
        List of action items with meeting context
    """
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.source_id,
                s.source_date,
                sm.action_items
            FROM sources s
            JOIN summaries sm ON s.id = sm.source_id
            WHERE sm.summary_type = 'tldr' AND sm.action_items IS NOT NULL
            ORDER BY s.source_date DESC
        """)

        rows = cur.fetchall()

        all_actions = []
        for row in rows:
            filename = row['source_id']
            date = row['source_date'].isoformat() if row['source_date'] else None

            for action in row['action_items']:
                if isinstance(action, dict):
                    action_owner = action.get('owner', '')

                    # Filter by owner if specified
                    if owner and owner.lower() not in action_owner.lower():
                        continue

                    all_actions.append({
                        'meeting': filename,
                        'date': date,
                        'task': action.get('task', 'N/A'),
                        'owner': action_owner,
                        'deadline': action.get('deadline', 'N/A')
                    })

        cur.close()
        conn.close()

        return {
            'filter_owner': owner,
            'total_actions': len(all_actions),
            'actions': all_actions
        }

    except Exception as e:
        return {"error": str(e)}


def get_decisions(date_from: Optional[str] = None) -> dict:
    """
    Get all decisions taken in meetings.

    Args:
        date_from: Optional start date in ISO format (e.g., "2025-11-01")

    Returns:
        List of decisions with meeting context
    """
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        query = """
            SELECT
                s.source_id,
                s.source_date,
                sm.decisions
            FROM sources s
            JOIN summaries sm ON s.id = sm.source_id
            WHERE sm.summary_type = 'tldr' AND sm.decisions IS NOT NULL
        """

        params = []
        if date_from:
            query += " AND s.source_date >= %s"
            params.append(date_from)

        query += " ORDER BY s.source_date DESC"

        cur.execute(query, params)
        rows = cur.fetchall()

        all_decisions = []
        for row in rows:
            filename = row['source_id']
            date = row['source_date'].isoformat() if row['source_date'] else None

            for decision in row['decisions']:
                if isinstance(decision, dict):
                    all_decisions.append({
                        'meeting': filename,
                        'date': date,
                        'decision': decision.get('decision', 'N/A'),
                        'decided_by': decision.get('by', 'N/A'),
                        'implementation_date': decision.get('date', 'N/A')
                    })

        cur.close()
        conn.close()

        return {
            'date_filter': date_from,
            'total_decisions': len(all_decisions),
            'decisions': all_decisions
        }

    except Exception as e:
        return {"error": str(e)}


# ===== MCP SERVER MAIN =====

def main():
    """MCP Server stdio interface."""
    import sys

    # Read from stdin, write to stdout (MCP protocol)
    for line in sys.stdin:
        try:
            request = json.loads(line)

            method = request.get('method')
            params = request.get('params', {})

            # Route to appropriate tool
            if method == 'search_meetings':
                result = search_meetings(**params)
            elif method == 'get_transcription':
                result = get_transcription(**params)
            elif method == 'get_summary':
                result = get_summary(**params)
            elif method == 'list_recent_meetings':
                result = list_recent_meetings(**params)
            elif method == 'get_action_items':
                result = get_action_items(**params)
            elif method == 'get_decisions':
                result = get_decisions(**params)
            elif method == 'list_tools':
                # Return available tools
                result = {
                    'tools': [
                        {
                            'name': 'search_meetings',
                            'description': 'Semantic search across meeting transcriptions',
                            'parameters': {
                                'query': 'str (required)',
                                'limit': 'int (optional, default=5)'
                            }
                        },
                        {
                            'name': 'get_transcription',
                            'description': 'Get full transcription for a meeting',
                            'parameters': {
                                'filename': 'str (required)'
                            }
                        },
                        {
                            'name': 'get_summary',
                            'description': 'Get AI summary for a meeting',
                            'parameters': {
                                'filename': 'str (required)'
                            }
                        },
                        {
                            'name': 'list_recent_meetings',
                            'description': 'List recent meetings',
                            'parameters': {
                                'limit': 'int (optional, default=10)'
                            }
                        },
                        {
                            'name': 'get_action_items',
                            'description': 'Get action items, optionally filtered by owner',
                            'parameters': {
                                'owner': 'str (optional)'
                            }
                        },
                        {
                            'name': 'get_decisions',
                            'description': 'Get decisions from meetings',
                            'parameters': {
                                'date_from': 'str ISO format (optional)'
                            }
                        }
                    ]
                }
            else:
                result = {"error": f"Unknown method: {method}"}

            # Send response
            response = {
                'id': request.get('id'),
                'result': result
            }

            print(json.dumps(response), flush=True)

        except Exception as e:
            error_response = {
                'id': request.get('id') if 'request' in locals() else None,
                'error': str(e)
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
