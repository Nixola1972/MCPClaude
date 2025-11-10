#!/bin/bash
# Script per testare Ollama e vedere se genera correttamente i JSON

echo "=========================================="
echo "TEST 1: Ollama è attivo?"
echo "=========================================="
curl -s http://localhost:11434/api/tags | head -20

echo ""
echo ""
echo "=========================================="
echo "TEST 2: Lista modelli disponibili"
echo "=========================================="
curl -s http://localhost:11434/api/tags | jq '.models[].name' 2>/dev/null || curl -s http://localhost:11434/api/tags

echo ""
echo ""
echo "=========================================="
echo "TEST 3: Test generazione JSON con gemma3:12b"
echo "=========================================="

curl -s http://localhost:11434/api/generate -d '{
  "model": "gemma3:12b",
  "prompt": "IMPORTANTE: Rispondi SOLO con JSON valido.\n\nAnalizza questa trascrizione:\n\nMarco: Dobbiamo investire 1000 euro in Google Ads.\nSara: Sono d'\''accordo. Io mi occupo di contattare il cliente Rossi entro lunedì.\n\nESTRAI in formato JSON:\n1. participants: [\"Marco\", \"Sara\"]\n2. topics: [\"Budget marketing\"]\n3. decisions: [{\"decision\": \"Investire 1000 euro in Google Ads\", \"by\": \"Marco\", \"date\": \"Immediato\"}]\n4. action_items: [{\"task\": \"Contattare cliente Rossi\", \"owner\": \"Sara\", \"deadline\": \"Lunedì\"}]\n\nRispondi SOLO con JSON valido, nessun altro testo.",
  "stream": false,
  "format": "json",
  "options": {"temperature": 0.3}
}' | jq '.' 2>/dev/null || echo "jq non disponibile, output raw:"

echo ""
echo ""
echo "=========================================="
echo "COMANDI MANUALI UTILI"
echo "=========================================="
echo ""
echo "# Vedere se Ollama è attivo:"
echo "curl http://localhost:11434/api/tags"
echo ""
echo "# Vedere lista modelli:"
echo "ollama list"
echo ""
echo "# Testare gemma3:12b interattivo:"
echo "ollama run gemma3:12b"
echo ""
echo "# Vedere log Ollama (se in systemd):"
echo "journalctl -u ollama -f"
echo ""
echo "# Vedere processi Ollama:"
echo "ps aux | grep ollama"
echo ""
