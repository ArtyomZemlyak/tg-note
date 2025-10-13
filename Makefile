.PHONY: help build up down restart logs clean setup

# Default target
help:
	@echo "tg-note Docker Deployment Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Initial setup (copy .env, create dirs)"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build          - Build all Docker images"
	@echo "  make up             - Start all services (with GPU/vLLM)"
	@echo "  make up-simple      - Start only bot + MCP (JSON mode, no GPU)"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs           - Show logs from all services"
	@echo "  make logs-bot       - Show bot logs"
	@echo "  make logs-mcp       - Show MCP server logs"
	@echo "  make logs-vllm      - Show vLLM server logs"
	@echo "  make ps             - Show service status"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Stop services and remove volumes (DELETES DATA)"
	@echo "  make rebuild        - Rebuild and restart services"
	@echo ""
	@echo "Storage Modes:"
	@echo "  make json           - Start with JSON storage (fast, no GPU)"
	@echo "  make vector         - Start with vector storage (semantic search)"
	@echo "  make mem-agent      - Start with mem-agent (AI-powered, needs GPU)"

# Initial setup
setup:
	@echo "🚀 Setting up tg-note deployment..."
	@if [ ! -f .env ]; then \
		cp .env.docker.example .env; \
		echo "✅ Created .env file from template"; \
		echo "⚠️  Please edit .env and add your TELEGRAM_BOT_TOKEN"; \
	else \
		echo "ℹ️  .env file already exists"; \
	fi
	@mkdir -p data/memory logs knowledge_base
	@echo "✅ Created necessary directories"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env and add your credentials"
	@echo "2. Run 'make up-simple' (no GPU) or 'make up' (with GPU)"

# Build images
build:
	@echo "🔨 Building Docker images..."
	docker-compose build

# Start all services (full mode with vLLM)
up:
	@echo "🚀 Starting all services (with vLLM/GPU)..."
	docker-compose up -d
	@echo "✅ Services started"
	@echo "📊 Check status: make ps"
	@echo "📋 View logs: make logs"

# Start simple mode (no vLLM/GPU)
up-simple:
	@echo "🚀 Starting services in simple mode (JSON storage, no GPU)..."
	docker-compose -f docker-compose.simple.yml up -d
	@echo "✅ Services started"
	@echo "📊 Check status: make ps"
	@echo "📋 View logs: make logs"

# Stop services
down:
	@echo "⏹️  Stopping services..."
	docker-compose down
	docker-compose -f docker-compose.simple.yml down 2>/dev/null || true

# Restart services
restart:
	@echo "🔄 Restarting services..."
	docker-compose restart
	@echo "✅ Services restarted"

# Show logs
logs:
	docker-compose logs -f

logs-bot:
	docker-compose logs -f bot

logs-hub:
	docker-compose logs -f mcp-hub

logs-vllm:
	docker-compose logs -f vllm-server

logs-sglang:
	docker-compose -f docker-compose.yml -f docker-compose.sglang.yml logs -f vllm-server

# Show service status
ps:
	@echo "📊 Service Status:"
	@docker-compose ps

# Clean everything (removes volumes)
clean:
	@echo "⚠️  WARNING: This will delete all data (memory, logs, etc.)"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	docker-compose down -v
	docker-compose -f docker-compose.simple.yml down -v 2>/dev/null || true
	@echo "✅ Cleaned up"

# Rebuild and restart
rebuild:
	@echo "🔨 Rebuilding and restarting..."
	docker-compose up -d --build
	@echo "✅ Services rebuilt and restarted"

# Storage mode shortcuts
json:
	@echo "🚀 Starting with JSON storage (fast, no GPU)..."
	@echo "MEM_AGENT_STORAGE_TYPE=json" > .env.storage
	docker-compose -f docker-compose.simple.yml up -d
	@echo "✅ JSON mode active"

vector:
	@echo "🚀 Starting with vector storage (semantic search)..."
	@grep -v "^MEM_AGENT_STORAGE_TYPE=" .env > .env.tmp || true
	@echo "MEM_AGENT_STORAGE_TYPE=vector" >> .env.tmp
	@mv .env.tmp .env
	docker-compose -f docker-compose.simple.yml up -d --build
	@echo "✅ Vector mode active"

mem-agent:
	@echo "🚀 Starting with mem-agent storage (AI-powered, needs GPU)..."
	@grep -v "^MEM_AGENT_STORAGE_TYPE=" .env > .env.tmp || true
	@echo "MEM_AGENT_STORAGE_TYPE=mem-agent" >> .env.tmp
	@mv .env.tmp .env
	docker-compose up -d --build
	@echo "✅ Mem-agent mode active (with vLLM)"

# Backend alternatives
up-vllm:
	@echo "🚀 Starting with vLLM backend..."
	docker-compose up -d --build
	@echo "✅ vLLM backend active"

up-sglang:
	@echo "🚀 Starting with SGLang backend (faster inference)..."
	docker-compose -f docker-compose.yml -f docker-compose.sglang.yml up -d --build
	@echo "✅ SGLang backend active"

up-mlx:
	@echo "🚀 Starting with MLX backend (macOS)..."
	@echo "⚠️  MLX Docker backend is deprecated. Use LM Studio on macOS."
	@echo "   Run: ./scripts/lms_load_mem_agent.sh   # downloads & loads model via lms CLI"
	@echo "   Or:  ./scripts/run_lmstudio_model.sh   # manual server setup"
	@echo "   Tip: Inside Docker on macOS, export LMSTUDIO_HOST=host.docker.internal"

# Backup
backup:
	@echo "📦 Creating backup..."
	@mkdir -p backups
	tar -czf backups/backup-$$(date +%Y%m%d-%H%M%S).tar.gz data/ knowledge_base/ .env
	@echo "✅ Backup created in backups/"

# Health check
health:
	@echo "🏥 Health Check:"
	@echo ""
	@echo "Bot:"
	@docker-compose exec bot python -c "print('✅ Bot container running')" 2>/dev/null || echo "❌ Bot not running"
	@echo ""
	@echo "MCP Hub:"
	@curl -s http://localhost:8765/health | python -m json.tool 2>/dev/null || echo "❌ MCP Hub not responding"
	@echo ""
	@echo "Inference Server (vLLM/SGLang/MLX):"
	@curl -s http://localhost:8001/health 2>/dev/null && echo "✅ Inference server running" || echo "⚠️  Inference server not running (OK if using JSON/vector mode)"
