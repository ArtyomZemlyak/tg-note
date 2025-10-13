# ✅ MCP Docker Integration - COMPLETE

## Сводка изменений

### Создано

1. **src/agents/mcp/mcp_hub_server.py** - Единый MCP Hub
   - Built-in tools (memory: store/retrieve/list_categories)
   - Registry tools (list/get/register/enable/disable servers)
   - HTTP/SSE API на FastMCP
   - Health endpoint для Docker

2. **docker-compose.yml** - Обновлен
   - Используется готовый `vllm/vllm-openai` образ
   - `mcp-hub` контейнер вместо `mcp-http-server`
   - Bot подключается через `MCP_HUB_URL`

3. **docker-compose.sglang.yml** - SGLang backend
4. ~~docker-compose.mlx.yml~~ - removed; use LM Studio on macOS
5. **config.docker.yaml** - Настройки без кредов
6. **DOCKER_MCP_REFACTORING.md** - Документация

### Удалено

- **src/agents/mcp/memory/memory_server_http.py** ❌
  - Заменен на `mcp_hub_server.py`

### Обновлено

1. **src/agents/mcp/client.py**
   - Добавлен HTTP/SSE transport
   - `MCPServerConfig` поддерживает URL
   - `_send_request_http()` / `_send_request_stdio()`
   - Auto-detection транспорта

2. **src/agents/mcp/server_manager.py**
   - Docker mode detection (`MCP_HUB_URL` env var)
   - `_setup_mcp_hub_connection()` - для Docker
   - `_setup_memory_subprocess()` - для standalone
   - Создает правильные конфиги

3. **src/agents/mcp/registry_client.py**
   - Читает URL из JSON конфигов
   - Создает HTTP/SSE клиенты для URL
   - Создает stdio клиенты для subprocess

4. **src/agents/mcp/memory/memory_tool.py**
   - Обновлены ссылки на `mcp_hub_server`

5. **examples/qwen_mcp_integration_example.py**
   - Обновлены команды запуска

6. **.env.docker.example**
   - Только креды и inference server settings
   - Остальное в `config.docker.yaml`

## Архитектура

### Docker режим

```
┌─────────────────────────────────────┐
│         Docker Network              │
│                                     │
│  ┌─────────┐      ┌──────────────┐ │
│  │   Bot   │─HTTP→│   MCP Hub    │ │
│  │         │      │              │ │
│  │         │      │ ✅ Memory    │ │
│  │         │      │ ✅ Registry  │ │
│  └─────────┘      └──────┬───────┘ │
│                          │          │
│                          ↓          │
│                   ┌──────────────┐  │
│                   │ vLLM/SGLang  │  │
│                   │ (optional)   │  │
│                   └──────────────┘  │
└─────────────────────────────────────┘
```

**Логика:**
1. Bot читает `MCP_HUB_URL=http://mcp-hub:8765/sse`
2. MCPServerManager создает конфиг с URL
3. MCPClient подключается через HTTP/SSE
4. Все MCP операции идут через mcp-hub контейнер

### Standalone режим

```
┌─────────────────┐
│      Bot        │
│                 │
│  ┌──────────┐   │
│  │ MCP Mgr  │   │
│  │          │   │
│  │ subprocess   │
│  │    ↓     │   │
│  │  mcp-hub │   │
│  └──────────┘   │
└─────────────────┘
```

**Логика:**
1. Bot НЕ находит `MCP_HUB_URL`
2. MCPServerManager запускает subprocess
3. MCPClient подключается через stdio
4. Все работает локально

## Конфигурация

### Docker (.env)
```bash
# Креды
TELEGRAM_BOT_TOKEN=...
OPENAI_API_KEY=...

# MCP Hub URL (Docker internal)
MCP_HUB_URL=http://mcp-hub:8765/sse

# Inference server (только для mem-agent mode)
MEM_AGENT_MODEL=driaforall/mem-agent
GPU_MEMORY_UTILIZATION=0.8
```

