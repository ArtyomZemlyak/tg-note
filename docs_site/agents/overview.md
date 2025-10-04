# Agent System Overview

Understanding the AI agent system in tg-note.

---

## What are Agents?

Agents are AI-powered systems that process your messages and transform them into structured knowledge base entries. They analyze content, categorize it, extract key information, and generate well-formatted Markdown files.

---

## Available Agents

tg-note supports a flexible agent system with different implementations.

### Comparison Table

| Feature | Autonomous Agent | Stub |
|---------|------------------|------|
| **AI Processing** | ✅ Good | ❌ Basic |
| **Auto Planning** | ⚠️ Limited | ❌ No |
| **Web Search** | ✅ Custom | ❌ No |
| **Git Operations** | ✅ Custom | ❌ No |
| **External Dependencies** | None | None |
| **Free Tier** | API costs | Free |
| **Best For** | Custom needs | Testing/MVP |

---

## 1. Autonomous Agent

Pure Python agent with customizable tools.

### Features

- ✅ **Python Native** - No Node.js required
- ✅ **Custom Tools** - Build your own tool integrations
- ✅ **Flexible** - Full control over processing
- ⚠️ **API Costs** - Requires Qwen API key

### Configuration

```yaml
AGENT_TYPE: "openai"
AGENT_MODEL: "gpt-4"
```

Note: Implemented in `src/agents/autonomous_agent.py` via `AgentFactory`. It can optionally use an OpenAI-compatible API when `OPENAI_API_KEY`/`OPENAI_BASE_URL` are provided; otherwise it falls back to rule-based processing.

### When to Use

- ✅ Need Python-only solution
- ✅ Custom tool requirements
- ✅ Full control over agent behavior

[Full Documentation →](autonomous-agent.md)

---

## 2. Stub Agent

Simple testing agent without AI.

### Features

- ✅ **Fast** - No API calls
- ✅ **Simple** - Basic categorization
- ✅ **No Dependencies** - Works out of the box
- ❌ **Limited** - No AI analysis

### Configuration

```yaml
AGENT_TYPE: "stub"
```

### When to Use

- ✅ Testing and development
- ✅ MVP/prototype
- ✅ No API keys available
- ❌ Production use

[Full Documentation →](stub-agent.md)

---

## How Agents Work

### Processing Pipeline

```mermaid
graph LR
    A[Message] --> B[Agent]
    B --> C{Analyze}
    C --> D[Categorize]
    D --> E[Extract Info]
    E --> F[Generate Markdown]
    F --> G[Save to KB]
    
    style B fill:#fff3e0
    style F fill:#e8f5e9
```

### Agent Workflow

1. **Receive Content**
   - Text messages
   - URLs
   - Forwarded posts
   - Media

2. **Analyze**
   - Understand topic
   - Extract key points
   - Identify category

3. **Process**
   - Search for context (if enabled)
   - Gather additional info
   - Structure content

4. **Generate**
   - Create Markdown file
   - Add metadata
   - Format properly

5. **Save**
   - Write to KB
   - Commit to Git
   - Notify user

---

## Choosing an Agent

### Decision Tree

```mermaid
graph TD
    A[Choose Agent] --> B{Need AI?}
    
    B -->|Yes| C[Autonomous Agent]
    B -->|No| D[Stub Agent]
    
    style C fill:#c8e6c9
    style D fill:#ffccbc
```

### Recommendations

#### For Custom Needs
→ **Autonomous Agent**

- Full Python control
- Custom tool integration
- Flexible configuration

#### For Testing
→ **Stub Agent**

- Quick setup
- No dependencies
- Fast iteration

---

## Agent Configuration

### Global Settings

Set in `config.yaml`:

```yaml
# Agent Selection
AGENT_TYPE: "stub"

# Common Settings
AGENT_MODEL: "qwen-max"
AGENT_TIMEOUT: 300

# Tool Permissions
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false
```

### Per-User Settings

Users can override via Telegram:

```
/agentsettings
```

---

## Agent Capabilities

### Content Analysis

All agents can:
- Extract text content
- Identify topics
- Generate titles
- Create metadata

Advanced agents (Qwen) add:
- Deep semantic understanding
- Context enrichment
- Smart categorization
- Quality summaries

### Tool Usage

| Tool | Autonomous | Stub |
|------|------------|------|
| Web Search | ✅ | ❌ |
| Git Ops | ✅ | ❌ |
| GitHub API | ✅ | ❌ |
| Shell | ⚠️ | ❌ |

---

## Performance

### Typical Processing Time

| Agent | Short Text | Medium Text | Long Text |
|-------|------------|-------------|-----------|
| **Autonomous** | 3-10s | 10-30s | 30-90s |
| **Stub** | <1s | <1s | <1s |

### Factors Affecting Speed

- Content length
- URL complexity
- Web search usage
- API response time
- Network latency

---

## See Also

- [Autonomous Agent Guide](autonomous-agent.md)
- [Stub Agent Reference](stub-agent.md)
