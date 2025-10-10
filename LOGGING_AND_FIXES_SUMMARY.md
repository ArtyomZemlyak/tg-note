# Логирование и Исправления для Memory Services

## Обзор

Добавлено полное логирование ошибок для всех компонентов памяти и исправлена проблема с mem-agent режимом.

## Реализованные Изменения

### 1. Memory MCP Server (memory_server.py)

**Добавлено:**
- Файловое логирование в `logs/memory_mcp.log` (DEBUG уровень)
- Отдельный лог ошибок в `logs/memory_mcp_errors.log` (ERROR уровень)
- Детальное логирование всех вызовов инструментов
- Логирование параметров при ошибках

**Особенности:**
- Ротация логов при достижении 10 MB
- Хранение логов: 7 дней (общие), 30 дней (ошибки)
- Автоматическое сжатие старых логов в zip
- Backtrace и diagnose для полной диагностики

### 2. Mem-Agent Implementation

#### agent.py
**Добавлено:**
- Файловое логирование в `logs/mem_agent.log`
- Отдельный лог ошибок в `logs/mem_agent_errors.log`
- Логирование инициализации агента с параметрами
- Детальное логирование процесса chat:
  - Начало и завершение каждого запроса
  - Извлечение thoughts, reply, python_code
  - Выполнение Python кода
  - Цикл выполнения инструментов

#### engine.py (Sandboxed Code Execution)
**Добавлено:**
- Файловое логирование в `logs/mem_agent_sandbox.log`
- Отдельный лог ошибок в `logs/mem_agent_sandbox_errors.log`
- Логирование запуска и завершения sandboxed процессов
- Детальная диагностика ошибок выполнения кода
- Логирование timeout и других проблем subprocess

#### mcp_server.py (FastMCP Server для Mem-Agent)
**Добавлено:**
- Файловое логирование в `logs/mem_agent_mcp_server.log`
- Отдельный лог ошибок в `logs/mem_agent_mcp_server_errors.log`
- Логирование всех MCP tool вызовов:
  - chat_with_memory
  - query_memory
  - save_to_memory
  - list_memory_structure
- Логирование запуска и остановки сервера

### 3. vLLM Server Logging

**Добавлено в agent.py:**
- Логирование запуска vLLM сервера в `logs/vllm_server.log`
- Отдельный лог ошибок в `logs/vllm_server_errors.log`
- Аналогично для MLX сервера (macOS):
  - `logs/mlx_server.log`
  - `logs/mlx_server_errors.log`
- Логирование проверки доступности сервера
- Детальное логирование процесса запуска
- Логирование ожидания готовности сервера

### 4. ИСПРАВЛЕНИЕ: Memory MCP в Mem-Agent Режиме

**Проблема:**
`memory_server_http.py` не поддерживал mem-agent режим, так как был жёстко закодирован на использование `MemoryStorage` (JSON storage).

**Решение:**
Обновлён `memory_server_http.py`:

1. **Добавлена поддержка MemoryStorageFactory:**
   ```python
   from src.agents.mcp.memory.memory_factory import MemoryStorageFactory
   ```

2. **Обновлена функция init_storage():**
   - Теперь использует `MEM_AGENT_STORAGE_TYPE` environment variable
   - Поддерживает все типы хранилища: "json", "vector", "mem-agent"
   - Автоматический fallback к JSON при ошибках
   - Передаёт параметры `MEM_AGENT_MODEL` и `MEM_AGENT_USE_VLLM`

3. **Добавлено логирование:**
   - `logs/memory_http.log` - общий лог
   - `logs/memory_http_errors.log` - ошибки
   - Логирование типа хранилища при инициализации
   - Детальное логирование всех операций

**Как использовать mem-agent режим:**

Установите environment переменные:
```bash
export MEM_AGENT_STORAGE_TYPE="mem-agent"
export MEM_AGENT_MODEL="driaforall/mem-agent"
export MEM_AGENT_USE_VLLM="true"  # или "false" для OpenRouter
```

При запуске memory HTTP сервера он теперь:
1. Прочитает `MEM_AGENT_STORAGE_TYPE`
2. Создаст `MemAgentStorage` через factory
3. Все memory операции будут использовать LLM-based память

