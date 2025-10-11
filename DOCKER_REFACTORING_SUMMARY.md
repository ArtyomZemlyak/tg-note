# Docker Refactoring Summary

## Что изменилось

### 1. MCP Hub - Единый Gateway

**Было:**
- Отдельный `mcp-http-server` только для memory
- Registry отдельно в `src/mcp_registry/`

**Стало:**
- Единый **MCP Hub** сервер (`src/agents/mcp/mcp_hub_server.py`)
- Объединяет:
  - Built-in MCP tools (memory, и другие в будущем)
  - MCP Server Registry (регистрация внешних MCP серверов)
  - HTTP/SSE API для всех MCP операций
  
**Преимущества:**
- ✅ Одна точка входа для всех MCP операций
- ✅ Меньше сервисов = проще архитектура
- ✅ Легче добавлять новые built-in tools
- ✅ Registry интегрирован напрямую

### 2. Inference Backends - Готовые образы

**Было:**
- `Dockerfile.vllm` - кастомный образ

**Стало:**
- Используем готовый образ `vllm/vllm-openai:latest`
- Добавлены варианты:
  - `docker-compose.yml` - vLLM (по умолчанию)
  - `docker-compose.sglang.yml` - SGLang (быстрее)
  - `docker-compose.mlx.yml` - MLX для macOS

**Преимущества:**
- ✅ Не нужно поддерживать свои Dockerfile
- ✅ Автоматические обновления от разработчиков
- ✅ Выбор backend под задачу
- ✅ Меньше проблем с зависимостями

### 3. Конфигурация - Разделение на креды и настройки

**Было:**
- Все настройки через environment variables в docker-compose

**Стало:**
- `.env` - **только креды** (токены, API ключи)
- `config.docker.yaml` - **все остальные настройки**
- Environment variables - **только для vLLM/SGLang/MLX** (у них нет конфигов)

**Преимущества:**
- ✅ Чистое разделение ответственности
- ✅ Легко менять настройки без пересборки
- ✅ Меньше переменных окружения
- ✅ Креды не смешиваются с обычными настройками

## Архитектура

```
┌──────────────────────────────────────────────────────────────┐
│                     Docker Network                           │
│                                                              │
│  ┌────────────────┐                                         │
│  │  Telegram Bot  │  Читает: config.docker.yaml + .env     │
│  │  (main.py)     │                                         │
│  └───────┬────────┘                                         │
│          │ HTTP                                             │
│          ↓                                                  │
│  ┌──────────────────┐         ┌─────────────────┐         │
│  │   MCP Hub        │ HTTP    │  vLLM/SGLang/   │         │
│  │   (Gateway)      │←────────│  MLX Server     │         │
│  │                  │         │  (optional)     │         │
│  │  ✅ Memory Tools │         │                 │         │
│  │  ✅ Registry     │         │  Готовый образ  │         │
│  │                  │         │  или host       │         │
│  └──────┬───────────┘         └─────────────────┘         │
│         │                                                   │
│         ↓                                                   │
│  ┌──────────────────┐                                       │
│  │   Volumes        │                                       │
│  │  - data/memory   │  Читает:                             │
│  │  - data/registry │  config.docker.yaml                  │
│  │  - knowledge_base│                                       │
│  └──────────────────┘                                       │
└──────────────────────────────────────────────────────────────┘
```

## Файловая структура

### Созданные файлы

```
src/agents/mcp/
└── mcp_hub_server.py         # Единый MCP Hub сервер

docker-compose.yml             # Основной (vLLM)
docker-compose.simple.yml      # Упрощенный (без GPU)
docker-compose.sglang.yml      # Override для SGLang
docker-compose.mlx.yml         # Override для MLX (macOS)

config.docker.yaml             # Настройки для Docker (без кредов)
.env.docker.example            # Только креды

Dockerfile.bot                 # Bot service
Dockerfile.hub                 # MCP Hub service (renamed from Dockerfile.mcp)
```

### Удаленные файлы

```
Dockerfile.vllm               # Используем готовый образ
```

### Обновленные файлы

```
docker-compose.yml            # vLLM через готовый образ, mcp-hub вместо mcp-http-server
docker-compose.simple.yml     # Обновлены ссылки
.env.docker.example          # Только креды + inference server settings
Makefile                     # Добавлены up-vllm, up-sglang, up-mlx
```

## Использование

### Быстрый старт (JSON mode, без GPU)

```bash
# 1. Настройка
make setup
nano .env  # Добавь TELEGRAM_BOT_TOKEN

# 2. Запуск
make up-simple
```

