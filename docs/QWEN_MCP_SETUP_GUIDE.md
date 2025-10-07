## Qwen CLI MCP Integration - Setup Guide

Complete guide to using MCP (Model Context Protocol) with Qwen Code CLI agent.

---

## 🎯 What This Does

When you enable MCP for `QwenCodeCLIAgent`, the system will:

1. **Generate `.qwen/settings.json`** configuration files
2. **Configure mem-agent MCP server** for memory storage/retrieval
3. **Start standalone MCP server** when qwen CLI runs
4. **Make MCP tools available** to the LLM

The LLM will have access to these tools:
- `store_memory` - Store information for later retrieval
- `retrieve_memory` - Search and retrieve stored information
- `list_categories` - List all memory categories

---

## 📋 Prerequisites

### 1. Install Qwen CLI

```bash
npm install -g @qwen-code/qwen-code@latest
```

### 2. Authenticate

```bash
qwen
# Follow OAuth prompts to authenticate
```

### 3. Configure Approval Mode (IMPORTANT!)

```bash
qwen
/approval-mode yolo --project
```

This allows the agent to use tools automatically without manual approval.

---

## 🚀 Quick Start

### Option 1: Automatic Setup (Recommended)

Simply create an agent with MCP enabled:

```python
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

agent = QwenCodeCLIAgent(
    config={
        "enable_mcp": True,
        "user_id": 123  # Your user ID
    },
    working_directory="/path/to/knowledge_base"
)

# MCP is now configured automatically!
# Check ~/.qwen/settings.json to see the configuration
```

**What happens:**
1. ✅ Generates `~/.qwen/settings.json` (global config)
2. ✅ Generates `/path/to/knowledge_base/.qwen/settings.json` (project config)
3. ✅ Configures mem-agent MCP server
4. ✅ Ready to use!

---

### Option 2: Manual Configuration

If you want to configure MCP without creating an agent:

```python
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config
from pathlib import Path

# Setup MCP configuration
saved_paths = setup_qwen_mcp_config(
    user_id=123,
    kb_path=Path("/path/to/kb"),
    global_config=True
)

print(f"Configuration saved to: {saved_paths}")
```

---

## 📁 Generated Configuration

### Location 1: `~/.qwen/settings.json` (Global)

```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "/usr/bin/python3",
      "args": [
        "/path/to/project/src/agents/mcp/mem_agent_server.py",
        "--user-id",
        "123"
      ],
      "cwd": "/path/to/project",
      "timeout": 10000,
      "trust": true,
      "description": "Memory storage and retrieval agent"
    }
  },
  "allowMCPServers": ["mem-agent"]
}
```

### Location 2: `<kb-path>/.qwen/settings.json` (Project-specific)

Same structure, but applies only to this knowledge base directory.

---

## 🔧 How It Works

### Architecture

```
┌─────────────────────────────────────┐
│       Python Process                │
│                                     │
│  ┌──────────────────┐               │
│  │ QwenCodeCLIAgent │               │
│  └────────┬─────────┘               │
│           │                         │
│           │ subprocess              │
└───────────┼─────────────────────────┘
            │ stdin/stdout
            ▼
┌─────────────────────────────────────┐
│   Node.js Process (qwen CLI)        │
│                                     │
│  ┌──────────────────┐               │
│  │  Qwen LLM        │               │
│  └────────┬─────────┘               │
│           │                         │
│           ▼                         │
│  ┌──────────────────┐               │
│  │ MCP Client       │               │
│  │ (built-in)       │               │
│  └────────┬─────────┘               │
│           │                         │
│           │ Reads ~/.qwen/settings.json
│           │                         │
│           ▼                         │
│  Starts MCP Servers                 │
└───────────┬─────────────────────────┘
            │ stdio
            ▼
┌─────────────────────────────────────┐
│   Python Process (MCP Server)       │
│                                     │
│  ┌──────────────────┐               │
│  │ mem_agent_server │               │
│  │  (standalone)    │               │
│  └────────┬─────────┘               │
│           │                         │
│           ▼                         │
│  ┌──────────────────┐               │
│  │ MemoryStorage    │               │
│  └────────┬─────────┘               │
│           │                         │
│           ▼                         │
│  data/memory/user_123/memory.json   │
└─────────────────────────────────────┘
```

### Data Flow

1. **User sends message** to Telegram bot
2. **QwenCodeCLIAgent** processes message
3. **Qwen CLI starts** (reads `.qwen/settings.json`)
4. **Qwen CLI launches** `mem_agent_server.py` as subprocess
5. **MCP server connects** via stdio
6. **LLM gets tool list** (store_memory, retrieve_memory, etc.)
7. **LLM can call tools** as needed
8. **Memories stored** in `data/memory/user_123/memory.json`

---

## 🧪 Testing the Setup

