# MCP Servers Logging

Complete guide to logging configuration for all MCP servers (Memory MCP, Mem-Agent, vLLM).

## Overview

All MCP servers have comprehensive logging with:

- **File logging** with automatic rotation (10 MB per file)
- **Log retention** (7 days, compressed after rotation)
- **Console output** for real-time monitoring
- **Error tracking** with full stack traces
- **Centralized log directory** (`logs/mcp_servers/`)

## Log Directory Structure

```
logs/
└── mcp_servers/
    ├── memory_mcp.log              # Memory MCP server detailed logs
    ├── memory_mcp_stdout.log       # Memory MCP server stdout/stderr
    ├── mem_agent.log               # Mem-Agent server detailed logs  
    ├── mem_agent_stdout.log        # Mem-Agent stdout/stderr
    ├── vllm_server_latest.log      # vLLM server logs (symlink to latest)
    ├── vllm_server_latest_error.log # vLLM errors (symlink to latest)
    ├── vllm_server_YYYYMMDD_HHMMSS.log # vLLM timestamped logs
    └── pids/                       # Process ID files
        ├── memory_mcp.pid
        ├── mem_agent.pid
        └── vllm_server.pid
```

## Server Management

### Using the Management Script

The easiest way to manage MCP servers with proper logging:

```bash
# Start all servers
./scripts/manage_mcp_servers.sh start

# Start specific server
./scripts/manage_mcp_servers.sh start memory
./scripts/manage_mcp_servers.sh start mem-agent
./scripts/manage_mcp_servers.sh start vllm

# Stop servers
./scripts/manage_mcp_servers.sh stop all
./scripts/manage_mcp_servers.sh stop memory

# Restart servers
./scripts/manage_mcp_servers.sh restart all

# Check status
./scripts/manage_mcp_servers.sh status

# View logs (live tail)
./scripts/manage_mcp_servers.sh logs memory
./scripts/manage_mcp_servers.sh logs mem-agent 100  # last 100 lines
./scripts/manage_mcp_servers.sh logs vllm
```

### Manual Server Start (with logging)

#### Memory MCP Server

```bash
python3 -m src.agents.mcp.memory.memory_server_http \
    --host 127.0.0.1 \
    --port 8765 \
    --log-file logs/mcp_servers/memory_mcp.log \
    --log-level INFO
```

Options:
- `--log-file`: Path to log file (default: `logs/mcp_servers/memory_mcp.log`)
- `--log-level`: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

#### Mem-Agent MCP Server

```bash
python3 -m src.agents.mcp.memory.mem_agent_impl.mcp_server \
    --host 127.0.0.1 \
    --port 8766 \
    --log-file logs/mcp_servers/mem_agent.log \
    --log-level INFO
```

Options:
- `--log-file`: Path to log file (default: `logs/mcp_servers/mem_agent.log`)
- `--log-level`: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

#### vLLM Server

```bash
python3 scripts/start_vllm_server.py \
    --model driaforall/mem-agent \
    --host 127.0.0.1 \
    --port 8001 \
    --log-dir logs/mcp_servers
```

Options:
- `--log-dir`: Directory for logs (default: `logs/mcp_servers`)
- `--model`: Model to load (default: `driaforall/mem-agent`)
- `--gpu-memory-utilization`: GPU memory usage (default: 0.9)

## Log Formats

### Detailed File Logs

Format with full context for debugging:

```
2025-10-10 10:41:22 | INFO     | __main__:main:217 - Starting memory HTTP MCP server
2025-10-10 10:41:22 | ERROR    | __main__:store_memory:106 - Error storing memory: Connection timeout
Traceback (most recent call last):
  File "/workspace/src/agents/mcp/memory/memory_server_http.py", line 100, in store_memory
    result = storage.store(...)
```

Fields:
- Timestamp (YYYY-MM-DD HH:mm:ss)
- Log level
- Module:Function:Line number
- Log message
- Stack trace (for errors)

