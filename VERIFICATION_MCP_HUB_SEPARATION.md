# Проверка: Бот больше не запускает MCP Hub

## ✅ Подтверждение архитектуры

### 1. Разделение контейнеров

В `docker-compose.yml` определены **три отдельных контейнера**:

```yaml
services:
  vllm-server:    # LLM сервер для mem-agent
  mcp-hub:        # MCP Hub - отдельный контейнер
  bot:            # Telegram бот
```

### 2. MCP Hub как отдельный сервис

**`mcp-hub` контейнер** (строки 45-80):
- Собирается из `Dockerfile.hub`
- Запускается командой: `python -m src.mcp.mcp_hub_server`
- Слушает порт `8765`
- Имеет собственный healthcheck: `http://localhost:8765/health`
- **Работает независимо от бота**

### 3. Bot только подключается к MCP Hub

**`bot` контейнер** (строки 83-115):
- Собирается из `Dockerfile.bot`
- Запускается командой: `python main.py`
- Получает URL для подключения через переменную окружения:
  ```yaml
  environment:
    - MCP_HUB_URL=http://mcp-hub:8765/sse
  ```
- Зависит от `mcp-hub` через `depends_on`:
  ```yaml
  depends_on:
    mcp-hub:
      condition: service_healthy
  ```

### 4. Логика в коде бота

В `src/mcp/server_manager.py` (строки 280-295):

```python
if self.settings.AGENT_ENABLE_MCP_MEMORY:
    # Проверяем, запущен ли бот в Docker
    mcp_hub_url = os.getenv("MCP_HUB_URL")
    
    if mcp_hub_url:
        # Docker режим: ТОЛЬКО подключение к существующему mcp-hub
        logger.info(f"Docker mode: Connecting to mcp-hub at {mcp_hub_url}")
        self._setup_mcp_hub_connection(mcp_hub_url)
    else:
        # Standalone режим: запуск mcp-hub как subprocess
        logger.info("Standalone mode: Registering memory HTTP server subprocess")
        self._setup_memory_subprocess()
```

**В Docker режиме** (`_setup_mcp_hub_connection`, строки 301-335):
- ✅ Создает только конфигурационный файл `data/mcp_servers/memory.json`
- ✅ Указывает URL существующего MCP Hub
- ❌ **НЕ запускает** никаких процессов
- ❌ **НЕ вызывает** `subprocess.Popen`

**В Standalone режиме** (`_setup_memory_subprocess`, строки 336-409):
- Регистрирует mcp-hub как subprocess через `self.register_server()`
- Вызывается только когда `MCP_HUB_URL` **отсутствует**

### 5. Проверка доступности

Bot проверяет доступность MCP Hub через:

1. **Docker healthcheck** - бот не стартует пока mcp-hub не станет healthy
2. **HTTP запросы** - бот подключается к `http://mcp-hub:8765/sse`
3. **Конфигурация** - создает config файл с URL для SSE транспорта

## 📋 Выводы

### ✅ Подтверждено:

1. **MCP Hub - отдельный контейнер** с собственным Dockerfile
2. **Bot НЕ запускает mcp-hub** в Docker режиме
3. **Bot только проверяет доступность** через healthcheck и URL подключения
4. **Разделение ответственности**:
   - `mcp-hub` контейнер: запуск и работа MCP Hub сервера
   - `bot` контейнер: подключение к MCP Hub как к внешнему сервису

### 🔧 Исправлено:

- Путь к модулю в `Dockerfile.hub` исправлен с `src.agents.mcp.mcp_hub_server` на `src.mcp.mcp_hub_server`

## 🏗️ Архитектура

```
┌─────────────────┐
│  vllm-server    │  Порт: 8001
│  (LLM)          │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  mcp-hub        │  Порт: 8765
│  (MCP Gateway)  │  ← Отдельный контейнер, самостоятельно запускается
└────────┬────────┘
         │
         ↓ HTTP/SSE подключение
┌─────────────────┐
│  bot            │
│  (Telegram Bot) │  ← Только ПОДКЛЮЧАЕТСЯ к mcp-hub, не запускает его
└─────────────────┘
```

## ✅ Результат проверки: УСПЕШНО

Бот-сервис **больше не запускает** mcp-hub самостоятельно.  
MCP Hub - это **отдельный контейнер**, который **самостоятельно работает**.  
Бот **только проверяет доступность** и **подключается** к нему.
