#!/usr/bin/env python3
"""
MCP Server for Meetings Transcriptions - VPS Version
Runs on the VPS server where data resides (PostgreSQL, Qdrant, Ollama)
Accessible remotely via SSH tunnel
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
import requests
from datetime import datetime
from typing import Optional
import sys
import logging

# Setup logging (only to file, not stderr to avoid MCP protocol interference)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/mcp_server_meetings.log')
        # StreamHandler removed: stderr interferes with MCP JSON-RPC protocol
    ]
)
logger = logging.getLogger('mcp_server_meetings')

# Disable httpx logging to avoid stderr interference
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# Database config - LOCALHOST (running on same VPS)
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5433
POSTGRES_DB = "unified_memory"
POSTGRES_USER = "memory_user"
POSTGRES_PASS = "MemoryDB2025!Sicura"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# Ollama via Docker
OLLAMA_EMBED_API = "http://localhost:11434/api/embeddings"


def get_postgres_connection():
    """Create PostgreSQL connection."""
    try:
        return psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASS,
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        raise


def create_embedding(text: str) -> list:
    """Create embedding vector for text using Ollama."""
    try:
        response = requests.post(OLLAMA_EMBED_API, json={
            "model": "nomic-embed-text",
            "prompt": text
        }, timeout=30)

        if response.status_code == 200:
            return response.json()['embedding']
        else:
            logger.error(f"Embedding API error: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Embedding creation failed: {e}")
        return None


def search_meetings(query: str, limit: int = 5) -> dict:
    """
    Search meetings by semantic similarity.

    Args:
        query: Search query in natural language
        limit: Maximum number of results

    Returns:
        dict: Search results with meeting metadata
    """
    try:
        logger.info(f"Searching meetings: '{query}' (limit={limit})")

        # Create query embedding
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

        # Format results
        meetings = []
        for hit in results:
            meetings.append({
                'filename': hit.payload.get('source_file'),
                'date': hit.payload.get('source_date'),
                'text_snippet': hit.payload.get('text', '')[:300],
                'relevance_score': hit.score,
                'duration_seconds': hit.payload.get('duration_seconds')
            })

        logger.info(f"Found {len(meetings)} results")
        return {"results": meetings, "count": len(meetings)}

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"error": str(e)}


def get_transcription(filename: str) -> dict:
    """
    Get full transcription for a specific meeting.

    Args:
        filename: Name of the audio file

    Returns:
        dict: Full transcription with metadata
    """
    try:
        logger.info(f"Getting transcription: {filename}")

        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.source_id as filename,
                s.source_date,
                s.duration_seconds,
                t.full_text,
                t.word_count,
                t.language
            FROM sources s
            JOIN transcriptions t ON t.source_id = s.id
            WHERE s.source_id = %s
        """, (filename,))

        result = cur.fetchone()
        conn.close()

        if result:
            logger.info(f"Transcription found: {result['word_count']} words")
            return dict(result)
        else:
            logger.warning(f"Transcription not found: {filename}")
            return {"error": f"Meeting '{filename}' not found"}

    except Exception as e:
        logger.error(f"Get transcription failed: {e}")
        return {"error": str(e)}


def get_summary(filename: str) -> dict:
    """
    Get structured summary for a specific meeting.

    Args:
        filename: Name of the audio file

    Returns:
        dict: Summary with participants, topics, decisions, actions
    """
    try:
        logger.info(f"Getting summary: {filename}")

        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.source_id as filename,
                su.summary_type,
                su.content,
                su.participants,
                su.topics,
                su.decisions,
                su.action_items,
                su.key_numbers
            FROM sources s
            JOIN summaries su ON su.source_id = s.id
            WHERE s.source_id = %s AND su.summary_type = 'detailed'
        """, (filename,))

        result = cur.fetchone()
        conn.close()

        if result:
            logger.info(f"Summary found with {len(result.get('participants', []))} participants")
            return dict(result)
        else:
            logger.warning(f"Summary not found: {filename}")
            return {"error": f"Summary for '{filename}' not found"}

    except Exception as e:
        logger.error(f"Get summary failed: {e}")
        return {"error": str(e)}


def list_recent_meetings(days: int = 30, limit: int = 10) -> dict:
    """
    List recent meetings.

    Args:
        days: Number of days to look back
        limit: Maximum number of results

    Returns:
        dict: List of recent meetings with basic info
    """
    try:
        logger.info(f"Listing recent meetings: {days} days, limit {limit}")

        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.source_id as filename,
                s.source_date,
                s.duration_seconds,
                t.word_count,
                (SELECT COUNT(*) FROM summaries WHERE source_id = s.id) as has_summary
            FROM sources s
            LEFT JOIN transcriptions t ON t.source_id = s.id
            WHERE s.source_date >= NOW() - INTERVAL '%s days'
            ORDER BY s.source_date DESC
            LIMIT %s
        """, (days, limit))

        results = cur.fetchall()
        conn.close()

        meetings = [dict(r) for r in results]
        logger.info(f"Found {len(meetings)} recent meetings")

        return {"meetings": meetings, "count": len(meetings)}

    except Exception as e:
        logger.error(f"List recent meetings failed: {e}")
        return {"error": str(e)}


