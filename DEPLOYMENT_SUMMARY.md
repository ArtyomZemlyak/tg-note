# Docker Deployment - Summary

This document summarizes the Docker deployment setup for tg-note.

## 📁 Created Files

### Core Deployment Files

1. **docker-compose.yml** - Main orchestration file
   - Defines all three services (bot, mcp-http-server, vllm-server)
   - Configures networks and volumes
   - Full GPU-enabled setup

2. **docker-compose.simple.yml** - Simplified version
   - Only bot + MCP server
   - JSON storage mode
   - No GPU required
   - Perfect for testing

3. **docker-compose.override.yml.example** - Customization template
   - Examples for common customizations
   - Override main configuration without modifying it

### Dockerfiles

4. **Dockerfile.bot** - Bot service
   - Multi-stage build
   - Python 3.11 slim base
   - Includes git for KB operations

5. **Dockerfile.mcp** - MCP HTTP server
   - Multi-stage build
   - Includes FastMCP and mem-agent dependencies
   - No GPU-specific packages

6. **Dockerfile.vllm** - vLLM inference server
   - Based on official vLLM image
   - GPU-enabled
   - OpenAI-compatible API

### Configuration Files

7. **.dockerignore** - Build context optimization
   - Excludes unnecessary files from images
   - Reduces build time and image size

8. **.env.docker.example** - Environment template
   - All available configuration options
   - Comments explaining each variable
   - Default values

### Documentation

9. **README.Docker.md** - Comprehensive guide
   - Architecture overview
   - Deployment instructions
   - Troubleshooting
   - Performance tuning

10. **QUICKSTART.Docker.md** - Quick start guide
    - Get running in 5 minutes
    - Step-by-step instructions
    - Common commands

11. **DOCKER_ARCHITECTURE.md** - Technical documentation
    - System architecture
    - Service communication
    - Data flow
    - Resource requirements
    - Scaling considerations

### Automation

12. **Makefile** - Command shortcuts
    - `make setup` - Initial setup
    - `make up` - Start services
    - `make logs` - View logs
    - `make json/vector/mem-agent` - Switch storage modes

13. **.github/workflows/docker-build.yml.example** - CI/CD template
    - Automated image builds
    - Multi-platform support
    - Security scanning

### Updates to Existing Files

14. **.gitignore** - Updated
    - Added Docker-related entries
    - Ignore override files and backups

15. **src/agents/mcp/memory/memory_server_http.py** - Enhanced
    - Added `/health` endpoint for Docker health checks

## 🏗️ Architecture

```
┌─────────────────┐
│  Telegram Bot   │  Port: -
└────────┬────────┘
         │
         ↓
┌─────────────────┐  Port: 8765
│ MCP HTTP Server │
│   (Gateway)     │
└────────┬────────┘
         │
         ↓
   ┌─────────┐
   │ Storage │
   ├─────────┤
   │  json   │ ← Simple, fast (default)
   │ vector  │ ← Semantic search
   │mem-agent│ ← AI-powered (needs vLLM)
   └────┬────┘
        │ (if mem-agent)
        ↓
┌─────────────────┐  Port: 8001
│  vLLM Server    │  GPU: Required
└─────────────────┘
```

## 🚀 Quick Start

### Minimal Setup (No GPU)

```bash
# 1. Setup
make setup

# 2. Configure (edit .env)
nano .env

# 3. Start
make up-simple

# 4. Check
make logs
```

### Full Setup (With GPU)

```bash
# 1. Setup
make setup

# 2. Configure (edit .env)
nano .env

# 3. Start all services
make up

# 4. Check status
make ps
make logs
```

## 📊 Storage Modes

| Mode | Command | GPU | Speed | Features |
|------|---------|-----|-------|----------|
| JSON | `make json` | No | ⚡ Fast | Simple storage |
| Vector | `make vector` | No | 🔍 Medium | Semantic search |
| Mem-Agent | `make mem-agent` | Yes | 🤖 Slower | AI-powered |

## 🔧 Common Commands

```bash
# Setup & Build
make setup              # Initial setup
make build             # Build images

# Start/Stop
make up                # Start all (with GPU)
make up-simple         # Start without GPU
make down              # Stop all
make restart           # Restart all

# Monitoring
make logs              # All logs
make logs-bot          # Bot logs
make logs-mcp          # MCP logs
make ps                # Status
make health            # Health check

# Maintenance
make rebuild           # Rebuild & restart
make backup            # Backup data
make clean             # Remove all (deletes data!)

# Storage modes
make json              # JSON mode
make vector            # Vector mode
make mem-agent         # Mem-agent mode
```

## 📝 Configuration

### Environment Variables (.env)

**Required:**
```bash
TELEGRAM_BOT_TOKEN=your-token
```

**Optional but recommended:**
```bash
# Agent
AGENT_TYPE=qwen_code
QWEN_API_KEY=your-key

# Memory
AGENT_ENABLE_MCP_MEMORY=true
MEM_AGENT_STORAGE_TYPE=json|vector|mem-agent

# For mem-agent mode
MEM_AGENT_MODEL=driaforall/mem-agent
MEM_AGENT_BACKEND=vllm
```

## 💾 Data Persistence

All data is stored in local directories:

```
./data/memory/        # Per-user memory
./knowledge_base/     # Git-based KB
./logs/              # Application logs
```

Shared model cache in Docker volume:
```
huggingface-cache    # HuggingFace models
```

## 🔒 Security

1. **Never commit `.env` file**
2. Use `ALLOWED_USER_IDS` to restrict access
3. Keep ports internal (default)
4. Regular updates

```bash
chmod 600 .env
chmod 700 data/
```

## 🐛 Troubleshooting

### Bot not starting
```bash
make logs-bot
# Check: TELEGRAM_BOT_TOKEN set?
```

### MCP server issues
```bash
make logs-mcp
curl http://localhost:8765/health
```

### vLLM GPU errors
```bash
nvidia-smi
make logs-vllm
# Reduce GPU_MEMORY_UTILIZATION in .env
```

## 📚 Documentation

- **Quick Start:** [QUICKSTART.Docker.md](QUICKSTART.Docker.md)
- **Full Guide:** [README.Docker.md](README.Docker.md)
- **Architecture:** [DOCKER_ARCHITECTURE.md](DOCKER_ARCHITECTURE.md)

## 🎯 What's Next?

1. ✅ Setup completed
2. 📱 Message your bot on Telegram
3. 💾 Bot stores memories automatically
4. 🔍 Use `/memory` to search
5. 📚 Integrate with knowledge base

## ✨ Features

- 🐳 **Easy deployment** - One command to start
- 🔄 **Multiple storage modes** - JSON, Vector, AI-powered
- 📦 **Self-contained** - All dependencies included
- 🔧 **Configurable** - Environment-based config
- 📊 **Health checks** - Automatic monitoring
- 💾 **Persistent data** - Volume-based storage
- 🚀 **Production-ready** - Resource limits, restarts

## 🤝 Contributing

To improve Docker deployment:

1. Test on your setup
2. Report issues
3. Submit improvements
4. Share your docker-compose.override.yml examples

## 📞 Support

- 📖 Docs: See above links
- 🐛 Issues: GitHub Issues
- 💬 Questions: Create an issue

---

**Ready to deploy?** → Start with [QUICKSTART.Docker.md](QUICKSTART.Docker.md)
