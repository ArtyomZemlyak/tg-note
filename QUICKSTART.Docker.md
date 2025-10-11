# Quick Start - Docker Deployment

Get tg-note running in Docker in 5 minutes! 🚀

## Prerequisites

- ✅ Docker & Docker Compose installed
- ✅ Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- ⚡ GPU with NVIDIA drivers (only for AI-powered memory mode)

## Quick Start (Simple Mode - No GPU)

This mode uses fast JSON storage and doesn't require a GPU.

### 1. Clone & Setup

```bash
git clone https://github.com/ArtyomZemlyak/tg-note.git
cd tg-note

# Create environment file
make setup
```

### 2. Configure

Edit `.env` and add your bot token:

```bash
nano .env
```

**Minimum required:**
```bash
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

### 3. Start Services

```bash
make up-simple
```

That's it! 🎉 Your bot is running!

## Verify Deployment

```bash
# Check service status
make ps

# View logs
make logs

# Test bot
# Send a message to your bot on Telegram
```

## Next Steps

### Monitor Services

```bash
# All logs
make logs

# Bot only
make logs-bot

# MCP server only
make logs-mcp
```

### Stop Services

```bash
make down
```

### Restart Services

```bash
make restart
```

## Advanced: AI-Powered Memory Mode

For AI-powered memory management with semantic understanding (requires GPU):

### 1. Ensure NVIDIA Docker Runtime

```bash
# Install nvidia-docker2
sudo apt-get install nvidia-docker2
sudo systemctl restart docker

# Test GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 2. Configure for Mem-Agent

Edit `.env`:
```bash
MEM_AGENT_STORAGE_TYPE=mem-agent
MEM_AGENT_MODEL=driaforall/mem-agent
MEM_AGENT_BACKEND=vllm
```

### 3. Start with GPU Support

```bash
make mem-agent
# or
make up
```

This will:
- ✅ Start vLLM inference server
- ✅ Download the model (~4GB)
- ✅ Start MCP server with mem-agent storage
- ✅ Start bot

**First start takes 5-10 minutes** to download the model.

## Storage Modes Comparison

| Mode | Command | GPU | Speed | Features |
|------|---------|-----|-------|----------|
| 🚀 JSON | `make json` | No | Fast | Simple key-value storage |
| 🔍 Vector | `make vector` | No | Medium | Semantic search |
| 🤖 Mem-Agent | `make mem-agent` | Yes | Slower | AI-powered context management |

## Useful Commands

```bash
# Setup
make setup              # Initial setup
make build             # Build images

# Start/Stop
make up                # Start all (with GPU)
make up-simple         # Start without GPU
make down              # Stop services
make restart           # Restart services

# Monitoring
make logs              # View all logs
make logs-bot          # Bot logs only
make logs-mcp          # MCP server logs
make ps                # Service status
make health            # Health check

# Maintenance
make rebuild           # Rebuild and restart
make backup            # Backup data
make clean             # Remove all (WARNING: deletes data!)

# Storage modes
make json              # Switch to JSON mode
make vector            # Switch to vector mode
make mem-agent         # Switch to mem-agent mode
```

## Troubleshooting

### Bot not starting?

```bash
# Check logs
make logs-bot

# Common issue: Missing bot token
# Solution: Add TELEGRAM_BOT_TOKEN to .env
```

### MCP server not responding?

```bash
# Check MCP logs
make logs-mcp

# Test endpoint
curl http://localhost:8765/health
```

### vLLM server issues?

```bash
# Check logs
make logs-vllm

# Check GPU
nvidia-smi

# If out of memory, reduce GPU usage in .env:
GPU_MEMORY_UTILIZATION=0.6
```

### "Permission denied" errors?

```bash
# Fix permissions
sudo chown -R $USER:$USER data/ logs/ knowledge_base/
chmod 700 data/ logs/
```

## Configuration

### Minimal (JSON mode - no GPU)
```bash
TELEGRAM_BOT_TOKEN=your-token
```

### With AI Agent (requires API key)
```bash
TELEGRAM_BOT_TOKEN=your-token
AGENT_TYPE=qwen_code
QWEN_API_KEY=your-qwen-key
AGENT_ENABLE_MCP_MEMORY=true
```

### Full AI Stack (requires GPU)
```bash
TELEGRAM_BOT_TOKEN=your-token
AGENT_TYPE=qwen_code
QWEN_API_KEY=your-qwen-key
AGENT_ENABLE_MCP_MEMORY=true
MEM_AGENT_STORAGE_TYPE=mem-agent
MEM_AGENT_BACKEND=vllm
```

## Data Persistence

Your data is stored in:
- `./data/memory/` - Memory storage
- `./knowledge_base/` - Knowledge base files
- `./logs/` - Application logs

To backup:
```bash
make backup
```

## Need Help?

- 📖 Full documentation: [README.Docker.md](README.Docker.md)
- 🐛 Report issues: [GitHub Issues](https://github.com/ArtyomZemlyak/tg-note/issues)
- 💬 Questions: Check existing issues or create new one

## What's Next?

1. ✅ Send messages to your bot
2. 📝 Bot will store conversations in memory
3. 🔍 Use `/memory` command to search memories
4. 📚 Integrate with knowledge base for note-taking

Enjoy! 🎉
