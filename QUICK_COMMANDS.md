# Quick Commands - Memory Services Logging

## Start Servers

### MCP Hub Server (HTTP/SSE)
```bash
python -m src.agents.mcp.mcp_hub_server
```

### MCP Hub (Mem-Agent mode)
```bash
export MEM_AGENT_STORAGE_TYPE="mem-agent"
export MEM_AGENT_MODEL="driaforall/mem-agent"
export MEM_AGENT_BACKEND="vllm"  # or "auto", "mlx", "transformers"
python -m src.agents.mcp.mcp_hub_server
```

### MCP Hub (Debug mode)
```bash
python -m src.agents.mcp.mcp_hub_server --log-level DEBUG
```

### Memory MCP Server (stdio mode)
```bash
python -m src.agents.mcp.memory.memory_server --log-level DEBUG
```

## View Logs

### Real-time Log Viewing
```bash
# MCP Hub server
tail -f logs/mcp_hub.log

# MCP Hub errors
tail -f logs/mcp_hub_errors.log

# Mem-agent
tail -f logs/mem_agent.log

# Mem-agent errors
tail -f logs/mem_agent_errors.log

# vLLM server
tail -f logs/vllm_server.log

# vLLM errors
tail -f logs/vllm_server_errors.log

# All logs at once
tail -f logs/*.log
```

### Search Logs
```bash
# Check storage type
grep "Storage type" logs/memory_http.log

# Check initialization
grep "initialized successfully" logs/memory_http.log

# Check tool calls
grep "called" logs/memory_http.log

# Check errors only
cat logs/memory_http_errors.log

# Search for specific error
grep -i "timeout" logs/*.log
```

## Diagnostic Commands

### Check if server is running
```bash
# MCP Hub SSE endpoint
curl http://127.0.0.1:8765/sse

# Check vLLM server
curl http://127.0.0.1:8001/v1/models
```

### List all log files
```bash
ls -lh logs/
```

### Check recent errors
```bash
tail -50 logs/*_errors.log
```

### Monitor all activity
```bash
watch -n 1 'tail -20 logs/memory_http.log'
```

## Environment Variables

### Set Mem-Agent Mode
```bash
export MEM_AGENT_STORAGE_TYPE="mem-agent"
export MEM_AGENT_MODEL="driaforall/mem-agent"
export MEM_AGENT_BACKEND="vllm"  # or "auto", "mlx", "transformers"
```

### Set Vector Mode
```bash
export MEM_AGENT_STORAGE_TYPE="vector"
export MEM_AGENT_MODEL="BAAI/bge-m3"
```

### Set JSON Mode (default)
```bash
export MEM_AGENT_STORAGE_TYPE="json"
```

### Set Memory Path
```bash
export KB_PATH="/path/to/knowledge/base"
export MEM_AGENT_MEMORY_POSTFIX="memory"
```

## Clean Up

### Remove old logs
```bash
rm logs/*.log.*.zip
```

### Clean all logs
```bash
rm -rf logs/*
```

### Check log sizes
```bash
du -sh logs/*
```

## Testing

### Quick Test
```bash
# Terminal 1: Start server with debug
export MEM_AGENT_STORAGE_TYPE="mem-agent"
python -m src.agents.mcp.memory.memory_server_http --log-level DEBUG

# Terminal 2: Watch logs
tail -f logs/memory_http.log

# Terminal 3: Test with curl (if HTTP API available)
# Or use qwen CLI to test tools
```

### Verify Logging Works
```bash
# Start MCP Hub
python -m src.agents.mcp.mcp_hub_server &

# Wait a second
sleep 2

# Check logs were created
ls -lh logs/

# Should see:
# mcp_hub.log
# mcp_hub_errors.log
```

## Troubleshooting

### No logs created?
```bash
# Check if logs directory exists
mkdir -p logs

# Check permissions
chmod 755 logs

# Try running with debug
python -m src.agents.mcp.mcp_hub_server --log-level DEBUG
```

### Server not starting?
```bash
# Check error logs
cat logs/memory_http_errors.log

# Check if port is already in use
lsof -i :8765

# Try different port
python -m src.agents.mcp.mcp_hub_server --port 8766
```

### Mem-agent mode not working?
```bash
# Verify environment variables
echo $MEM_AGENT_STORAGE_TYPE
echo $MEM_AGENT_MODEL

# Check initialization in logs
grep "Storage type" logs/memory_http.log
grep "initialized successfully" logs/memory_http.log

# Check for errors
tail -50 logs/memory_http_errors.log
```

### vLLM server not starting?
```bash
# Check vLLM logs
tail -100 logs/vllm_server_errors.log

# Check if vLLM is installed
python -c "import vllm; print(vllm.__version__)"

# Check GPU availability
nvidia-smi  # Linux only
```

## One-Liner Diagnostics

```bash
# Full diagnostic
echo "=== Logs ===" && ls -lh logs/ && \
echo "=== Recent Activity ===" && tail -20 logs/memory_http.log && \
echo "=== Recent Errors ===" && tail -20 logs/memory_http_errors.log && \
echo "=== Environment ===" && env | grep MEM_AGENT

# Quick health check
grep -E "initialized successfully|Starting.*server|ERROR" logs/memory_http.log | tail -10
```
