# Настройка MCP для контейнеризованных развёртываний

Руководство по настройке MCP (Model Context Protocol) серверов для развёртываний в Docker.

## Обзор

При запуске в Docker, MCP Hub развёртывается как отдельный контейнер (`mcp-hub`), который взаимодействует с:
- **Контейнер бота** - Основной Telegram бот с Python MCP клиентами
- **Qwen CLI** - Запускается внутри контейнера бота или на хост-машине
- **Другие LLM** - Локально развёрнутые LLM (vLLM, SGLang, LM Studio и т.д.)

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│ Docker окружение                                            │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │  Контейнер   │ HTTP/SSE│  Контейнер   │                │
│  │  бота        │────────▶│  MCP Hub     │                │
│  │              │         │  :8765       │                │
│  │  - Qwen CLI  │         │              │                │
│  │  - Python    │         │  - Память    │                │
│  └──────────────┘         │  - Реестр    │                │
│                           └──────────────┘                │
│                                  ▲                          │
│                                  │                          │
│                                  │ vLLM/SGLang              │
│                           ┌──────────────┐                │
│                           │  vLLM        │                │
│                           │  сервер      │                │
│                           │  :8001       │                │
│                           └──────────────┘                │
└─────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ HTTP :8765
                                  │
                           ┌──────────────┐
                           │  Хост        │
                           │  машина      │
                           │              │
                           │  - Qwen CLI  │
                           │  - LM Studio │
                           │  - Cursor    │
                           └──────────────┘
```

## Конфигурация сети

### Внутренняя сеть Docker

Сервисы внутри Docker Compose сети общаются по именам сервисов:

```yaml
# docker-compose.yml
services:
  mcp-hub:
    ports:
      - "8765:8765"  # Доступен на хосте
    
  bot:
    environment:
      - MCP_HUB_URL=http://mcp-hub:8765/sse  # Внутри Docker
```

**Внутренние URL:**
- MCP Hub: `http://mcp-hub:8765/sse`
- vLLM: `http://vllm-server:8001`

### Доступ с хост-машины

С хост-машины используйте localhost:

**URL для хоста:**
- MCP Hub: `http://127.0.0.1:8765/sse`
- vLLM: `http://127.0.0.1:8001`

## Файлы конфигурации MCP

### Автоматически генерируемые конфигурации

Система автоматически создаёт конфигурации для разных клиентов:

1. **Qwen CLI** - `~/.qwen/settings.json`
2. **Python клиенты** - `data/mcp_servers/mcp-hub.json`
3. **Cursor** - `.mcp.json` (корень проекта)
4. **Claude Desktop** - `~/Library/Application Support/Claude/claude_desktop_config.json`
5. **LM Studio** - `~/.lmstudio/mcp_config.json`

### Определение окружения

Генераторы конфигурации автоматически определяют окружение:

```python
# Логика автоопределения:
1. Проверка файла /.dockerenv (Docker контейнер)
2. Проверка переменной окружения MCP_HUB_URL
3. Проверка /proc/1/cgroup на наличие docker
4. По умолчанию localhost (хост окружение)
```

## Конфигурация для разных сценариев

### 1. Qwen CLI внутри контейнера бота

Когда Qwen CLI запускается внутри контейнера бота:

**Окружение:**
```bash
MCP_HUB_URL=http://mcp-hub:8765/sse
```

**Сгенерированный `~/.qwen/settings.json`:**
```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://mcp-hub:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "MCP Hub - Unified MCP gateway"
    }
  },
  "allowMCPServers": ["mcp-hub"]
}
```

### 2. Qwen CLI на хост-машине

Когда Qwen CLI запускается на хосте:

**Сгенерированный `~/.qwen/settings.json`:**
```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "MCP Hub - Unified MCP gateway"
    }
  },
  "allowMCPServers": ["mcp-hub"]
}
```

### 3. LM Studio на хосте

**Сгенерированный `~/.lmstudio/mcp_config.json`:**
```json
{
  "mcp_servers": {
    "mcp-hub": {
      "transport": "http",
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "enabled": true,
      "description": "MCP Hub - Memory and tool gateway"
    }
  }
}
```

## Ручная настройка

### Использование универсального генератора конфигураций

Сгенерировать конфигурации для всех поддерживаемых клиентов:

```bash
# Внутри контейнера
python -m src.mcp.universal_config_generator --all

# На хост-машине
python -m src.mcp.universal_config_generator --all --url http://127.0.0.1:8765/sse
```

Сгенерировать конфигурацию для конкретного клиента:

```bash
# Только Qwen CLI
python -m src.mcp.universal_config_generator --qwen

# Только Cursor
python -m src.mcp.universal_config_generator --cursor

# Только LM Studio
python -m src.mcp.universal_config_generator --lmstudio

# Директория data (Python клиенты)
python -m src.mcp.universal_config_generator --data
```

## Аутентификация и безопасность

### API ключи в Docker

API ключи передаются через переменные окружения и автоматически доступны для Qwen CLI:

```yaml
# docker-compose.yml
services:
  bot:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL}
      - QWEN_API_KEY=${QWEN_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

### Переменные окружения

В файле `.env`:

```bash
# API ключи
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
QWEN_API_KEY=...
ANTHROPIC_API_KEY=...

