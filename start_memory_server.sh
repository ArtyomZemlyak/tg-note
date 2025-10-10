#!/bin/bash
# Start Memory MCP Server
# This server handles memory storage/retrieval operations

echo "Starting Memory MCP Server..."
echo "Host: 127.0.0.1"
echo "Port: 8765"
echo ""
echo "Server will run in the background. Logs will be saved to memory_server.log"
echo ""

# Start server in background
nohup python3 -m src.agents.mcp.memory.memory_server_http \
    --host 127.0.0.1 \
    --port 8765 \
    > memory_server.log 2>&1 &

SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"
echo "To check logs: tail -f memory_server.log"
echo "To stop server: kill $SERVER_PID"
echo ""

# Wait a moment for server to start
sleep 2

# Check if server is running
if ps -p $SERVER_PID > /dev/null; then
    echo "✓ Server is running"
    echo ""
    echo "You can now use memory storage operations:"
    echo "  - store_memory(content='...')"
    echo "  - retrieve_memory(query='...')"
    echo "  - list_categories()"
else
    echo "✗ Server failed to start. Check memory_server.log for errors"
fi
