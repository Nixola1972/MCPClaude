#!/usr/bin/env python3
"""
Fixed MCP server code - handles 'initialized' notification correctly
"""

# This is the fix to add after line 378 in handle_mcp_request:

"""
        elif method == 'initialized':
            # This is a notification, no response needed
            logger.info("Client initialized notification received")
            return None
"""

# And update the main loop (lines 509-522) to:

"""
    for line in sys.stdin:
        try:
            request = json.loads(line)
            request_id = request.get('id')
            method = request.get('method')

            result = handle_mcp_request(request)

            # Notifications (no id) don't need a response
            if request_id is None:
                logger.info(f"Notification {method} processed, no response needed")
                continue

            # Build JSON-RPC response for requests
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

            print(json.dumps(response), flush=True)
"""
