# YAML Configuration Support

## Overview

Приложение теперь поддерживает загрузку конфигурации из YAML файла в дополнение к `.env` файлу и переменным окружения.

## Порядок приоритета

Конфигурация загружается из нескольких источников с следующим приоритетом (от высшего к низшему):

1. **Переменные окружения (Environment Variables)** - наивысший приоритет
2. **Аргументы командной строки (CLI)** - будет реализовано в будущем
3. **Файл .env** - для credentials и переопределения
4. **Файл config.yaml** - базовая конфигурация
5. **Значения по умолчанию** - встроенные в код

> **Важно:** Первый источник, который содержит значение для конкретного параметра, определяет финальное значение. Это означает, что переменные окружения переопределяют все остальные источники.

## Структура файлов

### config.yaml
Содержит все **не-чувствительные** настройки:
- Пути к директориям
- Настройки обработки
- Настройки логирования
- Git конфигурация

**НЕ ХРАНИТЕ** в YAML файле:
- Токены API
- Пароли
- Ключи доступа
- Другие credentials

### .env файл
Содержит **чувствительные** данные:
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `OPENAI_API_KEY` - API ключ OpenAI (опционально)
- `ANTHROPIC_API_KEY` - API ключ Anthropic (опционально)

## Пример использования

### 1. config.yaml (базовая конфигурация)
```yaml
# Knowledge Base Settings
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true
KB_GIT_REMOTE: origin
KB_GIT_BRANCH: main

# Processing Settings
MESSAGE_GROUP_TIMEOUT: 30
PROCESSED_LOG_PATH: ./data/processed.json

# Logging Settings
LOG_LEVEL: INFO
LOG_FILE: ./logs/bot.log

# User Access Control
ALLOWED_USER_IDS: ""
```

### 2. .env файл (credentials)
```bash
# Telegram Bot Token (REQUIRED)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Override YAML settings if needed
# MESSAGE_GROUP_TIMEOUT=60
# LOG_LEVEL=DEBUG
```

### 3. Переменные окружения (наивысший приоритет)
```bash
# Export environment variables to override everything
export MESSAGE_GROUP_TIMEOUT=120
export LOG_LEVEL=DEBUG

# Run the application
python main.py
```

## Примеры переопределения

### Пример 1: Базовая конфигурация
```yaml
# config.yaml
MESSAGE_GROUP_TIMEOUT: 30
LOG_LEVEL: INFO
```

Результат: `MESSAGE_GROUP_TIMEOUT=30`, `LOG_LEVEL=INFO`

### Пример 2: Переопределение через .env
```yaml
# config.yaml
MESSAGE_GROUP_TIMEOUT: 30
LOG_LEVEL: INFO
```

```bash
# .env
MESSAGE_GROUP_TIMEOUT=60
```

Результат: `MESSAGE_GROUP_TIMEOUT=60` (из .env), `LOG_LEVEL=INFO` (из YAML)

### Пример 3: Переопределение через ENV
```yaml
# config.yaml
MESSAGE_GROUP_TIMEOUT: 30
LOG_LEVEL: INFO
```

```bash
# .env
MESSAGE_GROUP_TIMEOUT=60
```

```bash
# Environment variable
export LOG_LEVEL=DEBUG
```

Результат: 
- `MESSAGE_GROUP_TIMEOUT=60` (из .env, ENV не установлен)
- `LOG_LEVEL=DEBUG` (из ENV, переопределяет YAML и .env)

## Программное использование

```python
from config import settings

# Все настройки доступны как атрибуты
print(f"KB Path: {settings.KB_PATH}")
print(f"Timeout: {settings.MESSAGE_GROUP_TIMEOUT}")
print(f"Log Level: {settings.LOG_LEVEL}")

# Валидация настроек
errors = settings.validate()
if errors:
    print(f"Configuration errors: {errors}")
```

## Поддерживаемые настройки

### Telegram Bot
- `TELEGRAM_BOT_TOKEN` (string) - токен бота [**только .env или ENV**]
- `ALLOWED_USER_IDS` (string) - список разрешенных user ID через запятую

### Knowledge Base
- `KB_PATH` (Path) - путь к базе знаний
- `KB_GIT_ENABLED` (bool) - включить Git интеграцию
- `KB_GIT_AUTO_PUSH` (bool) - автоматический push
- `KB_GIT_REMOTE` (string) - имя remote
- `KB_GIT_BRANCH` (string) - имя ветки

### Processing
- `MESSAGE_GROUP_TIMEOUT` (int) - таймаут группировки сообщений (секунды)
- `PROCESSED_LOG_PATH` (Path) - путь к логу обработанных сообщений

### Logging
- `LOG_LEVEL` (string) - уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FILE` (Path) - путь к файлу логов

### Agent System (future)
- `OPENAI_API_KEY` (string) - API ключ OpenAI [**только .env или ENV**]
- `ANTHROPIC_API_KEY` (string) - API ключ Anthropic [**только .env или ENV**]

## Миграция с предыдущей версии

Если вы использовали только `.env` файл, ничего менять не нужно - все продолжит работать.

Для использования YAML:
1. Скопируйте `config.example.yaml` в `config.yaml`
2. Перенесите не-чувствительные настройки из `.env` в `config.yaml`
3. Оставьте credentials (токены, ключи) в `.env`

## Best Practices

1. **YAML для базовой конфигурации**
   - Храните в Git
   - Используйте для настроек окружения (dev, staging, prod)

2. **.env для credentials**
   - НЕ храните в Git (добавьте в .gitignore)
   - Используйте для чувствительных данных

3. **ENV для переопределения**
   - Используйте в Docker/Kubernetes
   - Используйте для CI/CD
   - Удобно для временного изменения настроек

## Troubleshooting

### Настройка не применяется
Проверьте порядок приоритета. Возможно, значение переопределено источником с более высоким приоритетом.

```bash
# Проверить, откуда берется значение:
# 1. Проверьте переменную окружения
echo $MESSAGE_GROUP_TIMEOUT

# 2. Проверьте .env файл
cat .env | grep MESSAGE_GROUP_TIMEOUT

# 3. Проверьте config.yaml
cat config.yaml | grep MESSAGE_GROUP_TIMEOUT
```

### YAML файл не читается
Убедитесь, что:
1. Файл называется `config.yaml` (без опечаток)
2. Файл находится в корне проекта
3. YAML синтаксис корректен
4. Права на чтение файла установлены

### Ошибка валидации
Запустите:
```python
from config import settings
errors = settings.validate()
print(errors)
```

## Техническая реализация

Используется `pydantic-settings` с кастомным `YamlConfigSettingsSource`:

```python
@classmethod
def settings_customise_sources(cls, ...):
    return (
        env_settings,       # Highest priority
        cli_settings,       # Future
        dotenv_settings,    # .env file
        yaml_settings,      # Lowest priority
    )
```

Первый источник, который находит значение для поля, определяет финальное значение.
