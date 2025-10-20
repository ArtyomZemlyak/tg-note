# Troubleshooting

## Tests: `pytest: command not found`

Some environments (e.g., system Python 3.13) install packages into user site without exposing console scripts on PATH. Use the module form instead:

```bash
python -m pytest
```

Alternatively, ensure your virtual environment is active so `pytest` is on PATH.

## Git push: authentication errors

If pushing to `https://github.com/...` fails with username/password errors:

- Switch to SSH remote: `git remote set-url origin git@github.com:user/repo.git`
- Or configure a credential helper: `git config credential.helper store`
- Or use a personal access token (PAT) in the HTTPS URL.

`GitOperations` detects HTTPS and logs guidance. It also avoids double credential injection.

## Missing optional dependencies

Vector search and some agents require extras. Install as needed:

```bash
pip install -e ".[vector-search]"
pip install -e ".[mcp]"
pip install -e ".[mem-agent]"
```

## MCP Connection Errors

### Error: "No module named 'starlette'"

**Symptom:**
```
WARNING  | src.mcp.qwen_config_generator:_detect_available_tools:110 | 
[QwenMCPConfig] Failed to detect available tools: No module named 'starlette'
```

**Cause:** Missing FastMCP dependencies (fastmcp requires starlette).

**Solution:**
```bash
# Install MCP extras
pip install -e ".[mcp]"

# Or install fastmcp directly
pip install fastmcp
```

The system will automatically fall back to basic memory tools if fastmcp is not installed.

### Error: "This event loop is already running"

**Symptom:**
```
ERROR | __main__:reindex_vector - ❌ Error in reindexing: This event loop is already running
```

**Cause:** The MCP server functions (`vector_search`, `reindex_vector`) are called from an async context (FastMCP server) but try to run async operations in an already-running event loop.

**Solution:**
This issue is fixed in the latest version by automatically using `nest-asyncio` when needed. Ensure you have the MCP extras installed:

```bash
poetry install --extras mcp
# or
pip install nest-asyncio
```

The code now automatically detects when an event loop is running and uses `nest-asyncio` to handle nested async operations.

### Error: "SSE connection timeout"

**Symptom:**
```
ERROR    | src.mcp.client:_connect_sse:255 | [MCPClient] SSE connection timeout
ERROR    | src.mcp.client:connect:127 | [MCPClient] Failed to connect: 
SSE connection timeout - server did not respond
```

**Possible Causes:**
1. MCP Hub server is not running
2. URL is incorrect (check `MCP_HUB_URL` environment variable)
3. Network connectivity issues
4. Firewall blocking the connection

**Solutions:**

**Docker mode:**
```bash
# 1. Check if MCP Hub container is running
docker ps | grep mcp-hub

# 2. Check MCP Hub health
curl http://localhost:8765/health

# 3. Check docker-compose logs
docker-compose logs mcp-hub

# 4. Verify MCP_HUB_URL is correct
echo $MCP_HUB_URL
# Should be: http://mcp-hub:8765/sse

# 5. Restart MCP Hub service
docker-compose restart mcp-hub
```

**Standalone mode:**
```bash
# 1. Check if MCP Hub process is running
ps aux | grep mcp_hub_server

# 2. Check MCP Hub health
curl http://127.0.0.1:8765/health

# 3. Check logs
tail -f logs/mcp_hub.log

# 4. Restart the application
python -m main
```

### Error: "Failed to parse SSE data"

**Symptom:**
```
WARNING  | src.mcp.client:_connect_sse:232 | [MCPClient] Failed to parse SSE data: 
Expecting value: line 1 column 1 (char 0)
```

**Cause:** MCP Hub server sent empty or invalid SSE data.

**Solutions:**
1. Update to the latest version (this error is fixed in recent versions)
2. Check MCP Hub server logs for errors
3. Verify MCP Hub is using FastMCP 0.1.0 or later

### Error: "Failed to connect to MCP Hub"

**Symptom:**
```
WARNING  | src.mcp.tools_description:get_mcp_tools_description:48 | 
[MCPToolsDescription] Failed to connect to MCP Hub at http://mcp-hub:8765/sse
```

**Diagnostic Steps:**

1. **Verify MCP Hub URL:**
   ```bash
   # Check environment variable
   echo $MCP_HUB_URL
   
   # Test with curl
   curl http://mcp-hub:8765/health
   ```

2. **Check Docker network connectivity (Docker mode):**
   ```bash
   # Check if services can communicate
   docker-compose exec bot ping mcp-hub
   
   # Verify network configuration
   docker network inspect tg-note_default
   ```

3. **Check firewall rules:**
   ```bash
   # Linux: check if port 8765 is accessible
   sudo netstat -tulpn | grep 8765
   
   # macOS: check if port 8765 is accessible
   lsof -i :8765
   ```

4. **Enable debug logging:**
   ```python
   # In your code or config
   import logging
   logging.getLogger("src.mcp.client").setLevel(logging.DEBUG)
   logging.getLogger("src.mcp.tools_description").setLevel(logging.DEBUG)
   ```