### Docker (config.docker.yaml)
```yaml
# MCP
AGENT_ENABLE_MCP_MEMORY: true

# Memory storage
MEM_AGENT_STORAGE_TYPE: json  # или vector, или mem-agent
MEM_AGENT_BACKEND: vllm
```

### Standalone
Просто включи MCP в `config.yaml`:
```yaml
AGENT_ENABLE_MCP_MEMORY: true
```

## Запуск

### Docker - Simple mode (JSON, без GPU)
```bash
make setup
nano .env  # TELEGRAM_BOT_TOKEN
make up-simple
```

### Docker - Full mode (с GPU)
```bash
# vLLM
make up-vllm

# SGLang (быстрее)
make up-sglang

# MLX (macOS)
python -m mlx_lm.server --model driaforall/mem-agent --port 8001
make up-mlx
```

### Standalone
```bash
python main.py
```

## Проверка

### Логи
```bash
# Docker
make logs-bot | grep MCP
make logs-hub

# Standalone
tail -f logs/bot.log | grep MCP
```

### Ожидаемый вывод

**Docker mode:**
```
[MCPServerManager] Docker mode: Connecting to mcp-hub at http://mcp-hub:8765/sse
[MCPRegistryClient] Created HTTP/SSE client for: memory
[MCPClient] Connecting to MCP server (SSE): http://mcp-hub:8765/sse
[MCPClient] ✓ Connected. Available tools: [...]
```

**Standalone mode:**
```
[MCPServerManager] Standalone mode: Registering memory HTTP server subprocess
[MCPRegistryClient] Created stdio client for: memory
[MCPClient] Connecting to MCP server (stdio): python3
[MCPServerManager] Server 'memory' started (PID: 12345)
[MCPClient] ✓ Connected. Available tools: [...]
```

## API Endpoints (MCP Hub)

### Memory Tools
- `store_memory(content, user_id, category, tags, metadata)` - Сохранить
- `retrieve_memory(user_id, query, category, tags, limit)` - Получить
- `list_categories(user_id)` - Список категорий

### Registry Tools
- `list_mcp_servers(user_id)` - Список серверов
- `get_mcp_server(name)` - Информация о сервере
- `register_mcp_server(...)` - Зарегистрировать сервер
- `enable_mcp_server(name)` / `disable_mcp_server(name)` - Управление

### Health
```bash
curl http://localhost:8765/health
```

## Преимущества

1. ✅ **Единая архитектура** - Bot всегда использует MCPClient
2. ✅ **Docker-native** - Нативная интеграция с контейнерами
3. ✅ **Backward compatible** - Standalone mode работает
4. ✅ **Гибкость** - Легко переключаться между режимами
5. ✅ **Масштабируемость** - Легко добавлять новые tools в Hub
6. ✅ **Простота** - Одна точка входа для всех MCP операций

## Что дальше?

### Возможные улучшения:
- [ ] WebSocket transport (кроме SSE)
- [ ] Prometheus metrics в mcp-hub
- [ ] Rate limiting
- [ ] Добавить новые built-in tools (web scraping, docs, etc.)
- [ ] Multi-tenancy для MCP servers

### Тестирование:
```bash
# Unit tests
pytest tests/test_mcp*.py

# Integration test
make up-simple
# Отправь сообщение боту
# Проверь что memory работает
```

## Заключение

MCP интеграция для Docker завершена! Бот теперь:
- В Docker подключается к mcp-hub через HTTP/SSE
- В standalone запускает mcp-hub как subprocess
- Использует единый MCPClient для обоих режимов
- Поддерживает все storage backends (json/vector/mem-agent)

**Готово к использованию!** 🎉

---

См. также:
- [DOCKER_REFACTORING_SUMMARY.md](DOCKER_REFACTORING_SUMMARY.md) - Docker changes
- [DOCKER_MCP_REFACTORING.md](DOCKER_MCP_REFACTORING.md) - MCP refactoring
- [QUICKSTART.Docker.md](QUICKSTART.Docker.md) - Quick start
- [README.Docker.md](README.Docker.md) - Full guide
