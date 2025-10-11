# Comprehensive Tracing for MCP Memory Server and Mem-Agent

## Summary

Added detailed tracing to all MCP memory server and mem-agent components to help debug and monitor operations.

## Changes Made

### 1. Memory Server (STDIO) - `src/agents/mcp/memory/memory_server.py`

**Added tracing for:**
- ✅ Server startup with full configuration display
- ✅ Storage type initialization (JSON/Vector/Mem-Agent)
- ✅ Environment variables logging
- ✅ Model and backend information
- ✅ Every tool call (store_memory, retrieve_memory, list_categories)
- ✅ Request/response details with emoji markers
- ✅ Error handling with detailed context

**Key features:**
- 🚀 Startup banner with all settings
- 📊 Tool execution tracing
- 📥 Request logging with IDs
- 📤 Response logging with size
- ❌ Error logging with full context

### 2. Memory Server (HTTP) - `src/agents/mcp/memory/memory_server_http.py`

**Added tracing for:**
- ✅ Server startup with HTTP/SSE configuration
- ✅ Per-user storage initialization
- ✅ Storage creation with model loading
- ✅ Every tool call with user context
- ✅ Request parameters logging
- ✅ Response results logging

**Key features:**
- 🚀 HTTP server startup banner
- 👥 Multi-user storage tracking
- 📊 Per-request tracing
- ♻️ Storage reuse detection
- 📈 Result statistics

### 3. Mem-Agent MCP Server - `src/agents/mcp/memory/mem_agent_impl/mcp_server.py`

**Added tracing for:**
- ✅ Server startup configuration
- ✅ Agent instance creation
- ✅ Tool calls (chat_with_memory, query_memory, save_to_memory, list_memory_structure)
- ✅ Request/response logging
- ✅ Error handling

**Key features:**
- 🤖 Agent initialization tracking
- 💬 Chat operation logging
- 🔍 Query operation logging
- ♻️ Agent instance reuse detection

### 4. Mem-Agent Core - `src/agents/mcp/memory/mem_agent_impl/agent.py`

**Added tracing for:**
- ✅ Agent initialization with all settings
- ✅ Model client setup (vLLM/OpenAI)
- ✅ Memory path configuration
- ✅ System prompt loading
- ✅ Chat message processing
- ✅ Tool execution loop
- ✅ Python code execution
- ✅ Local server auto-start (vLLM/MLX)

**Key features:**
- 🤖 Complete agent lifecycle tracing
- 🧠 Model response logging
- 🐍 Code execution tracking
- 🔄 Tool turn counting
- 🎯 Response part extraction

### 5. Model Client - `src/agents/mcp/memory/mem_agent_impl/model.py`

**Added tracing for:**
- ✅ Client creation (OpenAI/vLLM)
- ✅ Model request preparation
- ✅ Message history logging
- ✅ Token estimation
- ✅ Model response reception
- ✅ Error handling

**Key features:**
- 🔧 Client setup logging
- 📤 Request details
- 📥 Response details
- 📊 Message statistics

### 6. Memory Factory - `src/agents/mcp/memory/memory_factory.py`

**Added tracing for:**
- ✅ Storage type selection
- ✅ Factory creation process
- ✅ Model loading for each storage type
- ✅ Configuration parameters
- ✅ Error handling with fallback

**Key features:**
- 🏭 Factory operation logging
- 📦 Model loading tracking
- ⚙️ Configuration display
- ❌ Detailed error messages

### 7. MemAgent Storage - `src/agents/mcp/memory/memory_mem_agent_storage.py`

**Added tracing for:**
- ✅ Storage initialization
- ✅ Agent instance creation
- ✅ Store operations
- ✅ Retrieve operations
- ✅ Instruction building
- ✅ Agent chat interactions

**Key features:**
- 🗄️ Storage lifecycle tracking
- 💾 Store operation logging
- 🔍 Retrieve operation logging
- 📝 Instruction generation tracking

## Tracing Features

### Emoji Markers
- 🚀 - Startup/Initialization
- ✅ - Success
- ❌ - Error
- ⚠️ - Warning
- 📊 - Statistics/Info
- 📥 - Incoming request
- 📤 - Outgoing response
- 🔧 - Configuration
- 💬 - Chat/Communication
- 🔍 - Search/Query
- 💾 - Storage operation
- 🧠 - Model operation
- 🐍 - Python code execution
- 🔄 - Loop/Iteration
- ♻️ - Reuse/Cache hit

### Log Levels
- **INFO**: High-level operations (startup, tool calls, completion)
- **DEBUG**: Detailed information (parameters, previews, intermediate steps)
- **ERROR**: Errors with full context and stack traces

### Information Logged

#### Startup:
- Storage type (JSON/Vector/Mem-Agent)
- Model name
- Backend (vLLM/MLX/OpenRouter/Transformers/auto)
- Memory paths
- All environment variables
- Configuration parameters

