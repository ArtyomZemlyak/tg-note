# Agent and MCP Compatibility Matrix

## Quick Reference

| Agent Type | MCP Support | Runtime | Recommended For |
|------------|-------------|---------|-----------------|
| **AutonomousAgent** | ✅ **Full Support** | Python | MCP tools, custom workflows |
| **QwenCodeCLIAgent** | ❌ **Not Supported** | Node.js (subprocess) | Built-in tools (web, git, github) |
| **StubAgent** | ❌ **Not Supported** | Python | Testing only |

## Why QwenCodeCLIAgent doesn't support MCP?

**Technical Reason**: Process boundary

- Qwen CLI runs as a **separate Node.js process**
- MCP tools are **Python objects** in the main process
- No bridge exists between Node.js subprocess and Python MCP tools
- Even if MCP tools are described in the prompt, they **cannot be executed**

## Choosing the Right Agent

### Use AutonomousAgent when:

✅ You need MCP tools (memory, custom integrations)  
✅ You have an OpenAI-compatible API key  
✅ You want Python-native integration  
✅ You need custom tool development  

**Configuration:**
```yaml
AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"
AGENT_ENABLE_MCP: true
```

### Use QwenCodeCLIAgent when:

✅ You want free tier (2000 requests/day via Qwen OAuth)  
✅ You need vision model support  
✅ Built-in tools (web search, git, github) are sufficient  
✅ You prefer official Qwen integration  

**Configuration:**
```yaml
AGENT_TYPE: "qwen_code_cli"
# MCP is automatically disabled
# Built-in tools: web_search, git, github, shell
```

## Feature Comparison

| Feature | AutonomousAgent | QwenCodeCLIAgent |
|---------|----------------|------------------|
| **Language** | Python | Node.js (subprocess) |
| **MCP Tools** | ✅ Yes | ❌ No |
| **Built-in Tools** | ✅ Yes (Python) | ✅ Yes (Node.js) |
| **Custom Tools** | ✅ Easy (Python) | ❌ Difficult |
| **API** | OpenAI-compatible | Qwen-specific |
| **Free Tier** | Depends on provider | 2000/day |
| **Setup** | pip install | npm install |
| **Vision** | Model-dependent | ✅ Yes |

## MCP Tools Architecture

### AutonomousAgent (Working ✅)

```
┌─────────────────────────────────────┐
│       Python Runtime                │
│                                     │
│  ┌─────────────┐                   │
│  │ Autonomous  │                   │
│  │   Agent     │                   │
│  └──────┬──────┘                   │
│         │                           │
│         ▼                           │
│  ┌─────────────┐                   │
│  │ ToolManager │                   │
│  └──────┬──────┘                   │
│         │                           │
│         ├──► MCP Tools ✅          │
│         ├──► File Tools            │
│         ├──► Web Search            │
│         └──► Git Tools             │
│                                     │
└─────────────────────────────────────┘
```

### QwenCodeCLIAgent (Not Working ❌)

```
┌─────────────────────────────────────┐
│       Python Runtime                │
│                                     │
│  ┌─────────────┐                   │
│  │  Qwen CLI   │                   │
│  │   Agent     │                   │
│  └──────┬──────┘                   │
│         │ subprocess                │
│         ▼                           │
│  ═══════════════════════════════   │  ← Process boundary
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    Node.js Process (qwen CLI)       │
│                                     │
│  ┌─────────────┐                   │
│  │  Qwen LLM   │                   │
│  └──────┬──────┘                   │
│         │                           │
│         ▼                           │
│  ┌─────────────┐                   │
│  │   Tools     │                   │
│  └──────┬──────┘                   │
│         │                           │
│         ├──► web_search ✅         │
│         ├──► git ✅                │
│         ├──► github ✅             │
│         ├──► shell ✅              │
│         └──► MCP Tools ❌          │  ← Not accessible!
│                                     │
└─────────────────────────────────────┘

MCP Tools in Python (inaccessible from Node.js):
┌─────────────┐
│ MCP Tools   │
│ Registry    │
└─────────────┘
```

## FAQ

### Q: Can I enable MCP for QwenCodeCLIAgent?

**A:** No. Even if you set `AGENT_ENABLE_MCP: true`, it will be ignored and a warning will be logged. Use AutonomousAgent instead.

### Q: Why does the prompt include MCP tools description for qwen CLI?

**A:** This was a misunderstanding of the architecture. The description is now **disabled** for qwen CLI to avoid confusion.

### Q: Can I use both agents?

**A:** Not simultaneously. Choose one based on your needs. Switch by changing `AGENT_TYPE` in config.

### Q: Will MCP support be added to qwen CLI in the future?

**A:** Unlikely due to process boundary. Possible solutions:
- HTTP bridge (complex, adds latency)
- MCP servers in Node.js (requires reimplementation)
- Contributing to qwen-code project (external dependency)

Current recommendation: **Use AutonomousAgent for MCP**

## Examples

### Example 1: Using MCP with AutonomousAgent

```yaml
# config.yaml
AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"
AGENT_ENABLE_MCP: true
AGENT_ENABLE_WEB_SEARCH: true
```

```bash
# .env
OPENAI_API_KEY=sk-proj-...
```

Bot will have access to:
- ✅ MCP tools (memory, custom)
- ✅ Web search
- ✅ File management
- ✅ Git operations

### Example 2: Using qwen CLI without MCP

```yaml
# config.yaml
AGENT_TYPE: "qwen_code_cli"
# MCP automatically disabled
```

Bot will have access to:
- ✅ Web search (built-in)
- ✅ Git operations (built-in)
- ✅ GitHub API (built-in)
- ✅ Shell commands (if enabled)
- ❌ MCP tools (not accessible)

## See Also

- [Qwen CLI Agent Documentation](../docs_site/agents/qwen-code-cli.md)
- [Autonomous Agent Documentation](../docs_site/agents/autonomous-agent.md)
- [MCP Tools Discovery](MCP_TOOLS_DISCOVERY.md)
- [Architecture Analysis](QWEN_CLI_MCP_ANALYSIS_RU.md)