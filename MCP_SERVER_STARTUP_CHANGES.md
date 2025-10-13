# MCP Memory Service Startup Changes

## Summary

This document describes the changes made to move vLLM/MLX server startup from "on first tool call" to "on MCP memory service startup".

## Problem Statement

Previously, the vLLM/MLX server would start automatically only when an Agent instance was first created (lazy initialization). This caused:

1. **Delayed first response**: The first agent call would be very slow as it waited for the server to start
2. **Poor user experience**: No clear indication that a server was starting
3. **Repeated startup attempts**: Multiple agent instances might try to start the server
4. **MLX compatibility issues**: No graceful handling when MLX was incompatible with the macOS version

## Solution

### New Startup Sequence

The new startup flow is:

```
1. MCP Memory Service starts
   ↓
2. vLLM/MLX server starts (if needed)
   ↓
3. Mem-agent initializes
   ↓
4. Agent ready to accept requests
```

### Changes Made

#### 1. Created Server Manager Module

**File**: `src/agents/mcp/memory/mem_agent_impl/server_manager.py`

New centralized module for managing vLLM and MLX server lifecycle:

- `ensure_server_started()`: Main entry point - starts appropriate server based on platform
- `start_vllm_server()`: Starts vLLM on Linux
- `start_mlx_server()`: Starts MLX on macOS (with compatibility checks)
- `is_server_running()`: Checks if server is already running
- `stop_server()`: Gracefully stops server on shutdown

**Key Features**:
- Platform detection (Linux → vLLM, macOS → MLX)
- MLX compatibility checking before attempting to start
- Detailed logging to separate log files
- Configurable timeout (default: 60 seconds)
- Graceful fallback to OpenRouter/OpenAI if server fails to start

#### 2. Modified MCP Memory Server Initialization

**File**: `src/agents/mcp/memory/memory_server.py`

Added server startup in the `__init__` method:

```python
# STEP 1: Start vLLM/MLX server if using mem-agent storage
storage_type = os.getenv("MEM_AGENT_STORAGE_TYPE", "json")
if storage_type == "mem-agent":
    logger.info("🔧 Detected mem-agent storage type")
    logger.info("🚀 Starting local LLM server (vLLM/MLX)...")
    
    from src.agents.mcp.memory.mem_agent_impl.server_manager import ensure_server_started
    
    server_started = ensure_server_started(timeout=60)
    if server_started:
        logger.info("✅ Local LLM server is ready")
    else:
        logger.warning("⚠️ Local LLM server not started - will use configured endpoint")
```

**Why Here?**
- Only starts server when `MEM_AGENT_STORAGE_TYPE=mem-agent`
- JSON/vector storage types don't need the server
- Server is ready before any agent instances are created

#### 3. Modified MCP Server (HTTP/SSE)

**File**: `src/agents/mcp/memory/mem_agent_impl/mcp_server.py`

Added server startup in the `run_server()` function:

```python
# STEP 1: Start vLLM/MLX server before initializing agent
logger.info("STEP 1: Starting local LLM server (vLLM/MLX)")
from .server_manager import ensure_server_started
server_started = ensure_server_started(timeout=60)

# STEP 2: Starting MCP server
logger.info("STEP 2: Starting MCP server")
mcp.run(transport="sse", host=host, port=port)
```

#### 4. Updated Agent Initialization

**File**: `src/agents/mcp/memory/mem_agent_impl/agent.py`

**Removed**: Automatic server startup on first agent creation

```python
# OLD: Auto-started server here
if not MEM_AGENT_BASE_URL and not MEM_AGENT_OPENAI_API_KEY:
    logger.info("⚠️  No explicit endpoint/key provided, ensuring local server...")
    self._ensure_local_server()

# NEW: Expects server to be already running
if MEM_AGENT_BASE_URL:
    logger.info(f"  Using endpoint: {MEM_AGENT_BASE_URL}")
elif MEM_AGENT_OPENAI_API_KEY:
    logger.info("  Using OpenRouter/OpenAI with API key")
else:
    logger.warning("⚠️  No endpoint or API key configured!")
    logger.warning("  Expected server to be started during MCP service initialization")
```

**Added**: MLX compatibility checking in `_ensure_local_server()` (kept for backward compatibility):

```python
# Check if MLX is available and compatible
try:
    import mlx.core as mx
    logger.debug("✅ MLX import successful, library is compatible")
except ImportError as mlx_error:
    logger.error("❌ MLX COMPATIBILITY ERROR")
    logger.error(f"  Error: {mlx_error}")
    logger.error("  Possible causes:")
    logger.error("  1. macOS version too old (MLX requires macOS 13.5+)")
    logger.error("  2. MLX not installed correctly")
    logger.error("  Solutions:")
    logger.error("  - Upgrade to macOS 13.5 or later, OR")
    logger.error("  - Set MEM_AGENT_OPENAI_API_KEY to use OpenRouter/OpenAI")
    return
```

## MLX Compatibility Fix

### Problem

The error occurred because:
```
ImportError: Symbol not found: _cblas_dgemm$NEWLAPACK
Referenced from: libmlx.dylib (built for macOS 13.5 which is newer than running OS)
```

The MLX library was compiled for macOS 13.5+ but the system was running an older version.

### Solution

Added comprehensive MLX compatibility checking:

1. **Before attempting to start MLX server**, check if `mlx.core` can be imported
2. **If import fails**, log detailed error message with solutions:
   - Upgrade macOS to 13.5+
   - Use OpenRouter/OpenAI instead
   - Reinstall compatible MLX version
3. **Gracefully fall back** to configured OpenRouter/OpenAI endpoint
4. **Continue operation** without crashing