# Конфигурация MCP (опционально - автоопределяется если не задано)
MCP_HUB_URL=http://mcp-hub:8765/sse
```

### Запуск Qwen CLI в контейнере

Qwen CLI внутри контейнера автоматически имеет доступ к переменным окружения:

```bash
# Войти в контейнер бота
docker exec -it tg-note-bot bash

# Qwen CLI автоматически использует переменные окружения
qwen "Проанализируй этот код и сохрани insights в памяти"

# MCP Hub доступен по адресу http://mcp-hub:8765/sse
```

### Запуск Qwen CLI на хосте

На хост-машине установите переменные окружения:

```bash
# Экспортировать API ключи
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1

# Запустить qwen CLI
qwen "Проанализируй этот код и сохрани insights в памяти"

# MCP Hub доступен по адресу http://127.0.0.1:8765/sse
```

## Обновление аутентификации

При ротации API ключей:

1. **Обновить файл `.env`:**
   ```bash
   vim .env
   # Обновить OPENAI_API_KEY=...
   ```

2. **Перезапустить контейнеры:**
   ```bash
   docker-compose restart bot
   ```

3. **Проверить доступ к MCP:**
   ```bash
   curl http://127.0.0.1:8765/health
   ```

Не нужно перегенерировать конфигурации MCP - аутентификация обрабатывается отдельно через переменные окружения.

## Диагностика проблем

### MCP Hub недоступен

**Из контейнера бота:**
```bash
docker exec -it tg-note-bot bash
curl http://mcp-hub:8765/health
```

**С хоста:**
```bash
curl http://127.0.0.1:8765/health
```

### Проверка конфигурации MCP

**Конфигурация Qwen CLI:**
```bash
cat ~/.qwen/settings.json
```

**Конфигурация Python клиентов:**
```bash
cat data/mcp_servers/mcp-hub.json
```

### Перегенерация конфигураций

**Внутри контейнера бота:**
```bash
docker exec -it tg-note-bot python -m src.mcp.universal_config_generator --all
```

**На хосте:**
```bash
python -m src.mcp.universal_config_generator --all --url http://127.0.0.1:8765/sse
```

### Проверка логов

**Логи MCP Hub:**
```bash
docker logs tg-note-hub
# или
tail -f logs/mcp_hub.log
```

**Логи бота:**
```bash
docker logs tg-note-bot
# или
tail -f logs/bot.log
```

## Ответы на ваши вопросы

### Как должны выглядеть MCP JSON конфиги?

**Для Qwen CLI (`~/.qwen/settings.json`):**
```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://mcp-hub:8765/sse",  // В Docker
      // или
      "url": "http://127.0.0.1:8765/sse", // На хосте
      "timeout": 10000,
      "trust": true
    }
  },
  "allowMCPServers": ["mcp-hub"]
}
```

**Для общих MCP серверов (`data/mcp_servers/mcp-hub.json`):**
```json
{
  "mcpServers": {
    "mcp-hub": {
      "url": "http://mcp-hub:8765/sse",  // Автоопределяется
      "timeout": 10000,
      "trust": true,
      "description": "MCP Hub - Memory tools"
    }
  }
}
```

### Как Qwen CLI запускается в контейнерах?

1. **Qwen CLI установлен в контейнере бота** (через Dockerfile.bot)
2. **Переменные окружения пробрасываются** через docker-compose.yml:
   ```yaml
   bot:
     environment:
       - OPENAI_API_KEY=${OPENAI_API_KEY}
       - MCP_HUB_URL=http://mcp-hub:8765/sse
   ```
3. **Конфигурация MCP генерируется автоматически** при старте бота
4. **Qwen CLI использует сгенерированную конфигурацию** из `~/.qwen/settings.json`

### Как работает аутентификация?

1. **API ключи хранятся в `.env`** - никогда не в конфигурациях MCP
2. **Docker автоматически пробрасывает** переменные окружения в контейнеры
3. **Qwen CLI читает ключи** из переменных окружения автоматически
4. **При обновлении ключей** - просто рестарт контейнеров, без изменения конфигов

### Доступ для других локальных LLM

Для других локальных LLM (например, запущенных через LM Studio, Ollama с MCP поддержкой):

```bash
# Сгенерировать конфигурации для всех клиентов
python -m src.mcp.universal_config_generator --all --url http://127.0.0.1:8765/sse

# Или для конкретного клиента
python -m src.mcp.universal_config_generator --lmstudio --url http://127.0.0.1:8765/sse
```

Это создаст конфигурационные файлы с правильными URL для доступа с хост-машины.

## Лучшие практики

1. **Используйте переменные окружения** - Храните все секреты в `.env`, никогда в конфигах
2. **Автоопределение окружения** - Позвольте системе автоматически определять Docker vs хост
3. **Регенерация при развёртывании** - MCP конфигурации автогенерируются при старте контейнеров
4. **Единообразие портов** - Держите MCP Hub на порту 8765 для консистентности
5. **Проверки здоровья** - Используйте `/health` эндпоинт для проверки работы MCP Hub

## Ссылки

- [MCP Configuration Format](../agents/mcp-config-format.md)
- [MCP Tools Documentation](../agents/mcp-tools.md)
- [Qwen CLI Documentation](../agents/qwen-code-cli.md)
- [Docker Deployment](./docker.md)