def get_action_items(owner: Optional[str] = None) -> dict:
    """
    Get action items from all meetings.

    Args:
        owner: Optional filter by owner name

    Returns:
        dict: List of action items with meeting context
    """
    try:
        logger.info(f"Getting action items (owner={owner})")

        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.source_id as filename,
                s.source_date,
                su.action_items
            FROM sources s
            JOIN summaries su ON su.source_id = s.id
            WHERE su.action_items IS NOT NULL AND su.action_items != '[]'
        """)

        results = cur.fetchall()
        conn.close()

        # Flatten action items
        all_actions = []
        for row in results:
            actions = row['action_items'] if isinstance(row['action_items'], list) else []
            for action in actions:
                if owner is None or action.get('owner', '').lower() == owner.lower():
                    all_actions.append({
                        'meeting': row['filename'],
                        'meeting_date': row['source_date'],
                        'task': action.get('task'),
                        'owner': action.get('owner'),
                        'deadline': action.get('deadline')
                    })

        logger.info(f"Found {len(all_actions)} action items")
        return {"action_items": all_actions, "count": len(all_actions)}

    except Exception as e:
        logger.error(f"Get action items failed: {e}")
        return {"error": str(e)}


def get_decisions() -> dict:
    """
    Get all decisions from meetings.

    Returns:
        dict: List of decisions with meeting context
    """
    try:
        logger.info("Getting all decisions")

        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.source_id as filename,
                s.source_date,
                su.decisions
            FROM sources s
            JOIN summaries su ON su.source_id = s.id
            WHERE su.decisions IS NOT NULL AND su.decisions != '[]'
        """)

        results = cur.fetchall()
        conn.close()

        # Flatten decisions
        all_decisions = []
        for row in results:
            decisions = row['decisions'] if isinstance(row['decisions'], list) else []
            for decision in decisions:
                all_decisions.append({
                    'meeting': row['filename'],
                    'meeting_date': row['source_date'],
                    'decision': decision.get('decision'),
                    'decided_by': decision.get('by'),
                    'date': decision.get('date')
                })

        logger.info(f"Found {len(all_decisions)} decisions")
        return {"decisions": all_decisions, "count": len(all_decisions)}

    except Exception as e:
        logger.error(f"Get decisions failed: {e}")
        return {"error": str(e)}


# MCP Server Protocol Handler
def handle_mcp_request(request: dict) -> dict:
    """Handle MCP protocol requests."""
    try:
        method = request.get('method')
        params = request.get('params', {})

        logger.info(f"MCP request: {method}")

        if method == 'initialize':
            return {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "meetings-mcp-server",
                    "version": "1.0.0"
                }
            }

        elif method == 'tools/list':
            return {
                "tools": [
                    {
                        "name": "search_meetings",
                        "description": "Search meetings by semantic similarity",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "limit": {"type": "integer", "default": 5}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "get_transcription",
                        "description": "Get full transcription for a meeting",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "filename": {"type": "string"}
                            },
                            "required": ["filename"]
                        }
                    },
                    {
                        "name": "get_summary",
                        "description": "Get structured summary for a meeting",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "filename": {"type": "string"}
                            },
                            "required": ["filename"]
                        }
                    },
                    {
                        "name": "list_recent_meetings",
                        "description": "List recent meetings",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "days": {"type": "integer", "default": 30},
                                "limit": {"type": "integer", "default": 10}
                            }
                        }
                    },
                    {
                        "name": "get_action_items",
                        "description": "Get action items from meetings",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "owner": {"type": "string"}
                            }
                        }
                    },
                    {
                        "name": "get_decisions",
                        "description": "Get all decisions from meetings",
                        "inputSchema": {
                            "type": "object"
                        }
                    }
                ]
            }

        elif method == 'tools/call':
            tool_name = params.get('name')
            tool_params = params.get('arguments', {})

            if tool_name == 'search_meetings':
                result = search_meetings(**tool_params)
            elif tool_name == 'get_transcription':
                result = get_transcription(**tool_params)
            elif tool_name == 'get_summary':
                result = get_summary(**tool_params)
            elif tool_name == 'list_recent_meetings':
                result = list_recent_meetings(**tool_params)
            elif tool_name == 'get_action_items':
                result = get_action_items(**tool_params)
            elif tool_name == 'get_decisions':
                result = get_decisions()
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            return {"content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]}

        else:
            return {"error": f"Unknown method: {method}"}

    except Exception as e:
        logger.error(f"MCP request handling failed: {e}")
        return {"error": str(e)}


def main():
    """Main MCP server loop - reads from stdin, writes to stdout."""
    logger.info("MCP Server starting...")
    logger.info(f"PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}")
    logger.info(f"Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")

    # Test connections
    try:
        conn = get_postgres_connection()
        conn.close()
        logger.info("PostgreSQL connection: OK")
    except Exception as e:
        logger.error(f"PostgreSQL connection: FAILED - {e}")
        sys.exit(1)

    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        logger.info("Qdrant connection: OK")
    except Exception as e:
        logger.error(f"Qdrant connection: FAILED - {e}")
        sys.exit(1)

    logger.info("MCP Server ready, waiting for requests...")

    # MCP protocol: read JSON-RPC from stdin, write to stdout
    for line in sys.stdin:
        try:
            request = json.loads(line)
            request_id = request.get('id')
            result = handle_mcp_request(request)

            # Build JSON-RPC response
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get('id') if 'request' in locals() else None,
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
