# Qwen Code CLI Agent

Complete guide to using the Qwen Code CLI agent.

---

## Overview

The Qwen Code CLI agent is the most powerful option, using the official [qwen-code](https://github.com/QwenLM/qwen-code) CLI tool for advanced AI processing.

---

## Features

- ✅ Full integration with Qwen3-Coder models
- ✅ Automatic TODO planning
- ✅ Built-in tools: web search, git, github, shell
- ✅ Free tier: 2000 requests/day
- ✅ Vision model support

---

## Installation

### 1. Install Node.js 20+

```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install node@20

# Windows
# Download from nodejs.org
```

### 2. Install Qwen Code CLI

```bash
npm install -g @qwen-code/qwen-code@latest
```

### 3. Verify Installation

```bash
qwen --version
```

### 4. Authenticate

```bash
qwen
```

Follow the prompts to authenticate via qwen.ai.

---

## Configuration

Update `config.yaml`:

```yaml
AGENT_TYPE: "qwen_code_cli"
AGENT_QWEN_CLI_PATH: "qwen"
AGENT_TIMEOUT: 300
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false
```

Tip: The CLI path is configurable via `AGENT_QWEN_CLI_PATH` and defaults to `qwen`. Ensure `qwen --version` succeeds on your system before enabling this agent.

---

## How It Works

1. Message received
2. Agent prepares prompt
3. Calls `qwen` CLI
4. Qwen creates TODO plan
5. Executes plan with tools
6. Returns structured markdown
7. Saved to KB

---

## See Also

- [Agent Overview](overview.md)
- [Qwen Code Agent](qwen-code.md)
