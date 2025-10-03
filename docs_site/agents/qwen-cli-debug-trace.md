# Qwen CLI Agent - DEBUG Трейсинг

## Обзор

QwenCodeCLIAgent поддерживает детальное DEBUG логирование для отладки и мониторинга выполнения qwen-code CLI команды. Это позволяет получить полный трейс выполнения, включая:

- Команды и аргументы CLI
- Входные данные (промпт)
- Выходные данные (результат)
- Переменные окружения
- Время выполнения
- Ошибки и предупреждения

## Быстрый старт

### 1. Настройка логирования

```python
from pathlib import Path
from config.logging_config import setup_logging

# Включить DEBUG логирование
setup_logging(
    log_level="DEBUG",
    log_file=Path("logs/qwen_debug.log"),
    enable_debug_trace=True
)
```

### 2. Использование агента

```python
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

# Создать агента
agent = QwenCodeCLIAgent(
    enable_web_search=True,
    enable_git=True,
    timeout=300
)

# Обработать контент
content = {
    "text": "Ваш текст для обработки",
    "urls": ["https://example.com"]
}

result = await agent.process(content)
```

### 3. Проверить логи

Логи будут сохранены в:
- `logs/qwen_debug.log` - основной лог (все уровни)
- `logs/qwen_debug_debug.log` - только DEBUG сообщения

## Что логируется

### Инициализация агента

```
[DEBUG] [QwenCodeCLIAgent._check_cli_available] Checking qwen CLI availability...
[DEBUG] [QwenCodeCLIAgent._check_cli_available] CLI path: qwen
[DEBUG] [QwenCodeCLIAgent._check_cli_available] Running command: qwen --version
[DEBUG] [QwenCodeCLIAgent._check_cli_available] Return code: 0
[DEBUG] [QwenCodeCLIAgent._check_cli_available] STDOUT: qwen version 1.0.0
[DEBUG] [QwenCodeCLIAgent._check_cli_available] STDERR: 
```

### Выполнение CLI команды

```
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === CLI EXECUTION TRACE START ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Command: qwen
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Working dir: /workspace
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Environment variables:
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli]   OPENAI_API_KEY=sk-xxxxx...
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli]   OPENAI_BASE_URL=https://api.openai.com

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === STDIN (PROMPT) ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Prompt length: 1234 characters
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Prompt preview (first 500 chars):
You are an autonomous content processing agent...

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === FULL PROMPT ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli]
<полный текст промпта>
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === END FULL PROMPT ===

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Starting subprocess at 1234567890.123
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Process created with PID: 12345
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Sending prompt to stdin...

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Process completed in 15.42s
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] Process return code: 0

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === STDERR OUTPUT ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] STDERR length: 0 characters
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] STDERR is empty
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === END STDERR OUTPUT ===

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === STDOUT OUTPUT ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] STDOUT length: 5678 characters
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] STDOUT preview (first 500 chars):
# Machine Learning Article
...

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === FULL STDOUT ===
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli]
<полный текст результата>
[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === END FULL STDOUT ===

[DEBUG] [QwenCodeCLIAgent._execute_qwen_cli] === CLI EXECUTION TRACE END ===
```

### Обработка результата

```
[DEBUG] [QwenCodeCLIAgent] STEP 1: Preparing prompt for qwen-code
[DEBUG] [QwenCodeCLIAgent] Prepared prompt length: 1234 characters

[DEBUG] [QwenCodeCLIAgent] STEP 2: Executing qwen-code CLI
[DEBUG] [QwenCodeCLIAgent] Received result length: 5678 characters

[DEBUG] [QwenCodeCLIAgent] STEP 3: Parsing agent response with standard parser
[DEBUG] [QwenCodeCLIAgent] Result text preview (first 500 chars): ...
[DEBUG] [QwenCodeCLIAgent] Files created: ['path/to/file.md']
[DEBUG] [QwenCodeCLIAgent] Folders created: ['path/to/folder']

[DEBUG] [QwenCodeCLIAgent] STEP 4: Extracting KB structure from response
[DEBUG] [QwenCodeCLIAgent] STEP 5: Extracting title from markdown

[INFO] [QwenCodeCLIAgent] Successfully processed content: title='Machine Learning'
```

## Уровни логирования

### DEBUG
**Когда использовать:** Разработка, отладка, поиск проблем

**Что логируется:**
- Все детали выполнения CLI
- Полные тексты промптов и результатов
- Внутренние переменные
- Шаги обработки

**Пример:**
```python
setup_logging(log_level="DEBUG", enable_debug_trace=True)
```

### INFO
**Когда использовать:** Production, нормальная работа

**Что логируется:**
- Основные события (начало/конец обработки)
- Важная информация (заголовки, категории)
- Успешные операции

**Пример:**
```python
setup_logging(log_level="INFO")
```

### WARNING
**Когда использовать:** Production с минимальным логированием

**Что логируется:**
- Предупреждения (пустые результаты, fallback)
- Потенциальные проблемы

**Пример:**
```python
setup_logging(log_level="WARNING")
```

### ERROR
**Когда использовать:** Минимальное логирование

**Что логируется:**
- Только критические ошибки

**Пример:**
```python
setup_logging(log_level="ERROR")
```

## Примеры использования

### Пример 1: Отладка проблем с CLI

```python
import asyncio
from pathlib import Path
from config.logging_config import setup_logging
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

async def debug_cli_issue():
    # Включить максимально детальное логирование
    setup_logging(
        log_level="DEBUG",
        log_file=Path("logs/debug.log"),
        enable_debug_trace=True
    )
    
    agent = QwenCodeCLIAgent(timeout=60)
    
    try:
        result = await agent.process({
            "text": "Test content",
            "urls": []
        })
        print(f"Success: {result['title']}")
    except Exception as e:
        print(f"Error: {e}")
        print("Check logs/debug.log and logs/debug_debug.log for details")

asyncio.run(debug_cli_issue())
```