## Структура Логов

Все логи сохраняются в директорию `logs/`:

```
logs/
├── memory_mcp.log              # Memory MCP stdio server (общий)
├── memory_mcp_errors.log       # Memory MCP stdio server (ошибки)
├── memory_http.log             # Memory MCP HTTP server (общий)
├── memory_http_errors.log      # Memory MCP HTTP server (ошибки)
├── mem_agent.log               # Mem-agent (общий)
├── mem_agent_errors.log        # Mem-agent (ошибки)
├── mem_agent_sandbox.log       # Sandboxed code execution (общий)
├── mem_agent_sandbox_errors.log # Sandboxed code execution (ошибки)
├── mem_agent_mcp_server.log    # Mem-agent MCP server (общий)
├── mem_agent_mcp_server_errors.log # Mem-agent MCP server (ошибки)
├── vllm_server.log             # vLLM server output
├── vllm_server_errors.log      # vLLM server errors
├── mlx_server.log              # MLX server output (macOS)
└── mlx_server_errors.log       # MLX server errors (macOS)
```

## Настройка Логирования

### Уровни Логирования

Все компоненты поддерживают DEBUG уровень для детальной диагностики:

**Memory Servers:**
```bash
python -m src.agents.mcp.memory.memory_server --log-level DEBUG
python -m src.agents.mcp.memory.memory_server_http --log-level DEBUG
```

**Environment Variables:**
Логирование автоматически активируется при импорте модулей.

### Ротация и Хранение

- **Общие логи:** 10 MB rotation, 7 дней хранения
- **Логи ошибок:** 10 MB rotation, 30 дней хранения
- **Сжатие:** Автоматическое zip-сжатие старых логов
- **Backtrace:** Включён для полной трассировки ошибок
- **Diagnose:** Включён для детальной диагностики

## Диагностика Проблем

### Memory MCP не работает

1. **Проверьте логи:**
   ```bash
   tail -f logs/memory_http.log
   tail -f logs/memory_http_errors.log
   ```

2. **Проверьте storage type:**
   ```bash
   grep "Storage type" logs/memory_http.log
   ```

3. **Проверьте инициализацию:**
   ```bash
   grep "initialized successfully" logs/memory_http.log
   ```

### Mem-Agent проблемы

1. **Логи агента:**
   ```bash
   tail -f logs/mem_agent.log
   tail -f logs/mem_agent_errors.log
   ```

2. **Логи sandbox:**
   ```bash
   tail -f logs/mem_agent_sandbox.log
   tail -f logs/mem_agent_sandbox_errors.log
   ```

3. **Логи vLLM/MLX:**
   ```bash
   tail -f logs/vllm_server.log
   tail -f logs/vllm_server_errors.log
   ```

### qwen CLI не видит инструменты

1. **Проверьте MCP server:**
   ```bash
   tail -f logs/mem_agent_mcp_server.log
   ```

2. **Проверьте вызовы инструментов:**
   ```bash
   grep "called with" logs/mem_agent_mcp_server.log
   ```

3. **Проверьте ошибки:**
   ```bash
   tail -f logs/mem_agent_mcp_server_errors.log
   ```

## Тестирование

Для проверки работы логирования:

1. **Запустите Memory HTTP server:**
   ```bash
   export MEM_AGENT_STORAGE_TYPE="mem-agent"
   python -m src.agents.mcp.memory.memory_server_http --log-level DEBUG
   ```

2. **Проверьте создание логов:**
   ```bash
   ls -lh logs/
   ```

3. **Наблюдайте за логами в реальном времени:**
   ```bash
   tail -f logs/memory_http.log
   ```

4. **Проверьте логи ошибок:**
   ```bash
   tail -f logs/memory_http_errors.log
   ```

## Заключение

Теперь все компоненты памяти имеют полное логирование:
- ✅ Memory MCP (stdio и HTTP)
- ✅ Mem-Agent (agent, engine, MCP server)
- ✅ vLLM/MLX серверы
- ✅ Исправлен mem-agent режим в memory HTTP server

Все логи пишутся в файлы в директории `logs/`, что упрощает диагностику и отладку.