### Benefits

- No more cryptic import errors that crash the service
- Clear instructions for users on how to fix the issue
- Graceful degradation to cloud endpoints
- Better user experience

## Configuration

### Environment Variables

- `MEM_AGENT_STORAGE_TYPE`: Set to `mem-agent` to enable server startup
- `MEM_AGENT_MODEL`: Model name to load (e.g., `driaforall/mem-agent`)
- `MEM_AGENT_HOST`: Server host (default: `127.0.0.1`)
- `MEM_AGENT_PORT`: Server port (default: `8000`)
- `MEM_AGENT_BASE_URL`: If set, skip local server and use this endpoint
- `MEM_AGENT_OPENAI_API_KEY`: If set, use OpenRouter/OpenAI instead

### Startup Behavior

| Configuration | Behavior |
|--------------|----------|
| `MEM_AGENT_STORAGE_TYPE=json` | No server startup |
| `MEM_AGENT_STORAGE_TYPE=mem-agent` + Linux | Start vLLM server |
| `MEM_AGENT_STORAGE_TYPE=mem-agent` + macOS | Start MLX server (with compatibility check) |
| `MEM_AGENT_BASE_URL` set | Skip local server, use endpoint |
| `MEM_AGENT_OPENAI_API_KEY` set | Skip local server, use OpenRouter/OpenAI |

## Logging

### Server Logs

Servers now log to dedicated files:

- **vLLM**: `logs/vllm_server.log` and `logs/vllm_server_errors.log`
- **MLX**: `logs/mlx_server.log` and `logs/mlx_server_errors.log`

### Startup Logging

Clear logging shows the startup sequence:

```
================================================================================
🚀 INITIALIZING MCP MEMORY SERVER (STDIO)
================================================================================

🔧 Detected mem-agent storage type
🚀 Starting local LLM server (vLLM/MLX)...

================================================================================
🚀 STARTING MLX SERVER
================================================================================
  Host: 127.0.0.1
  Port: 8000
  Model: driaforall/mem-agent
  Timeout: 60s
================================================================================

✅ MLX library is compatible
📋 MLX server process started (PID: 12345)
📄 Logs: logs/mlx_server.log
📄 Errors: logs/mlx_server_errors.log
⏳ Waiting for server to become ready...

================================================================================
✅ MLX server is ready at http://127.0.0.1:8000/v1
================================================================================
```

## Testing

To test the changes:

### 1. Test with mem-agent storage (Linux/vLLM)

```bash
export MEM_AGENT_STORAGE_TYPE=mem-agent
export MEM_AGENT_MODEL=meta-llama/Llama-3.2-3B-Instruct

python -m src.agents.mcp.memory.memory_server --user-id 1
```

### 2. Test with mem-agent storage (macOS/MLX)

```bash
export MEM_AGENT_STORAGE_TYPE=mem-agent
export MEM_AGENT_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit

python -m src.agents.mcp.memory.memory_server --user-id 1
```

### 3. Test with OpenRouter fallback

```bash
export MEM_AGENT_STORAGE_TYPE=mem-agent
export MEM_AGENT_OPENAI_API_KEY=your_key_here

python -m src.agents.mcp.memory.memory_server --user-id 1
```

### 4. Test with JSON storage (no server startup)

```bash
export MEM_AGENT_STORAGE_TYPE=json

python -m src.agents.mcp.memory.memory_server --user-id 1
```

## Benefits

1. **Faster first response**: Server is ready before any requests arrive
2. **Better visibility**: Clear logging of startup sequence
3. **Graceful error handling**: MLX compatibility issues are caught early
4. **Single startup point**: Only one place attempts to start the server
5. **Platform-aware**: Automatically chooses correct server for platform
6. **Configurable**: Easy to override with environment variables
7. **Backward compatible**: Existing configurations continue to work

## Migration Notes

### For Users

No configuration changes required! The system will:
- Automatically detect your platform
- Start the appropriate server
- Fall back to OpenRouter/OpenAI if needed

### For Developers

If you were manually starting servers:
1. Remove manual server startup code
2. Set appropriate environment variables
3. Let the MCP service handle server lifecycle

## Troubleshooting

### Server doesn't start

**Check logs**:
- `logs/vllm_server_errors.log` (Linux)
- `logs/mlx_server_errors.log` (macOS)

**Common issues**:
1. Model not downloaded - download first with `huggingface-cli download`
2. Port already in use - change `MEM_AGENT_PORT`
3. Insufficient memory - use a smaller model

### MLX compatibility error

**Solution 1**: Upgrade macOS to 13.5+

**Solution 2**: Use OpenRouter/OpenAI:
```bash
export MEM_AGENT_OPENAI_API_KEY=your_key
```

**Solution 3**: Use vLLM on Linux instead

### Server starts but requests timeout

**Check**:
1. Firewall settings
2. Server logs for errors
3. Model loading time (may need to increase timeout)

## Files Changed

1. ✅ `src/agents/mcp/memory/mem_agent_impl/server_manager.py` (NEW)
2. ✅ `src/agents/mcp/memory/memory_server.py` (MODIFIED)
3. ✅ `src/agents/mcp/memory/mem_agent_impl/mcp_server.py` (MODIFIED)
4. ✅ `src/agents/mcp/memory/mem_agent_impl/agent.py` (MODIFIED)

## Related Documentation

- [MCP Memory Integration](src/agents/mcp/memory/INTEGRATION.md)
- [Mem-Agent README](src/agents/mcp/memory/mem_agent_impl/README.md)
- [MCP Memory README](src/agents/mcp/memory/README.md)