#### Runtime:
- Every request received
- Request parameters
- Tool being called
- User ID (for multi-user servers)
- Content length/preview
- Model responses
- Response length/preview
- Execution time hints
- Tool turn counts
- Error details with full stack traces

#### Model Operations:
- Model client creation
- Request preparation
- Message history size
- Token estimation
- Response reception
- Response length

## Usage

### View Logs

All logs are written to `logs/` directory:

```bash
# Memory MCP Server (STDIO)
tail -f logs/memory_mcp.log
tail -f logs/memory_mcp_errors.log

# Memory HTTP Server
tail -f logs/memory_http.log
tail -f logs/memory_http_errors.log

# Mem-Agent MCP Server
tail -f logs/mem_agent_mcp_server.log
tail -f logs/mem_agent_mcp_server_errors.log

# Mem-Agent Core
tail -f logs/mem_agent.log
tail -f logs/mem_agent_errors.log

# vLLM Server (if auto-started)
tail -f logs/vllm_server.log
tail -f logs/vllm_server_errors.log

# MLX Server (if auto-started on macOS)
tail -f logs/mlx_server.log
tail -f logs/mlx_server_errors.log
```

### Run with Debug Logging

```bash
# STDIO server
python -m src.agents.mcp.memory.memory_server --log-level DEBUG

# HTTP server
python -m src.agents.mcp.memory.memory_server_http --log-level DEBUG

# Set environment for more tracing
export MEM_AGENT_STORAGE_TYPE=mem-agent
export MEM_AGENT_MODEL=driaforall/mem-agent
export MEM_AGENT_BACKEND=vllm
export MEM_AGENT_MAX_TOOL_TURNS=20

python -m src.agents.mcp.memory.memory_server_http --log-level DEBUG
```

## Benefits

1. **Full Visibility**: Every operation is traced from start to finish
2. **Easy Debugging**: Detailed error messages with context
3. **Performance Monitoring**: Response sizes and operation counts
4. **Configuration Validation**: All settings logged at startup
5. **User Tracking**: Multi-user operations clearly marked
6. **Model Monitoring**: Model requests and responses tracked
7. **Storage Type Visibility**: Clear indication of JSON/Vector/Mem-Agent mode

## Example Output

```
================================================================================
🚀 STARTING MCP MEMORY SERVER (HTTP/SSE)
================================================================================

🔧 Server Configuration:
  🏗️  Host: 127.0.0.1
  🔌 Port: 8765
  👥 Mode: Multi-user (per-user storage)
  💾 Storage type: mem-agent
  🎮 Backend: vllm
  📦 Model: driaforall/mem-agent

📋 Environment Variables:
  - MEM_AGENT_STORAGE_TYPE: mem-agent
  - MEM_AGENT_MODEL: driaforall/mem-agent
  - MEM_AGENT_BACKEND: vllm
  - MEM_AGENT_MAX_TOOL_TURNS: 20

ℹ️  Note: Each user's storage is isolated at data/memory/user_{user_id}/
================================================================================

============================================================
🚀 INITIALIZING STORAGE FOR USER 12345
============================================================
📁 Data directory: /workspace/data/memory/user_12345
💾 Storage type: mem-agent

📋 Configuration:
  - MEM_AGENT_STORAGE_TYPE: mem-agent
  - MEM_AGENT_MODEL: driaforall/mem-agent
  - MEM_AGENT_BACKEND: vllm

🔧 Creating mem-agent storage via factory...
  📦 Model: driaforall/mem-agent
  🎮 Backend: vllm
✅ Successfully created mem-agent storage for user 12345
============================================================

💾 STORE_MEMORY called
  User: 12345
  Category: tasks
  Content length: 156 chars
  Tags: ['important', 'todo']
  
💬 Chatting with agent to store information...
✅ Store completed successfully
```

## Files Modified

1. `src/agents/mcp/memory/memory_server.py` - STDIO server
2. `src/agents/mcp/memory/memory_server_http.py` - HTTP server
3. `src/agents/mcp/memory/mem_agent_impl/mcp_server.py` - Mem-agent MCP server
4. `src/agents/mcp/memory/mem_agent_impl/agent.py` - Mem-agent core
5. `src/agents/mcp/memory/mem_agent_impl/model.py` - Model client
6. `src/agents/mcp/memory/memory_factory.py` - Storage factory
7. `src/agents/mcp/memory/memory_mem_agent_storage.py` - MemAgent storage

## Next Steps

If issues persist after these changes:

1. Check logs in `logs/` directory
2. Look for error messages with ❌ marker
3. Verify environment variables are set correctly
4. Check that models are available
5. Verify network connectivity for API endpoints
6. Check file permissions for data directories
