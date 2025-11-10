#!/bin/bash
# Script per verificare lo stato completo del VPS

echo "=== 1. Stato container Qdrant ==="
docker ps | grep qdrant

echo ""
echo "=== 2. Test connessione Qdrant ==="
curl -s http://localhost:6333 | head -n 5

echo ""
echo "=== 3. Ultimi 30 righe log MCP server ==="
tail -n 30 /var/log/mcp_server_meetings.log

echo ""
echo "=== 4. Ultimi 30 righe stderr log ==="
tail -n 30 /var/log/mcp_server_meetings_stderr.log

echo ""
echo "=== 5. Test manuale MCP server ==="
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | timeout 5 python3 /opt/mcp_server_meetings/mcp_server_meetings.py
