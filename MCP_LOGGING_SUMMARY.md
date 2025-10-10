# MCP Servers Logging Implementation - Summary

## ✅ Completed Tasks

Реализовано полное логирование для всех MCP серверов с ротацией и централизованным хранением.

### 1. Memory MCP Server (HTTP/SSE)
**Файл**: `src/agents/mcp/memory/memory_server_http.py`

**Изменения**:
- ✅ Добавлено логирование в файл с автоматической ротацией (10 MB)
- ✅ Хранение логов 7 дней с автоматическим сжатием
- ✅ Параметр `--log-file` для указания пути к логу
- ✅ Параметр `--log-level` для уровня логирования
- ✅ Обработка ошибок во всех MCP tools с полным stack trace
- ✅ Логирование всех операций: store_memory, retrieve_memory, list_categories

**Логи**:
- Основной лог: `logs/mcp_servers/memory_mcp.log`
- Console output: `logs/mcp_servers/memory_mcp_stdout.log`

**Формат логов**:
```
2025-10-10 10:41:22 | INFO     | __main__:main:217 - Starting memory HTTP MCP server
2025-10-10 10:41:22 | ERROR    | __main__:store_memory:106 - Error storing memory: Connection timeout
```

### 2. Mem-Agent MCP Server
**Файл**: `src/agents/mcp/memory/mem_agent_impl/mcp_server.py`

**Изменения**:
- ✅ Добавлено логирование в файл с ротацией
- ✅ Параметры `--log-file` и `--log-level`
- ✅ Обработка ошибок во всех async tools
- ✅ Логирование: chat_with_memory, query_memory, save_to_memory, list_memory_structure

**Логи**:
- Основной лог: `logs/mcp_servers/mem_agent.log`
- Console output: `logs/mcp_servers/mem_agent_stdout.log`

### 3. vLLM Server Wrapper
**Файл**: `scripts/start_vllm_server.py`

**Функциональность**:
- ✅ Обёртка для vLLM сервера с логированием
- ✅ Раздельные логи для stdout и stderr
- ✅ Автоматическое создание symlinks на последние логи
- ✅ Timestamped лог файлы
- ✅ Потоковый вывод в реальном времени + запись в файл

**Логи**:
- Основной лог: `logs/mcp_servers/vllm_server_YYYYMMDD_HHMMSS.log`
- Ошибки: `logs/mcp_servers/vllm_server_YYYYMMDD_HHMMSS.error.log`
- Symlinks: `vllm_server_latest.log`, `vllm_server_latest_error.log`

### 4. Централизованное Управление
**Файл**: `scripts/manage_mcp_servers.sh`

**Функции**:
- ✅ Start/stop/restart всех серверов
- ✅ Проверка статуса
- ✅ Просмотр логов в реальном времени
- ✅ Управление PID файлами
- ✅ Graceful shutdown с timeout

**Команды**:
```bash
# Запуск
./scripts/manage_mcp_servers.sh start [memory|mem-agent|vllm|all]

# Остановка
./scripts/manage_mcp_servers.sh stop [memory|mem-agent|vllm|all]

# Перезапуск
./scripts/manage_mcp_servers.sh restart [memory|mem-agent|vllm|all]

# Статус
./scripts/manage_mcp_servers.sh status

# Просмотр логов
./scripts/manage_mcp_servers.sh logs memory [количество_строк]
./scripts/manage_mcp_servers.sh logs mem-agent
./scripts/manage_mcp_servers.sh logs vllm
```

## 📁 Структура Логов

```
logs/
└── mcp_servers/
    ├── memory_mcp.log                   # Memory MCP детальные логи
    ├── memory_mcp_stdout.log            # Memory MCP stdout/stderr
    ├── memory_mcp.log.1.gz              # Ротированные логи (сжатые)
    ├── mem_agent.log                    # Mem-Agent детальные логи
    ├── mem_agent_stdout.log             # Mem-Agent stdout/stderr
    ├── vllm_server_20251010_104122.log  # vLLM лог с timestamp
    ├── vllm_server_latest.log           # Symlink на последний vLLM лог
    ├── vllm_server_latest_error.log     # Symlink на последние ошибки
    └── pids/                            # PID файлы для управления
        ├── memory_mcp.pid
        ├── mem_agent.pid
        └── vllm_server.pid
```