### Console Logs

Simplified format for real-time monitoring:

```
10:41:22 | INFO     | Starting memory HTTP MCP server
10:41:23 | ERROR    | Failed to connect to storage
```

## Log Levels

### DEBUG
Most detailed logging for development and troubleshooting:
- All function calls with parameters
- Database queries
- Network requests/responses
- Internal state changes

**When to use**: Development, detailed troubleshooting

### INFO (Default)
General operational information:
- Server start/stop
- Successful operations
- Configuration loaded
- Connections established

**When to use**: Production monitoring, normal operations

### WARNING
Potentially problematic situations:
- Deprecated features used
- Performance issues
- Fallback operations triggered
- Non-critical errors recovered

**When to use**: Production with alerting on warnings

### ERROR
Error events that still allow operation:
- Failed requests
- Connection failures
- Invalid input
- Recoverable exceptions

**When to use**: Always enabled

## Log Rotation

All logs automatically rotate to prevent disk space issues:

- **Rotation trigger**: When file reaches 10 MB
- **Retention**: 7 days of logs
- **Compression**: Old logs are gzip compressed
- **Naming**: `logfile.log`, `logfile.log.1.gz`, `logfile.log.2.gz`, etc.

Example:
```
memory_mcp.log           # Current log
memory_mcp.log.1.gz      # Yesterday (compressed)
memory_mcp.log.2.gz      # 2 days ago (compressed)
...
memory_mcp.log.7.gz      # 7 days ago (will be deleted on next rotation)
```

## Monitoring Logs

### Real-time Monitoring

```bash
# Watch all errors across all MCP servers
tail -f logs/mcp_servers/*.log | grep ERROR

# Monitor specific server
tail -f logs/mcp_servers/memory_mcp.log

# Monitor multiple servers
tail -f logs/mcp_servers/memory_mcp.log logs/mcp_servers/mem_agent.log

# Watch for specific patterns
tail -f logs/mcp_servers/memory_mcp.log | grep -E "ERROR|WARNING"
```

### Log Analysis

```bash
# Count errors in last hour
grep "ERROR" logs/mcp_servers/memory_mcp.log | grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')"

# Find most common errors
grep "ERROR" logs/mcp_servers/*.log | sort | uniq -c | sort -rn | head -10

# Search for specific issue
grep -r "Connection timeout" logs/mcp_servers/

# Check server startup times
grep "Starting.*MCP server" logs/mcp_servers/*.log
```

## Error Handling

### Memory MCP Server Errors

All MCP tool calls are wrapped with error handling:

```python
@mcp.tool()
def store_memory(content: str, ...) -> dict:
    try:
        logger.debug(f"Storing memory: category={category}")
        result = storage.store(...)
        logger.info(f"Memory stored successfully: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Error storing memory: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to store: {str(e)}"}
```

Errors include:
- Full stack trace in log file
- User-friendly error message returned to client
- Request context (parameters, user ID, etc.)

### Mem-Agent Server Errors

Same pattern with additional LLM-specific error handling:

```python
@mcp.tool()
async def chat_with_memory(question: str, ...) -> str:
    try:
        logger.debug(f"chat_with_memory called: question_length={len(question)}")
        # ... agent logic ...
        logger.info("chat_with_memory completed successfully")
        return response.reply
    except Exception as e:
        logger.error(f"Error in chat_with_memory: {e}", exc_info=True)
        return f"Error: {str(e)}"
```

### vLLM Server Errors

vLLM server wrapper captures both stdout and stderr separately:

- Standard output → `vllm_server_latest.log`
- Error output → `vllm_server_latest_error.log`

## Troubleshooting

### Server Won't Start

1. **Check logs**:
   ```bash
   cat logs/mcp_servers/memory_mcp.log
   cat logs/mcp_servers/memory_mcp_stdout.log
   ```

