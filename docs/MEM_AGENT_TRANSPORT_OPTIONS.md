# mem-agent MCP Server Transport Options

Сервер mem-agent поддерживает два режима работы:

## 1. **STDIO Transport** (по умолчанию)

### Описание
- Сервер общается через stdin/stdout
- Легче в настройке
- Меньше зависимостей
- Рекомендуется для большинства случаев

### Конфигурация `.qwen/settings.json`
```json
{
  "mcpServers": {
    "mem-agent": {
      "command": "python3",
      "args": [
        "src/agents/mcp/mem_agent_server.py"
      ],
      "cwd": "/workspace",
      "timeout": 10000,
      "trust": true,
      "description": "Memory storage and retrieval agent"
    }
  },
  "allowMCPServers": ["mem-agent"]
}
```

### Запуск (для тестирования)
```bash
cd /workspace
python3 src/agents/mcp/mem_agent_server.py
```

### Плюсы
✅ Простая настройка  
✅ Автоматический запуск при подключении  
✅ Минимум зависимостей  

### Минусы
❌ Может быть медленнее при большой нагрузке  
❌ Некоторые клиенты могут иметь проблемы со stdio  

---

## 2. **HTTP/SSE Transport** (альтернатива)

### Описание
- Сервер работает как HTTP сервис
- Использует Server-Sent Events (SSE)
- Лучше для одновременной работы с несколькими клиентами
- Требует установленный `fastmcp`

### Установка зависимостей
```bash
pip install fastmcp
```

### Запуск сервера (в отдельном терминале)
```bash
cd /workspace
python3 src/agents/mcp/mem_agent_server_http.py --host 127.0.0.1 --port 8765
```

### Конфигурация `.qwen/settings-http.json`
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

### Использование HTTP конфигурации
```bash
# Скопировать HTTP конфигурацию
cp ~/.qwen/settings-http.json ~/.qwen/settings.json

# Или создать симлинк
ln -sf ~/.qwen/settings-http.json ~/.qwen/settings.json
```

### Плюсы
✅ Лучше производительность при большой нагрузке  
✅ Работает со всеми клиентами  
✅ Можно запустить один раз и использовать из разных мест  

### Минусы
❌ Требует ручного запуска сервера  
❌ Дополнительная зависимость (fastmcp)  
❌ Нужно следить за работой процесса  

---

## Какой выбрать?

### Используйте **STDIO** если:
- Вы только начинаете работу с mem-agent
- Хотите минимум настроек
- Работаете локально с одним клиентом
- **Сервер отключается** - stdio запускается автоматически при подключении

### Используйте **HTTP** если:
- Stdio не работает с вашим клиентом
- Нужна лучшая производительность
- Работаете с несколькими клиентами одновременно
- **Сервер показывает "0 tools cached"** - может помочь HTTP

---

## Проверка работы

### Для STDIO (текущая конфигурация по умолчанию)
```bash
# Проверить что файл существует
cat ~/.qwen/settings.json

# Должно содержать "command": "python3"
```

### Для HTTP
```bash
# Запустить сервер
python3 src/agents/mcp/mem_agent_server_http.py

# В другом терминале проверить
curl http://127.0.0.1:8765/health
```

---

## Диагностика проблем

### Проблема: "Disconnected (0 tools cached)"

**Решение 1: Проверьте stdio конфигурацию**
```bash
# Проверьте конфигурацию
cat ~/.qwen/settings.json

# Попробуйте запустить сервер вручную
cd /workspace
python3 src/agents/mcp/mem_agent_server.py
```

**Решение 2: Попробуйте HTTP**
```bash
# Запустите HTTP сервер
python3 src/agents/mcp/mem_agent_server_http.py

# Скопируйте HTTP конфигурацию
cp ~/.qwen/settings-http.json ~/.qwen/settings.json

# Перезапустите qwen-code-cli
```

### Проблема: "Permission denied"
```bash
# Дайте права на выполнение
chmod +x src/agents/mcp/mem_agent_server.py
chmod +x src/agents/mcp/mem_agent_server_http.py
```

### Проблема: "Module not found"
```bash
# Убедитесь что запускаете из корня проекта
cd /workspace

# Проверьте что Python видит модули
python3 -c "from src.mem_agent.storage import MemoryStorage; print('OK')"
```

---

## Текущая конфигурация

Сейчас создана **STDIO** конфигурация в `~/.qwen/settings.json`.

Если она не работает, попробуйте HTTP:
```bash
# 1. Запустите HTTP сервер (в отдельном терминале)
python3 src/agents/mcp/mem_agent_server_http.py

# 2. Переключитесь на HTTP конфигурацию
cp ~/.qwen/settings-http.json ~/.qwen/settings.json

# 3. Перезапустите qwen-code-cli
```