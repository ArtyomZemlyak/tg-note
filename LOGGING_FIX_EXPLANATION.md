# Исправление проблемы с пустыми логами

## 🐛 Проблема

Логи в файлах `logs/memory_http.log` и `logs/mlx_server.log` оставались пустыми, несмотря на то, что серверы были запущены.

## 🔍 Причины

### 1. **memory_server_http.py** - Двойной вызов `logger.remove()`

**Файл:** `src/agents/mcp/memory/memory_server_http.py`

**Проблема:**
```python
# Строка 39 - в начале модуля
logger.remove()
logger.add(log_dir / "memory_http.log", level="DEBUG", ...)  # Добавили файловый обработчик

# ...

# Строки 297-302 - в функции main()
def main():
    args = parser.parse_args()
    
    logger.remove()  # ❌ УДАЛЯЕТ ВСЕ ОБРАБОТЧИКИ, включая файловые!
    logger.add(sys.stderr, level=args.log_level)  # Добавляет только консольный
```

**Результат:**
- При запуске сервера функция `main()` вызывает `logger.remove()`
- Это удаляет файловые обработчики, добавленные в начале модуля
- Логи идут **только в консоль** (stderr), но не в файлы

### 2. **agent.py** - Преждевременное закрытие файлов

**Файл:** `src/agents/mcp/memory/mem_agent_impl/agent.py`

**Проблема с MLX сервером (строки 239-258):**
```python
try:
    with open(mlx_log_file, "a") as log_f, open(mlx_error_file, "a") as err_f:
        log_f.write("=== MLX server startup ===\n")
        
        subprocess.Popen(
            ["mlx_lm", "serve", ...],
            stdout=log_f,
            stderr=err_f,
        )
    # ❌ ЗДЕСЬ блок with заканчивается и файлы ЗАКРЫВАЮТСЯ!
    # Процесс mlx_lm продолжает работать, но не может писать в закрытые файлы
```

**Аналогичная проблема с vLLM сервером (строки 179-198)**

**Результат:**
- Файлы открываются, записывается заголовок
- Запускается subprocess
- Блок `with` завершается и **закрывает файлы**
- Subprocess пытается писать в закрытые файлы → логи не сохраняются

## ✅ Решение

### 1. Исправлено в `memory_server_http.py`

```python
# Закомментировали проблемный код в main()
def main():
    args = parser.parse_args()
    
    # Configure logging level
    # NOTE: Don't call logger.remove() here - file handlers are already configured at module level
    # Just update the log level if needed
    # logger.remove()
    # logger.add(
    #     sys.stderr,
    #     format="...",
    #     level=args.log_level,
    # )
```

**Результат:**
- Файловые обработчики, добавленные в начале модуля, продолжают работать
- Логи сохраняются в `logs/memory_http.log` и `logs/memory_http_errors.log`

### 2. Исправлено в `agent.py`

**Для MLX сервера:**
```python
# Open log files (keep them open for the subprocess)
log_f = open(mlx_log_file, "a")
err_f = open(mlx_error_file, "a")

log_f.write(f"\n=== MLX server startup at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
err_f.write(f"\n=== MLX server startup at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
log_f.flush()
err_f.flush()

subprocess.Popen(
    ["mlx_lm", "serve", ...],
    stdout=log_f,
    stderr=err_f,
)
# ✅ Файлы остаются открытыми для процесса
```

**Аналогично для vLLM сервера**

**Результат:**
- Файлы остаются открытыми после запуска subprocess
- Процессы могут писать в них логи
- Логи сохраняются в `logs/mlx_server.log` и `logs/vllm_server.log`

## 📊 Итоговые изменения

### Изменённые файлы:

1. **`src/agents/mcp/memory/memory_server_http.py`**
   - Закомментирован `logger.remove()` в функции `main()`
   - Файловые обработчики логов теперь работают корректно

2. **`src/agents/mcp/memory/mem_agent_impl/agent.py`**
   - Исправлено управление файлами для MLX сервера (строки 239-263)
   - Исправлено управление файлами для vLLM сервера (строки 179-203)
   - Файлы остаются открытыми для subprocess

## 🎯 Проверка работы

После исправлений логи должны сохраняться:

```bash
# Memory HTTP сервер
tail -f logs/memory_http.log
tail -f logs/memory_http_errors.log

# MLX сервер (macOS)
tail -f logs/mlx_server.log
tail -f logs/mlx_server_errors.log

# vLLM сервер (Linux)
tail -f logs/vllm_server.log
tail -f logs/vllm_server_errors.log
```

## 💡 Уроки

1. **Не вызывайте `logger.remove()` повторно** после настройки логгеров
2. **Держите файлы открытыми** для subprocess, не используйте `with` 
3. **Всегда вызывайте `flush()`** после записи, чтобы данные сохранились
4. **Тестируйте логирование** сразу после настройки

## 🔧 Для разработчиков

Если нужно изменить уровень логирования в runtime:
```python
# Вместо logger.remove() + logger.add()
# Используйте configure или создайте отдельную функцию
from loguru import logger

def update_log_level(level: str):
    # Обновить существующие обработчики
    logger.configure(handlers=[
        {"sink": sys.stderr, "level": level},
        {"sink": "logs/app.log", "level": level},
    ])
```
