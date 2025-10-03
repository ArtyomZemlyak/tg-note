# Qwen Code Agent

Pure Python agent with custom tools.

---

## Overview

Python-native agent implementation with customizable tool integration.

---

## Features

- ✅ Python-only implementation
- ✅ Flexible tool configuration
- ✅ Custom TODO planning
- ✅ Web search, Git, GitHub support

---

## Configuration

```yaml
AGENT_TYPE: "qwen_code"
AGENT_MODEL: "qwen-max"
```

Note: `qwen_code` agent type is routed by `AgentFactory` to the Python autonomous agent (`src/agents/autonomous_agent.py`). If `OPENAI_API_KEY` (and optional `OPENAI_BASE_URL`) are set, it will use an OpenAI-compatible connector; otherwise it operates in a lightweight rule-based mode.

---

## See Also

- [Agent Overview](overview.md)
- [Qwen Code CLI](qwen-code-cli.md)