### Test 1: Verify Configuration

```bash
# Check global config
cat ~/.qwen/settings.json

# Check project config
cat /path/to/kb/.qwen/settings.json
```

You should see `mem-agent` in `mcpServers`.

---

### Test 2: Run MCP Server Manually

```bash
# Run standalone MCP server
python -m src.agents.mcp.mem_agent_server --user-id 123

# Server should start and wait for input
# Press Ctrl+C to stop
```

---

### Test 3: Test with Qwen CLI

```bash
cd /path/to/knowledge_base

# Run qwen CLI (will auto-connect to MCP servers)
qwen

# In qwen CLI, try using memory tools:
# "Store the following in memory: Project deadline is Dec 15"
# "What deadlines do I have?"
```

---

### Test 4: Run Example Script

```bash
python examples/qwen_mcp_integration_example.py
```

This will:
- Create agent with MCP
- Generate configuration
- Test MCP server
- Show stored memories

---

## 📂 Data Storage

### Memory Files Location

```
data/
└── memory/
    ├── user_123/
    │   └── memory.json      ← User 123's memories
    ├── user_456/
    │   └── memory.json      ← User 456's memories
    └── shared/
        └── memory.json      ← Shared memories (no user_id)
```

### Memory Format

```json
[
  {
    "id": 1,
    "content": "Project deadline: December 15, 2025",
    "category": "tasks",
    "metadata": {},
    "created_at": "2025-10-07T10:30:00",
    "updated_at": "2025-10-07T10:30:00"
  }
]
```

---

## 🔍 Using MCP Tools

### From Python (Telegram Bot)

```python
# User sends message
# "Remember: Team meeting every Monday at 10 AM"

# Agent processes with MCP enabled
agent = QwenCodeCLIAgent(config={"enable_mcp": True, "user_id": 123})
result = await agent.process({"text": user_message})

# LLM may automatically use store_memory tool
# Check data/memory/user_123/memory.json
```

### From Qwen CLI (Direct)

```bash
qwen

# In qwen CLI:
> Store in memory: Budget for Q4 is $50,000

# LLM will use store_memory tool
# Response: "✓ Stored in memory (ID: 1)"

> What's my Q4 budget?

# LLM will use retrieve_memory tool
# Response: "Your Q4 budget is $50,000"
```

---

## 🛠️ Troubleshooting

### Issue: "MCP server not found"

**Solution:**
1. Check `~/.qwen/settings.json` exists
2. Verify `mem_agent_server.py` path is correct
3. Check Python executable path in config

### Issue: "Permission denied"

**Solution:**
```bash
chmod +x src/agents/mcp/mem_agent_server.py
```

### Issue: "Server failed to start"

**Solution:**
1. Run server manually to see errors:
   ```bash
   python -m src.agents.mcp.mem_agent_server --user-id 123
   ```
2. Check logs in stderr
3. Verify dependencies installed

### Issue: "Tools not available in qwen CLI"

**Solution:**
1. Ensure approval mode is set:
   ```bash
   qwen
   /approval-mode yolo --project
   ```
2. Restart qwen CLI
3. Check `qwen` reads `.qwen/settings.json`

---

## 🚀 Advanced Usage

### Multiple MCP Servers

You can add more MCP servers to the configuration:

```python
# In qwen_config_generator.py, add more servers:

def generate_config(self):
    config = {
        "mcpServers": {
            "mem-agent": {...},
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
                "description": "File operations"
            }
        }
    }
    return config
```

### Per-User MCP Servers

Different users can have different MCP configurations:

```python
# User 1: Has mem-agent only
agent1 = QwenCodeCLIAgent(
    config={"enable_mcp": True, "user_id": 1}
)

# User 2: Has mem-agent + custom tools
agent2 = QwenCodeCLIAgent(
    config={"enable_mcp": True, "user_id": 2}
)
```

### Docker Deployment (Future)

The mem-agent server is designed to run in Docker:

```dockerfile
# Future: Dockerfile for mem-agent
FROM python:3.11-slim

COPY src/agents/mcp/mem_agent_server.py /app/
WORKDIR /app

CMD ["python", "mem_agent_server.py"]
```

---

## 📚 Resources

- [Qwen CLI Configuration](https://github.com/QwenLM/qwen-code/blob/main/docs/cli/configuration.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Project Documentation](../README.md)

---

## 🎉 Summary

**Before:**
- No MCP tools available in qwen CLI
- Manual configuration required

**After:**
- ✅ Automatic MCP configuration
- ✅ mem-agent server for memory storage
- ✅ Easy to extend with more MCP servers
- ✅ Per-user memory isolation
- ✅ Production-ready standalone server

**Next Steps:**
1. Enable MCP in your agent config
2. Test with example script
3. Use MCP tools from Telegram bot or qwen CLI
4. Add more MCP servers as needed