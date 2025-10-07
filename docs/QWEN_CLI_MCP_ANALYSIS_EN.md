# Analysis: Qwen Code CLI and MCP Server Interaction

## Short Answer

**NO, MCP server calls through Qwen Code CLI DO NOT WORK in the current implementation.**

Even if we pass MCP tools description in the prompt to qwen CLI, they cannot be executed during agent operation.

## Why?

### Qwen Code CLI Agent Architecture

```
┌─────────────┐
│   Python    │
│  Runtime    │
│             │
│ ┌─────────┐ │
│ │  MCP    │ │  ← MCP tools exist here (Python)
│ │ Tools   │ │
│ └─────────┘ │
│             │
│ ┌─────────┐ │
│ │ Qwen    │ │
│ │ CLI     │ ├──┐
│ │ Agent   │ │  │
│ └─────────┘ │  │
└─────────────┘  │
                 │ subprocess.run()
                 │ stdin/stdout
                 ▼
         ┌───────────────┐
         │   Node.js     │
         │   Process     │
         │               │
         │  qwen CLI     │  ← Separate process, NO access to Python
         │  (agentic     │
         │   system)     │
         └───────────────┘
              ▲     │
              │     │
         stdin│     │stdout
              │     │
              └─────┘
```

### The Problem

1. **Qwen Code CLI** is a **separate Node.js process** launched via `subprocess`
2. **MCP tools** are **Python objects** in our application's runtime
3. **No bridge** between the Node.js process and Python MCP tools

### What Happens Now

#### QwenCodeCLIAgent.process()

```python
# Step 1: Prepare prompt (with MCP tools description)
prompt = await self._prepare_prompt_async(content)
# Prompt contains text like:
# """
# # Available MCP Tools
# 
# ## MCP Server: mem-agent
# 
# ### mcp_mem_agent_store_memory
# - **Description**: Store information in memory
# ...
# """

# Step 2: Launch qwen CLI as subprocess
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=self.working_directory,
    env=env
)

# Step 3: Pass prompt to stdin
stdout, stderr = await process.communicate(input=prompt_text.encode('utf-8'))

# Step 4: Get result from stdout
result = stdout.decode('utf-8').strip()
```

### What qwen CLI Does Inside

1. Receives prompt via stdin
2. Runs its LLM (usually Qwen model)
3. LLM sees MCP tools description in the prompt
4. LLM **may decide** to call MCP tool (e.g., `mcp_mem_agent_store_memory`)
5. **BUT**: qwen CLI doesn't know how to call this tool!
   - qwen CLI has built-in tools: `web_search`, `git`, `github`, `shell`
   - These tools are implemented in Node.js code of qwen CLI
   - MCP tools are **not registered** in qwen CLI
   - **No mechanism** to call Python functions from Node.js process

### Comparison: AutonomousAgent vs QwenCodeCLIAgent

#### AutonomousAgent (WORKS ✅)

```
┌────────────────────────────────────────┐
│         Python Runtime                 │
│                                        │
│  ┌──────────────┐                     │
│  │ Autonomous   │                     │
│  │   Agent      │                     │
│  └──────┬───────┘                     │
│         │                              │
│         ▼                              │
│  ┌──────────────┐                     │
│  │ ToolManager  │                     │
│  └──────┬───────┘                     │
│         │                              │
│         ├─────► FileTools             │
│         ├─────► WebSearchTool         │
│         ├─────► GitTools              │
│         ├─────► DynamicMCPTool ✅     │  ← MCP tools available!
│         │       │                      │
│         │       └─────► MCPClient     │
│         │               │              │
│         │               └─────► MCP   │
│         │                       Server│
│         │                              │
└─────────┴──────────────────────────────┘
```

**How it works:**
1. LLM receives system prompt with MCP tools description
2. LLM decides to call MCP tool
3. AutonomousAgent executes Python code via ToolManager
4. DynamicMCPTool calls MCPClient
5. MCPClient communicates with MCP server
6. Result returns back to AutonomousAgent

#### QwenCodeCLIAgent (DOESN'T WORK ❌)

