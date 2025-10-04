# Agent System Overview

Understanding the AI agent system in tg-note.

---

## What are Agents?

Agents are AI-powered systems that process your messages and transform them into structured knowledge base entries. They analyze content, categorize it, extract key information, and generate well-formatted Markdown files.

---

## Available Agents

tg-note supports three types of agents, each with different capabilities and use cases.

### Comparison Table

| Feature | Qwen Code CLI | Autonomous | Stub |
|---------|---------------|------------|------|
| **AI Processing** | ✅ Advanced | ✅ Advanced | ❌ Basic |
| **Auto Planning** | ✅ Yes | ✅ Yes | ❌ No |
| **Web Search** | ✅ Built-in | ✅ Built-in | ❌ No |
| **Git Operations** | ✅ Built-in | ✅ Built-in | ❌ No |
| **Function Calling** | ✅ Yes | ✅ Yes | ❌ No |
| **External Dependencies** | Node.js | OpenAI lib | None |
| **Free Tier** | 2000/day | Depends on API | Free |
| **Best For** | Production | Custom APIs | Testing/MVP |

---

## 1. Qwen Code CLI ⭐ Recommended

The most powerful agent using the official Qwen Code CLI tool.

### Features

- ✅ **Advanced AI Processing** - Qwen3-Coder models
- ✅ **Automatic Planning** - Creates and executes TODO plans
- ✅ **Built-in Tools** - Web search, Git, GitHub, Shell
- ✅ **Vision Support** - Can analyze images
- ✅ **Free Tier** - 2000 requests/day, 60 req/min

### Installation

```bash
# Install Node.js 20+
npm install -g @qwen-code/qwen-code@latest

# Authenticate
qwen

# Configure
AGENT_TYPE: "qwen_code_cli"
```

### When to Use

- ✅ Production deployments
- ✅ Need best quality output
- ✅ Want automatic planning
- ✅ Can install Node.js

[Full Documentation →](qwen-code-cli.md)

---

## 2. Autonomous Agent

Python-based agent with OpenAI-compatible API support.

### Features

- ✅ **OpenAI-Compatible** - Works with OpenAI, Qwen, and other compatible APIs
- ✅ **Autonomous Planning** - Self-planning and decision-making
- ✅ **Function Calling** - Native function calling support
- ✅ **Built-in Tools** - Web search, Git, GitHub, file management
- ✅ **Flexible** - Custom LLM connectors

### Installation

```bash
# OpenAI library included in requirements
poetry install

# Configure
AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"  # or any compatible model
```

### Configuration

**Environment Variables:**
```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
```

**YAML Settings:**
```yaml
AGENT_TYPE: "autonomous"
AGENT_MODEL: "gpt-3.5-turbo"
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_FILE_MANAGEMENT: true
```

### When to Use

- ✅ OpenAI or compatible API available
- ✅ Need autonomous planning
- ✅ Custom LLM provider (Qwen, Azure, etc.)
- ✅ Python-only environment
- ❌ Don't want to use Node.js

[Full Documentation →](autonomous-agent.md)

---

## 3. Stub Agent

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
    A[Choose Agent] --> B{Production or Testing?}
    B -->|Production| C{Can install Node.js?}
    B -->|Testing| G[Stub Agent]
    C -->|Yes| D[Qwen Code CLI ⭐]
    C -->|No| E{Have OpenAI-compatible API?}
    E -->|Yes| F[Autonomous Agent]
    E -->|No| G
    
    style D fill:#c8e6c9
    style F fill:#b3e5fc
    style G fill:#ffccbc
```

### Recommendations

#### For Production
→ **Qwen Code CLI**

- Best quality results
- Automatic planning
- Built-in tools
- Free tier available

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
AGENT_TYPE: "qwen_code_cli"

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

| Tool | Qwen CLI | Autonomous | Stub |
|------|----------|------------|------|
| Web Search | ✅ | ✅ | ❌ |
| Git Ops | ✅ | ✅ | ❌ |
| GitHub API | ✅ | ✅ | ❌ |
| Shell | ✅ | ✅ | ❌ |
| File Management | ✅ | ✅ | ❌ |
| Vision | ✅ | ✅* | ❌ |

*Vision support depends on the LLM model used

---

## Performance

### Typical Processing Time

| Agent | Short Text | Medium Text | Long Text |
|-------|------------|-------------|-----------|
| **Qwen CLI** | 5-15s | 15-45s | 45-120s |
| **Autonomous** | 5-20s | 15-60s | 60-180s |
| **Stub** | <1s | <1s | <1s |

### Factors Affecting Speed

- Content length
- URL complexity
- Web search usage
- API response time
- Network latency

---

## See Also

- [Qwen Code CLI Guide](qwen-code-cli.md)
- [Autonomous Agent Guide](autonomous-agent.md)
- [Stub Agent Reference](stub-agent.md)