### Пример 2: Мониторинг в Production

```python
import asyncio
from pathlib import Path
from config.logging_config import setup_logging
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

async def production_monitoring():
    # Умеренное логирование для production
    setup_logging(
        log_level="INFO",
        log_file=Path("logs/production.log"),
        enable_debug_trace=False
    )
    
    agent = QwenCodeCLIAgent()
    result = await agent.process(content)
    
    # В логах будет только важная информация:
    # - Начало/конец обработки
    # - Заголовок и категория
    # - Ошибки (если есть)

asyncio.run(production_monitoring())
```

### Пример 3: Анализ производительности

```python
import asyncio
import time
from pathlib import Path
from config.logging_config import setup_logging
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

async def performance_analysis():
    # DEBUG для анализа времени выполнения
    setup_logging(
        log_level="DEBUG",
        log_file=Path("logs/performance.log"),
        enable_debug_trace=True
    )
    
    agent = QwenCodeCLIAgent()
    
    start = time.time()
    result = await agent.process(content)
    end = time.time()
    
    print(f"Total time: {end - start:.2f}s")
    # В логах будет детальное время выполнения каждого шага

asyncio.run(performance_analysis())
```

## Чтение логов

### Структура лог-файлов

При `enable_debug_trace=True` создаются два файла:

1. **Основной лог** (`logs/qwen_debug.log`):
   - Все уровни (DEBUG, INFO, WARNING, ERROR)
   - Ротация: 10 MB
   - Хранение: 7 дней
   - Сжатие: ZIP

2. **Debug-only лог** (`logs/qwen_debug_debug.log`):
   - Только DEBUG сообщения
   - Ротация: 50 MB
   - Хранение: 3 дня
   - Сжатие: ZIP

### Формат записей

```
2024-10-03 15:30:45.123 | DEBUG    | qwen_code_cli_agent:_execute_qwen_cli:270 | [QwenCodeCLIAgent._execute_qwen_cli] Executing qwen-code CLI...
│                         │           │                      │                    │
│                         │           │                      │                    └─ Сообщение
│                         │           │                      └─ Номер строки
│                         │           └─ Функция
│                         └─ Уровень
└─ Временная метка
```

### Поиск в логах

```bash
# Найти все CLI вызовы
grep "CLI EXECUTION TRACE" logs/qwen_debug.log

# Найти ошибки
grep "ERROR" logs/qwen_debug.log

# Найти время выполнения
grep "Process completed in" logs/qwen_debug.log

# Посмотреть только промпты
grep -A 20 "FULL PROMPT" logs/qwen_debug_debug.log

# Посмотреть только результаты
grep -A 50 "FULL STDOUT" logs/qwen_debug_debug.log
```

## Безопасность

### Маскировка чувствительных данных

API ключи и токены автоматически маскируются в логах:

```python
# В переменных окружения:
OPENAI_API_KEY=sk-1234567890abcdef1234567890abcdef

# В логах отображается как:
OPENAI_API_KEY=sk-12345...
```

### Защищенные переменные

Автоматически маскируются переменные, содержащие:
- `KEY`
- `TOKEN`
- `SECRET`
- `PASSWORD`

## Производительность

### Влияние на производительность

| Уровень | Overhead | Размер логов | Рекомендация |
|---------|----------|--------------|--------------|
| DEBUG   | ~5-10%   | Большой      | Development  |
| INFO    | ~1-2%    | Средний      | Production   |
| WARNING | <1%      | Малый        | Production   |
| ERROR   | <0.5%    | Минимальный  | Production   |

### Рекомендации

1. **Development/Testing:**
   - Используйте `DEBUG` для отладки
   - `enable_debug_trace=True`

2. **Staging:**
   - Используйте `INFO` или `DEBUG` по необходимости
   - `enable_debug_trace=False` (если не нужен детальный трейс)

3. **Production:**
   - Используйте `INFO` или `WARNING`
   - `enable_debug_trace=False`
   - Включайте `DEBUG` только при расследовании проблем

## Troubleshooting

### Проблема: Логи не создаются

**Решение:**
```python
# Проверьте, что директория существует
from pathlib import Path
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Настройте логирование
setup_logging(log_level="DEBUG", log_file=log_dir / "debug.log")
```

### Проблема: Слишком много логов

**Решение:**
```python
# Уменьшите уровень логирования
setup_logging(log_level="INFO")  # Вместо DEBUG

# Или отключите debug трейсинг
setup_logging(log_level="DEBUG", enable_debug_trace=False)
```

### Проблема: Не вижу детальный трейс CLI

**Решение:**
```python
# Убедитесь, что DEBUG включен
setup_logging(
    log_level="DEBUG",  # Обязательно DEBUG
    enable_debug_trace=True  # Обязательно True
)
```

### Проблема: Логи занимают много места

**Решение:**
```python
# Настройте ротацию и хранение
from loguru import logger

logger.add(
    "logs/app.log",
    rotation="5 MB",    # Ротация при 5 MB (вместо 50 MB)
    retention="2 days", # Хранить 2 дня (вместо 7)
    compression="zip"   # Сжатие
)
```

## Дополнительные ресурсы

- [Пример кода](../../examples/qwen_cli_debug_trace_example.py)
- [Конфигурация логирования](../../config/logging_config.py)
- [QwenCodeCLIAgent исходный код](../../src/agents/qwen_code_cli_agent.py)
- [Документация Loguru](https://loguru.readthedocs.io/)
