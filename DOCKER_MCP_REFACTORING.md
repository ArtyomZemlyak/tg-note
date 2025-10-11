# MCP Refactoring для Docker

## Что изменилось

### 1. Удален memory_server_http.py
- ❌ Удален `src/agents/mcp/memory/memory_server_http.py`
- ✅ Заменен на `src/agents/mcp/mcp_hub_server.py`

### 2. MCPClient - добавлен HTTP/SSE транспорт
- ✅ Поддержка `transport="stdio"` (subprocess)
- ✅ Поддержка `transport="sse"` (HTTP/SSE для Docker)
- ✅ Автоматическое определение транспорта

### 3. MCPServerManager - Docker mode
- ✅ Определяет Docker режим по `MCP_HUB_URL` env var
- ✅ Docker: создает конфиг для подключения к URL
- ✅ Standalone: запускает mcp_hub_server как subprocess

### 4. MCPRegistryClient - HTTP/SSE клиенты
- ✅ Читает URL из конфига memory.json
- ✅ Создает HTTP/SSE клиент если есть URL
- ✅ Создает stdio клиент если URL нет

## Логика работы

### Docker режим (с MCP_HUB_URL):
```
Bot запускается
↓
MCPServerManager.setup_default_servers()
↓
Находит MCP_HUB_URL env var
↓
Создает config: {"mcpServers": {"memory": {"url": "http://mcp-hub:8765/sse"}}}
↓
MCPRegistryClient.connect_all_enabled()
↓
MCPClient с transport="sse" подключается к mcp-hub
```

### Standalone режим (без MCP_HUB_URL):
```
Bot запускается
↓
MCPServerManager.setup_default_servers()
↓
НЕ находит MCP_HUB_URL
↓
Регистрирует subprocess: python -m src.agents.mcp.mcp_hub_server
↓
Запускает mcp_hub_server локально
↓
MCPClient с transport="stdio" подключается к subprocess
```

## Конфигурация

### Docker (.env):
```bash
MCP_HUB_URL=http://mcp-hub:8765/sse
AGENT_ENABLE_MCP_MEMORY=true
```

### Standalone (config.yaml):
```yaml
AGENT_ENABLE_MCP_MEMORY: true
# MCP_HUB_URL не указываем - запустит subprocess
```

## Преимущества

1. ✅ **Единая архитектура**: Bot всегда подключается через MCPClient
2. ✅ **Docker-native**: Использует URL контейнера вместо subprocess
3. ✅ **Backward compatible**: Standalone режим работает как раньше
4. ✅ **Гибкость**: Легко переключаться между режимами

## Файлы с изменениями

- `src/agents/mcp/client.py` - HTTP/SSE транспорт
- `src/agents/mcp/server_manager.py` - Docker mode detection
- `src/agents/mcp/registry_client.py` - HTTP клиенты
- ~~`src/agents/mcp/memory/memory_server_http.py`~~ - УДАЛЕН

