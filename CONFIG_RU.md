# Конфигурация приложения

## Быстрый старт

### 1. Скопируйте файл примера
```bash
cp config.example.yaml config.yaml
```

### 2. Создайте .env с токеном
```bash
echo "TELEGRAM_BOT_TOKEN=ваш_токен_здесь" > .env
```

### 3. Запустите
```bash
python main.py
```

## Порядок приоритета настроек

```
ENV переменные > CLI аргументы > .env файл > config.yaml
```

**Пример:**
- В `config.yaml`: `LOG_LEVEL: INFO`
- В `.env`: `LOG_LEVEL=WARNING`
- В терминале: `export LOG_LEVEL=DEBUG`
- **Результат**: `LOG_LEVEL=DEBUG` (ENV побеждает)

## Что где хранить

### 📄 config.yaml - основные настройки
```yaml
KB_PATH: ./knowledge_base
KB_GIT_ENABLED: true
MESSAGE_GROUP_TIMEOUT: 30
LOG_LEVEL: INFO
```

**Хранить в Git:** ❌ НЕТ (добавлен в .gitignore)  
**Что хранить:** Пути, таймауты, уровни логов, Git настройки

### 🔐 .env - секретные данные
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Хранить в Git:** ❌ НЕТ (добавлен в .gitignore)  
**Что хранить:** Токены, API ключи, пароли

### 🌍 ENV переменные - переопределение
```bash
export LOG_LEVEL=DEBUG
export MESSAGE_GROUP_TIMEOUT=120
python main.py
```

**Когда использовать:** Docker, Kubernetes, CI/CD, временные изменения

## Примеры

### Пример 1: Разработка локально
```yaml
# config.yaml
LOG_LEVEL: DEBUG
MESSAGE_GROUP_TIMEOUT: 10
KB_PATH: ./test_kb
```

```bash
# .env
TELEGRAM_BOT_TOKEN=test_token
```

### Пример 2: Production с Docker
```yaml
# config.yaml
LOG_LEVEL: WARNING
MESSAGE_GROUP_TIMEOUT: 30
KB_PATH: /app/knowledge_base
```

```bash
# В Dockerfile или docker-compose.yml
ENV TELEGRAM_BOT_TOKEN=prod_token
ENV LOG_LEVEL=INFO  # Переопределяем YAML
```

### Пример 3: Временное изменение
```bash
# Хочу отладить проблему, включу DEBUG временно
LOG_LEVEL=DEBUG python main.py

# После завершения DEBUG не сохранится в конфиг
```

## Все доступные настройки

### Telegram Bot
| Настройка | Тип | По умолчанию | Где хранить |
|-----------|-----|--------------|-------------|
| `TELEGRAM_BOT_TOKEN` | string | - | **.env** |
| `ALLOWED_USER_IDS` | string | "" | config.yaml |

### Knowledge Base
| Настройка | Тип | По умолчанию | Где хранить |
|-----------|-----|--------------|-------------|
| `KB_PATH` | Path | ./knowledge_base | config.yaml |
| `KB_GIT_ENABLED` | bool | true | config.yaml |
| `KB_GIT_AUTO_PUSH` | bool | true | config.yaml |
| `KB_GIT_REMOTE` | string | origin | config.yaml |
| `KB_GIT_BRANCH` | string | main | config.yaml |

### Processing
| Настройка | Тип | По умолчанию | Где хранить |
|-----------|-----|--------------|-------------|
| `MESSAGE_GROUP_TIMEOUT` | int | 30 | config.yaml |
| `PROCESSED_LOG_PATH` | Path | ./data/processed.json | config.yaml |

### Logging
| Настройка | Тип | По умолчанию | Где хранить |
|-----------|-----|--------------|-------------|
| `LOG_LEVEL` | string | INFO | config.yaml |
| `LOG_FILE` | Path | ./logs/bot.log | config.yaml |

### Agent System (будущее)
| Настройка | Тип | По умолчанию | Где хранить |
|-----------|-----|--------------|-------------|
| `OPENAI_API_KEY` | string | None | **.env** |
| `ANTHROPIC_API_KEY` | string | None | **.env** |

## Проверка конфигурации

```bash
# Показать текущие настройки
python -c "from config import settings; print(settings)"

# Проверить валидацию
python -c "from config import settings; print(settings.validate())"

# Проверить конкретное значение
python -c "from config import settings; print(settings.MESSAGE_GROUP_TIMEOUT)"
```

## Troubleshooting

### ❌ "TELEGRAM_BOT_TOKEN is required"
**Решение:** Добавьте токен в `.env` файл

### ❌ Настройка не применяется
**Решение:** Проверьте порядок приоритета. Возможно переопределено в ENV
```bash
env | grep MESSAGE_GROUP_TIMEOUT  # Проверить ENV
cat .env | grep MESSAGE_GROUP_TIMEOUT  # Проверить .env
cat config.yaml | grep MESSAGE_GROUP_TIMEOUT  # Проверить YAML
```

### ❌ YAML файл не читается
**Решение:** Проверьте синтаксис YAML (отступы, двоеточия)
```bash
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

## Полезные команды

```bash
# Создать config.yaml из примера
cp config.example.yaml config.yaml

# Создать пустой .env
touch .env

# Добавить токен в .env
echo "TELEGRAM_BOT_TOKEN=ваш_токен" >> .env

# Запустить с DEBUG логами
LOG_LEVEL=DEBUG python main.py

# Запустить с кастомным timeout
MESSAGE_GROUP_TIMEOUT=60 python main.py

# Проверить что токен загружен (не показывает полный токен)
python -c "from config import settings; print('Token set:', bool(settings.TELEGRAM_BOT_TOKEN))"
```

## Дополнительная документация

- 📖 [YAML_CONFIGURATION.md](YAML_CONFIGURATION.md) - подробная документация
- 📖 [YAML_MIGRATION_SUMMARY.md](YAML_MIGRATION_SUMMARY.md) - детали миграции
- 📖 [QUICK_START.md](QUICK_START.md) - руководство по быстрому старту