2. **Common issues**:
   - Port already in use
   - Missing dependencies
   - Permissions issues
   - Configuration errors

3. **Enable debug logging**:
   ```bash
   ./scripts/manage_mcp_servers.sh stop memory
   python3 -m src.agents.mcp.memory.memory_server_http \
       --log-level DEBUG \
       --log-file logs/mcp_servers/memory_mcp_debug.log
   ```

### High Memory Usage

Check detailed memory allocation:

```bash
# Enable DEBUG logging
./scripts/manage_mcp_servers.sh stop all
# Restart with DEBUG level
python3 -m src.agents.mcp.memory.memory_server_http --log-level DEBUG

# Monitor memory usage
ps aux | grep memory_server_http
```

### Connection Errors

1. **Check server is running**:
   ```bash
   ./scripts/manage_mcp_servers.sh status
   ```

2. **Check network connectivity**:
   ```bash
   curl http://127.0.0.1:8765/sse
   ```

3. **Check logs for connection errors**:
   ```bash
   grep -i "connection" logs/mcp_servers/memory_mcp.log
   ```

### Performance Issues

1. **Enable performance logging** (DEBUG level shows timing):
   ```bash
   # Restart with DEBUG
   ./scripts/manage_mcp_servers.sh restart memory
   # Edit: modify start command to use --log-level DEBUG
   ```

2. **Analyze slow operations**:
   ```bash
   # Find operations taking > 1s
   grep -E "took [1-9][0-9]*\.[0-9]+s" logs/mcp_servers/*.log
   ```

## Log Cleanup

### Manual Cleanup

```bash
# Remove old compressed logs
find logs/mcp_servers -name "*.gz" -mtime +7 -delete

# Remove old PID files
rm -f logs/mcp_servers/pids/*.pid

# Archive logs before cleanup
tar czf logs_backup_$(date +%Y%m%d).tar.gz logs/mcp_servers/
mv logs_backup_*.tar.gz /path/to/archive/
```

### Automated Cleanup (Cron)

Add to crontab (`crontab -e`):

```bash
# Clean up old MCP server logs daily at 2 AM
0 2 * * * find /path/to/workspace/logs/mcp_servers -name "*.gz" -mtime +7 -delete

# Archive logs weekly
0 3 * * 0 cd /path/to/workspace && tar czf logs_backup_$(date +\%Y\%m\%d).tar.gz logs/mcp_servers/ && mv logs_backup_*.tar.gz /archive/
```

## Integration with Application Logging

MCP servers use `loguru` which is compatible with the main application logging system.

### Forwarding to Central Log Aggregator

```python
from loguru import logger

# Add handler for central logging (e.g., Syslog, Graylog, etc.)
logger.add(
    "syslog://logserver:514",
    level="WARNING",
    format="{message}",
)
```

### Structured Logging

For machine-readable logs:

```python
logger.add(
    "logs/mcp_servers/memory_mcp.json",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    serialize=True,  # Output as JSON
)
```

## Best Practices

1. **Use appropriate log levels**:
   - Production: `INFO` or `WARNING`
   - Development: `DEBUG`
   - Critical systems: `ERROR` only

2. **Monitor log file sizes**:
   ```bash
   du -sh logs/mcp_servers/
   ```

3. **Set up alerting** for ERROR level logs:
   ```bash
   # Example: Email on errors
   tail -f logs/mcp_servers/*.log | grep ERROR | mail -s "MCP Server Error" admin@example.com
   ```

4. **Regular log review**:
   - Weekly: Review WARNING and ERROR logs
   - Monthly: Analyze patterns and trends
   - Quarterly: Adjust log levels and retention

5. **Backup important logs**:
   - Before major updates
   - After incidents
   - Periodically (weekly/monthly)

## See Also

- [MCP Server Management](./production.md#mcp-servers)
- [Monitoring and Alerting](./production.md#monitoring)
- [Troubleshooting Guide](../development/troubleshooting.md)
