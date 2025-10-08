# MCP HTTP/SSE Быстрый старт / Quick Start Guide

## 🚀 Быстрый старт / Quick Start

### 1. Запустите HTTP сервер / Start HTTP Server

```bash
python3 -m src.agents.mcp.mem_agent_server_http
```

Сервер запустится на `http://127.0.0.1:8765`

Server will start on `http://127.0.0.1:8765`

### 2. Проверьте статус / Check Status

```bash
curl http://127.0.0.1:8765/health
```

Должно вернуть / Should return: `{"status":"healthy"}`

### 3. Создайте конфигурацию / Generate Configuration

```bash
python3 -m src.agents.mcp.qwen_config_generator --http
```

Конфигурация будет сохранена в `~/.qwen/settings.json`

Configuration will be saved to `~/.qwen/settings.json`

### 4. Проверьте подключение / Test Connection

```bash
bash scripts/test_mem_agent_connection.sh
```

## 📋 Формат конфигурации / Configuration Format

### HTTP/SSE (новый по умолчанию) / HTTP/SSE (new default)

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

### STDIO (старый формат) / STDIO (legacy format)

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

## 🔧 Использование в коде / Usage in Code

### HTTP режим (default)

```python
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config

# HTTP mode is default
setup_qwen_mcp_config(
    user_id=123,
    global_config=True
)
```

### STDIO режим (legacy)

```python
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config

# Explicitly use STDIO
setup_qwen_mcp_config(
    user_id=123,
    global_config=True,
    use_http=False  # Use STDIO instead
)
```

### Custom порт / Custom Port

```python
from src.agents.mcp.qwen_config_generator import setup_qwen_mcp_config

# Use custom port
setup_qwen_mcp_config(
    user_id=123,
    global_config=True,
    use_http=True,
    http_port=9000  # Custom port
)
```

## 🐛 Troubleshooting

### Проблема: Сервер не запускается / Problem: Server won't start

```bash
# Проверить зависимости / Check dependencies
pip install fastmcp

# Проверить порт / Check if port is free
lsof -i :8765

# Убить процесс / Kill process if needed
kill $(lsof -t -i:8765)
```

### Проблема: Старая конфигурация STDIO / Problem: Old STDIO config

```bash
# Удалить старую конфигурацию / Remove old config
rm ~/.qwen/settings.json

# Создать новую HTTP конфигурацию / Create new HTTP config
python3 -m src.agents.mcp.qwen_config_generator --http
```

### Проблема: Сервер не отвечает / Problem: Server not responding

```bash
# Проверить health endpoint
curl http://127.0.0.1:8765/health

# Проверить логи / Check logs
tail -f mem_agent.log

# Перезапустить сервер / Restart server
pkill -f mem_agent_server_http
python3 -m src.agents.mcp.mem_agent_server_http
```

## 📊 Проверка конфигурации / Check Configuration

### Посмотреть конфигурацию / View configuration

```bash
cat ~/.qwen/settings.json | jq .
```

### Проверить формат / Check format

```bash
# HTTP формат должен содержать "url"
grep -q '"url".*"http://127.0.0.1:8765/sse"' ~/.qwen/settings.json && echo "HTTP format ✓" || echo "Not HTTP format ✗"

# STDIO формат содержит "command"
grep -q '"command"' ~/.qwen/settings.json && echo "STDIO format" || echo "Not STDIO format"
```

## 🎯 Endpoints

### Health Check

```bash
curl http://127.0.0.1:8765/health
```

### SSE Connection (используется qwen CLI)

```bash
curl -N http://127.0.0.1:8765/sse
```

## 📚 Дополнительно / Additional Resources

### Документация / Documentation
- `MCP_HTTP_MIGRATION_SUMMARY.md` - Полное описание изменений / Full migration summary
- `docs_site/agents/mem-agent-setup.md` - Руководство по установке / Setup guide
- `scripts/test_mem_agent_connection.sh` - Тестовый скрипт / Test script

### Код / Code
- `src/agents/mcp/mem_agent_server_http.py` - HTTP сервер / HTTP server
- `src/agents/mcp/qwen_config_generator.py` - Генератор конфигурации / Config generator

### Внешние ссылки / External Links
- [MCP Protocol](https://modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [SSE MDN Docs](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

## ✅ Чеклист / Checklist

- [ ] HTTP сервер запущен / HTTP server running
- [ ] Health check работает / Health check works
- [ ] Конфигурация в HTTP формате / Configuration in HTTP format
- [ ] Test script проходит / Test script passes
- [ ] qwen-code-cli перезапущен / qwen-code-cli restarted
- [ ] mem-agent показывает "Connected" / mem-agent shows "Connected"
- [ ] Доступны 3 tools / 3 tools available

## 🎉 Готово! / Done!

Теперь ваш mem-agent MCP сервер работает в HTTP/SSE режиме!

Your mem-agent MCP server is now running in HTTP/SSE mode!