## 🔧 Особенности Логирования

### Уровни Логирования
- **DEBUG**: Детальная информация о всех вызовах функций
- **INFO**: Общая информация о работе сервера (по умолчанию)
- **WARNING**: Предупреждения о потенциальных проблемах
- **ERROR**: Ошибки с полным stack trace

### Автоматическая Ротация
- Триггер: Файл достигает 10 MB
- Retention: 7 дней
- Сжатие: Старые логи в gzip формате
- Формат: `logfile.log.1.gz`, `logfile.log.2.gz`, и т.д.

### Обработка Ошибок
Все MCP tools обёрнуты в try-except блоки:
```python
try:
    logger.debug(f"Operation started: {params}")
    result = operation()
    logger.info("Operation completed successfully")
    return result
except Exception as e:
    logger.error(f"Error in operation: {e}", exc_info=True)
    return {"success": False, "error": str(e)}
```

## 📖 Документация

Создана полная документация: `docs_site/deployment/mcp-servers-logging.md`

Включает:
- Структуру логов
- Управление серверами
- Форматы логов
- Мониторинг и анализ
- Troubleshooting
- Best practices

## 🚀 Использование

### Быстрый Старт

```bash
# 1. Запустить все серверы
./scripts/manage_mcp_servers.sh start

# 2. Проверить статус
./scripts/manage_mcp_servers.sh status

# 3. Посмотреть логи
./scripts/manage_mcp_servers.sh logs memory
```

### Ручной Запуск с Логированием

```bash
# Memory MCP Server
python3 -m src.agents.mcp.memory.memory_server_http \
    --log-file logs/mcp_servers/memory_mcp.log \
    --log-level DEBUG

# Mem-Agent Server
python3 -m src.agents.mcp.memory.mem_agent_impl.mcp_server \
    --log-file logs/mcp_servers/mem_agent.log \
    --log-level INFO

# vLLM Server
python3 scripts/start_vllm_server.py \
    --model driaforall/mem-agent \
    --log-dir logs/mcp_servers
```

### Мониторинг

```bash
# Следить за всеми ошибками
tail -f logs/mcp_servers/*.log | grep ERROR

# Следить за конкретным сервером
tail -f logs/mcp_servers/memory_mcp.log

# Поиск проблем
grep -i "connection\|timeout\|failed" logs/mcp_servers/*.log
```

## ✨ Преимущества

1. **Централизованное хранение**: Все логи в одной директории
2. **Автоматическая ротация**: Не нужно вручную чистить логи
3. **Сжатие**: Экономия дискового пространства
4. **Детальная диагностика**: Полные stack traces для ошибок
5. **Удобное управление**: Единый скрипт для всех серверов
6. **Symlinks для vLLM**: Всегда известно, где последний лог
7. **PID tracking**: Простое управление процессами
8. **Graceful shutdown**: Корректное завершение серверов

## 📝 Примеры Логов

### Успешная операция
```
2025-10-10 10:41:22 | INFO     | __main__:init_storage:73 - Using shared memory path: data/memory/shared
2025-10-10 10:41:22 | DEBUG    | __main__:store_memory:99 - Storing memory: category=general, content_length=42
2025-10-10 10:41:22 | INFO     | __main__:store_memory:103 - Memory stored successfully: mem_123456
```

### Ошибка с Stack Trace
```
2025-10-10 10:41:23 | ERROR    | __main__:store_memory:106 - Error storing memory: Connection timeout
Traceback (most recent call last):
  File "/workspace/src/agents/mcp/memory/memory_server_http.py", line 100, in store_memory
    result = storage.store(...)
  File "/workspace/src/agents/mcp/memory/memory_storage.py", line 150, in store
    self._write_to_db()
ConnectionError: Connection timeout after 30s
```

## 🎯 Следующие Шаги

Система логирования полностью готова к использованию:

1. ✅ Все серверы имеют файловое логирование
2. ✅ Автоматическая ротация и очистка
3. ✅ Централизованное управление
4. ✅ Детальная документация

Можно сразу запускать серверы и мониторить логи!

## 📚 См. также

- Документация: `docs_site/deployment/mcp-servers-logging.md`
- Скрипт управления: `scripts/manage_mcp_servers.sh`
- vLLM wrapper: `scripts/start_vllm_server.py`