```
┌────────────────────────────────────────┐
│         Python Runtime                 │
│                                        │
│  ┌──────────────┐                     │
│  │  Qwen CLI    │                     │
│  │   Agent      │                     │
│  └──────┬───────┘                     │
│         │                              │
│         │ subprocess                   │
│         ▼                              │
│  ═══════════════════════════════════  │  ← Process boundary
│                                        │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│       Node.js Process (qwen CLI)       │
│                                        │
│  ┌──────────────┐                     │
│  │   Qwen LLM   │                     │
│  └──────┬───────┘                     │
│         │                              │
│         │ "Want to call                │
│         │  mcp_mem_agent_store_memory" │
│         ▼                              │
│  ┌──────────────┐                     │
│  │ Tool         │                     │
│  │ Executor     │                     │
│  └──────┬───────┘                     │
│         │                              │
│         ├─────► web_search ✅         │
│         ├─────► git ✅                │
│         ├─────► github ✅             │
│         ├─────► shell ✅              │
│         ├─────► mcp_* ❌              │  ← NO SUCH TOOL!
│         │                              │
│         ▼                              │
│     [ERROR]                            │
│                                        │
└────────────────────────────────────────┘

MCP Tools live in Python but are inaccessible ⚠️
┌────────────────┐
│ DynamicMCPTool │
│ MCPClient      │
│ MCP Server     │
└────────────────┘
```

## Possible Solutions

### Solution 1: Disable MCP for QwenCodeCLIAgent ✅ (Simple)

Already implemented in the code above.

**Pros:**
- Honest to users
- Prevents false expectations
- Doesn't break existing code

**Cons:**
- Functionality unavailable for qwen CLI

### Solution 2: MCP Server Bridge (Complex) ⚠️

Create HTTP/WebSocket server that:
1. Runs in Python runtime
2. Exposes MCP tools via HTTP API
3. qwen CLI calls this API as external service

**Pros:**
- MCP tools accessible for qwen CLI
- Works via standard HTTP

**Cons:**
- Complex implementation
- Requires additional server
- Security concerns (localhost access)
- Additional latency (HTTP overhead)

### Solution 3: Use AutonomousAgent ✅ (Recommended)

**For MCP, use AutonomousAgent:**

```yaml
# config.yaml

# For MCP support
AGENT_TYPE: "autonomous"
AGENT_ENABLE_MCP: true

# Or without MCP
AGENT_TYPE: "qwen_code_cli"
```

## Recommendations

### For Developers

1. ✅ Document limitation in README and docs
2. ✅ Add warning when trying to enable MCP for qwen CLI
3. ✅ Recommend AutonomousAgent for MCP use cases

### For Users

**If you need MCP:**
```yaml
AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"  # or any OpenAI-compatible model
AGENT_ENABLE_MCP: true
```

**If you need qwen CLI:**
```yaml
AGENT_TYPE: "qwen_code_cli"
# MCP automatically disabled
# Built-in tools available: web_search, git, github, shell
```

## Conclusions

### Current State

| Agent | MCP Support | Reason |
|-------|-------------|---------|
| **AutonomousAgent** | ✅ Yes | All in Python runtime, native integration |
| **QwenCodeCLIAgent** | ❌ No | Separate Node.js process, no access to Python MCP tools |
| **StubAgent** | ❌ No | Test agent without AI |

### Why It Doesn't Work for qwen CLI

1. **Process boundary**: qwen CLI = Node.js, MCP tools = Python
2. **No bridge**: No mechanism to call Python from Node.js subprocess
3. **Description ≠ Implementation**: Description in prompt doesn't make tool callable

### Correct Approach

- **For MCP**: Use **AutonomousAgent**
- **For qwen CLI**: Use built-in tools, **no MCP**
- **Documentation**: Clearly state agent and feature compatibility

## See Also

- [Agent MCP Compatibility Matrix](AGENT_MCP_COMPATIBILITY.md)
- [Russian Analysis](QWEN_CLI_MCP_ANALYSIS_RU.md)