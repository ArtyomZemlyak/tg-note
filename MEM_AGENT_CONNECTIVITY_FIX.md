# Исправление подключения mem-agent к qwen-code-cli

## Проблема
```
🔴 mem-agent - Disconnected (0 tools cached):
    Memory storage and retrieval agent
  No tools or prompts available
```

## Причина
Отсутствовала конфигурация `.qwen/settings.json`, которая указывает qwen-code-cli как подключиться к MCP серверу mem-agent.

## Что было сделано

### 1. ✅ Создана STDIO конфигурация (по умолчанию)
**Файл:** `~/.qwen/settings.json`

```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "python3",
      "args": ["src/agents/mcp/mem_agent_server.py"],
      "cwd": "/workspace",
      "timeout": 10000,
      "trust": true,
      "description": "Memory storage and retrieval agent"
    }
  },
  "allowMCPServers": ["mem-agent"]
}
```

**Как работает:**
- qwen-code-cli автоматически запускает сервер при подключении
- Сервер общается через stdin/stdout
- Не требует ручного запуска

### 2. ✅ Создан HTTP/SSE сервер (альтернатива)
**Файл:** `src/agents/mcp/mem_agent_server_http.py`

**Конфигурация:** `~/.qwen/settings-http.json`

```json
{
  "mcpServers": {
    "mem-agent": {
      "url": "http://127.0.0.1:8765/sse",
      "timeout": 10000,
      "trust": true,
      "description": "Memory storage and retrieval agent (HTTP/SSE)"
    }
  },
  "allowMCPServers": ["mem-agent"]
}
```

**Как работает:**
- HTTP сервер запускается вручную в отдельном терминале
- Подключение через HTTP/SSE
- Лучше производительность, работает со всеми клиентами

### 3. ✅ Обновлен генератор конфигурации
**Файл:** `src/agents/mcp/qwen_config_generator.py`

Теперь поддерживает оба режима:
```python
# STDIO (по умолчанию)
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config
setup_qwen_mcp_config(global_config=True)

# HTTP
setup_qwen_mcp_config(global_config=True, use_http=True, http_port=8765)
```

### 4. ✅ Создана документация
**Файл:** `docs/MEM_AGENT_TRANSPORT_OPTIONS.md`

Подробное описание обоих режимов работы и диагностика проблем.

---

## Как использовать

### Вариант 1: STDIO (рекомендуется для начала)

1. **Конфигурация уже создана** в `~/.qwen/settings.json`

2. **Перезапустите qwen-code-cli:**
   ```bash
   # В вашем терминале где запущен qwen-code-cli
   # Просто перезапустите его
   ```

3. **Проверьте подключение:**
   - Mem-agent должен показывать статус "Connected" с 3 tools cached:
     - `store_memory`
     - `retrieve_memory`
     - `list_categories`

### Вариант 2: HTTP (если STDIO не работает)

1. **Запустите HTTP сервер** (в отдельном терминале):
   ```bash
   cd /workspace
   python3 src/agents/mcp/mem_agent_server_http.py
   ```

2. **Переключитесь на HTTP конфигурацию:**
   ```bash
   cp ~/.qwen/settings-http.json ~/.qwen/settings.json
   ```

3. **Перезапустите qwen-code-cli**

4. **Проверьте подключение**

---

## Диагностика

### Проблема: Все еще "Disconnected"

**Проверьте конфигурацию:**
```bash
cat ~/.qwen/settings.json
```

Должна содержать конфигурацию mem-agent (см. выше).

**Проверьте что сервер запускается:**
```bash
cd /workspace
python3 src/agents/mcp/mem_agent_server.py --help
```

Если выдает ошибки о missing modules, установите зависимости:
```bash
pip install loguru pydantic
```

### Проблема: "Module not found"

**Убедитесь что работаете из /workspace:**
```bash
cd /workspace
python3 -c "from src.mem_agent.storage import MemoryStorage; print('OK')"
```

### Проблема: HTTP сервер не стартует

**Установите fastmcp:**
```bash
pip install fastmcp
```

**Проверьте что порт свободен:**
```bash
lsof -i :8765
```

---

## Тестирование

### Тест STDIO сервера
```bash
cd /workspace
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 src/agents/mcp/mem_agent_server.py
```

Должен вывести список из 3 tools.

### Тест HTTP сервера
```bash
# Терминал 1: запустите сервер
python3 src/agents/mcp/mem_agent_server_http.py

# Терминал 2: проверьте
curl http://127.0.0.1:8765/health
```

---

## Файлы конфигурации

### Созданные файлы:
1. `~/.qwen/settings.json` - STDIO конфигурация (активная)
2. `~/.qwen/settings-http.json` - HTTP конфигурация (резервная)

### Новые файлы кода:
1. `src/agents/mcp/mem_agent_server_http.py` - HTTP сервер
2. `docs/MEM_AGENT_TRANSPORT_OPTIONS.md` - документация

### Обновленные файлы:
1. `src/agents/mcp/qwen_config_generator.py` - добавлена поддержка HTTP

---

## Рекомендации

1. **Начните с STDIO** - она уже настроена и должна работать
2. **Если проблемы** - попробуйте HTTP режим
3. **Для production** - используйте HTTP с systemd или supervisor для автозапуска

---

## Дополнительная помощь

См. полную документацию в:
- `docs/MEM_AGENT_TRANSPORT_OPTIONS.md` - режимы работы и диагностика
- `docs_site/agents/mem-agent-setup.md` - общая настройка mem-agent
- `docs/MCP_CONFIGURATION_GUIDE.md` - конфигурация MCP серверов

---

## Следующие шаги

1. Перезапустите qwen-code-cli
2. Проверьте что mem-agent подключен (должно быть "Connected" с 3 tools)
3. Попробуйте использовать память:
   ```
   # В qwen-code-cli
   store_memory("Test note", category="test")
   retrieve_memory(query="Test")
   ```

Если все равно не работает - попробуйте HTTP вариант (см. "Вариант 2" выше).