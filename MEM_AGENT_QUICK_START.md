# mem-agent Quick Start Guide

## Installation (3 steps)

### 1. Install Dependencies
```bash
python3 scripts/install_mem_agent.py
```

### 2. Start vLLM Server (choose one backend)

**Option A: vLLM (Linux)**
```bash
pip install vllm>=0.5.5
python3 -m vllm.entrypoints.openai.api_server \
    --model driaforall/mem-agent \
    --host 127.0.0.1 \
    --port 8000
```

**Option B: MLX (macOS)**
```bash
pip install mlx mlx-lm
# Agent will automatically use MLX on macOS
```

**Option C: OpenRouter (Cloud)**
```bash
export OPENAI_API_KEY=your-openrouter-key
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### 3. Use the Agent

**Python:**
```python
from src.agents.mcp.memory.mem_agent_impl import Agent

agent = Agent(
    memory_path="/path/to/memory",
    use_vllm=True
)

response = agent.chat("Remember that my name is Alice")
print(response.reply)
```

**MCP Server:**
```bash
python3 -m src.agents.mem_agent.mcp_server --port 8766
```

## Quick Examples

### Save Information
```python
agent.chat("I work at Google as a senior engineer")
# Agent saves to memory/user.md and creates memory/entities/google.md
```

### Query Information
```python
response = agent.chat("Where do I work?")
print(response.reply)  # "You work at Google as a senior engineer"
```

### View Memory Structure
```python
agent.chat("Show me your memory structure")
# Lists all files and directories
```

## Files Added

```
src/agents/mem_agent/
├── __init__.py              # Package exports
├── agent.py                 # Main Agent class
├── engine.py                # Sandboxed execution
├── model.py                 # Model interface
├── schemas.py               # Data schemas
├── settings.py              # Configuration
├── tools.py                 # Memory tools
├── utils.py                 # Utilities
├── system_prompt.txt        # Agent prompt
├── mcp_server.py            # MCP integration
└── README.md                # Full documentation

examples/
└── mem_agent_example.py     # Usage examples

scripts/
└── test_mem_agent_basic.py  # Validation script

tests/
└── test_mem_agent.py        # Unit tests
```

## Configuration

**config.yaml or .env:**
```yaml
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true
MEM_AGENT_VLLM_HOST: 127.0.0.1
MEM_AGENT_VLLM_PORT: 8000
```

## MCP Tools

1. **chat_with_memory** - Full interaction (read/write)
2. **query_memory** - Read-only retrieval
3. **save_to_memory** - Explicit storage
4. **list_memory_structure** - View organization

## Troubleshooting

**Import errors?**
```bash
pip install transformers huggingface-hub fastmcp aiofiles pydantic python-dotenv jinja2 black
```

**vLLM not connecting?**
```bash
curl http://127.0.0.1:8000/v1/models
```

**Test installation:**
```bash
python3 scripts/test_mem_agent_basic.py
```

## Memory Structure

```
memory/
├── user.md                  # User info & relationships
└── entities/
    ├── alice.md            # Person entity
    ├── google.md           # Company entity
    └── project_x.md        # Project entity
```

## Resources

- **Model**: https://huggingface.co/driaforall/mem-agent
- **Full Docs**: `src/agents/mem_agent/README.md`
- **Summary**: `MEM_AGENT_INTEGRATION_SUMMARY.md`
- **Original**: https://github.com/firstbatchxyz/mem-agent-mcp

---

**Questions?** Check `src/agents/mem_agent/README.md` for detailed documentation.