### С AI-памятью (mem-agent)

```bash
# Выбери backend:

# vLLM (Linux/Windows, GPU)
make up-vllm

# SGLang (быстрее, Linux/Windows, GPU)  
make up-sglang

# MLX (macOS Apple Silicon)
# Сначала запусти MLX на хосте:
python -m mlx_lm.server --model driaforall/mem-agent --port 8001
# Потом:
make up-mlx
```

### Настройка

**Креды (.env):**
```bash
TELEGRAM_BOT_TOKEN=your-token
OPENAI_API_KEY=your-key
# и другие API ключи
```

**Настройки (config.docker.yaml):**
```yaml
AGENT_TYPE: qwen_code_cli
MEM_AGENT_STORAGE_TYPE: json  # или vector, или mem-agent
LOG_LEVEL: INFO
# и все остальные настройки
```

**Inference Server (только через .env):**
```bash
MEM_AGENT_MODEL=driaforall/mem-agent
GPU_MEMORY_UTILIZATION=0.8
MAX_MODEL_LEN=4096
```

## MCP Hub API

### Built-in Tools

- `store_memory` - Сохранить информацию
- `retrieve_memory` - Получить информацию
- `list_categories` - Список категорий

### Registry Tools

- `list_mcp_servers` - Список зарегистрированных серверов
- `get_mcp_server` - Получить информацию о сервере
- `register_mcp_server` - Зарегистрировать новый сервер
- `enable_mcp_server` / `disable_mcp_server` - Управление серверами

### Health Check

```bash
curl http://localhost:8765/health
```

Ответ:
```json
{
  "status": "ok",
  "service": "mcp-hub",
  "version": "1.0.0",
  "registry": {
    "servers_total": 3,
    "servers_enabled": 2
  },
  "storage": {
    "active_users": 1
  }
}
```

## Преимущества новой архитектуры

### 1. Упрощение

- **Было:** 3 независимых сервиса (bot, mcp-server, registry)
- **Стало:** 2 сервиса (bot, mcp-hub)

### 2. Гибкость

- Легко добавлять новые built-in tools в MCP Hub
- Выбор inference backend (vLLM, SGLang, MLX)
- Настройки через файл, а не через env vars

### 3. Масштабируемость

- Registry интегрирован - можно регистрировать внешние MCP серверы
- Per-user изоляция для memory
- Готовые образы для inference - проще обновлять

### 4. Безопасность

- Креды только в .env
- Настройки в read-only config
- Разделение ответственности

## Migration Guide

Если у вас уже развернут старый вариант:

### 1. Остановить старые сервисы

```bash
make down
```

### 2. Обновить конфигурацию

```bash
# Скопировать новый шаблон
cp .env .env.backup
cp .env.docker.example .env

# Перенести креды из .env.backup в новый .env
# Создать config.docker.yaml из config.example.yaml
```

### 3. Запустить новые сервисы

```bash
make up-simple  # или make up для full stack
```

### 4. Проверить health

```bash
make health
```

## Дальнейшее развитие

### Планируется добавить в MCP Hub:

- [ ] Web scraping tool
- [ ] Document processing tool
- [ ] Code analysis tool
- [ ] Email integration tool

### Улучшения:

- [ ] Prometheus metrics endpoint
- [ ] WebSocket support (кроме SSE)
- [ ] Multi-tenancy для MCP servers
- [ ] Rate limiting

## Troubleshooting

### MCP Hub не запускается

```bash
# Проверь логи
make logs-hub

# Проверь config
cat config.docker.yaml

# Проверь порт
netstat -tulpn | grep 8765
```

### Inference server недоступен

```bash
# vLLM/SGLang
make logs-vllm
curl http://localhost:8001/health

# MLX (на хосте)
ps aux | grep mlx_lm
```

### Креды не подхватываются

```bash
# Проверь .env
cat .env | grep TELEGRAM_BOT_TOKEN

# Пересоздай контейнеры
make rebuild
```

## Заключение

Новая архитектура проще, гибче и лучше разделяет ответственность между компонентами. Единый MCP Hub упрощает добавление новых функций и управление всей MCP инфраструктурой.

---

**Готово к использованию!** 🎉

См. также:
- [QUICKSTART.Docker.md](QUICKSTART.Docker.md) - Быстрый старт
- [README.Docker.md](README.Docker.md) - Полная документация
- [DOCKER_ARCHITECTURE.md](DOCKER_ARCHITECTURE.md) - Техническая документация
