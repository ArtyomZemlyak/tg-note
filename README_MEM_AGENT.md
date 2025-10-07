# Интеграция mem-agent в tg-note

## Что сделано

Успешно мигрирована реализация mem-agent из https://github.com/firstbatchxyz/mem-agent-mcp в наш репозиторий со следующими улучшениями:

### 1. Система регистрации MCP серверов

Создана универсальная система для управления MCP серверами через JSON конфигурации:

- **Автоматическое обнаружение** серверов из `data/mcp_servers/*.json`
- **Простое управление** (включение/выключение серверов)
- **Поддержка пользовательских серверов** - просто добавь JSON файл
- **Динамическая конфигурация** без изменения кода

### 2. Локальный mem-agent

- **Без OpenAI API** - использует локальные LLM модели
- **Python-based** - не нужен Node.js/npm
- **Автоматическая загрузка моделей** через HuggingFace CLI
- **Множество бэкендов**:
  - vLLM для Linux с GPU (лучшая производительность)
  - MLX для macOS с Apple Silicon
  - Transformers для CPU (работает везде)

### 3. Память per-user в knowledge base

Память хранится **для каждого пользователя** в его базе знаний:

```
knowledge_bases/
└── {user_kb_name}/   # Каждый пользователь имеет свою KB
    ├── .mcp_servers/ # MCP серверы пользователя
    │   └── mem-agent.json
    ├── memory/       # Память пользователя (настраивается через postfix)
    │   ├── user.md   # Информация о пользователе
    │   └── entities/ # Файлы сущностей
    └── topics/       # Заметки пользователя
```

**Важно:**
- Путь к памяти: `{kb_path}/{MEM_AGENT_MEMORY_POSTFIX}`
- MCP серверы: `{kb_path}/{MCP_SERVERS_POSTFIX}`
- Каждый пользователь изолирован

## Быстрый старт

### 1. Установка

```bash
# Установить mem-agent
python scripts/install_mem_agent.py

# Это автоматически:
# - Установит зависимости
# - Скачает модель с HuggingFace
# - Создаст структуру памяти
# - Зарегистрирует MCP сервер
```

### 2. Настройка

Включить в `config.yaml`:

```yaml
# Включить MCP
AGENT_ENABLE_MCP: true
AGENT_ENABLE_MCP_MEMORY: true

# Настройки mem-agent
MEM_AGENT_MODEL: driaforall/mem-agent
MEM_AGENT_MODEL_PRECISION: 4bit  # 4bit, 8bit, или fp16
MEM_AGENT_BACKEND: auto          # auto, vllm, mlx, или transformers
MEM_AGENT_MEMORY_POSTFIX: memory # Postfix в рамках KB (kb_path/memory)

# Настройки MCP
MCP_SERVERS_POSTFIX: .mcp_servers # Per-user MCP серверы (kb_path/.mcp_servers)
```

### 3. Установка зависимостей

```bash
# Базовые зависимости MCP
pip install ".[mcp]"

# Зависимости mem-agent
pip install ".[mem-agent]"

# Бэкенд для вашей платформы:
# macOS:
pip install mlx mlx-lm

# Linux с GPU:
pip install vllm
```

### 4. Проверка

```bash
# Проверить, что mem-agent зарегистрирован
cat data/mcp_servers/mem-agent.json

# Проверить структуру памяти
ls -la knowledge_bases/{user_kb}/memory/

# Проверить загрузку модели
huggingface-cli scan-cache | grep mem-agent
```

## Выбор модели

### Доступные модели

- `driaforall/mem-agent` - основная модель (рекомендуется)
- Автоматически доступны квантизованные версии (4bit, 8bit)

### Смена модели

1. Обновить конфигурацию:
   ```yaml
   MEM_AGENT_MODEL: driaforall/mem-agent
   MEM_AGENT_MODEL_PRECISION: 8bit  # или 4bit, fp16
   ```

2. Модель скачается автоматически при первом запуске
   
   Или скачать вручную:
   ```bash
   huggingface-cli download driaforall/mem-agent
   ```

## Добавление своих MCP серверов

### Способ 1: JSON файл

Создать файл в `data/mcp_servers/`:

```json
{
  "name": "my-server",
  "description": "Мой кастомный MCP сервер",
  "command": "python",
  "args": ["-m", "my_package.server"],
  "env": {
    "MY_VAR": "value"
  },
  "enabled": true
}
```

### Способ 2: Программно

```python
from src.mcp_registry import MCPServersManager

manager = MCPServersManager()
manager.initialize()

# Добавить из JSON строки
json_config = '''
{
  "name": "custom-server",
  "description": "Custom MCP server",
  "command": "node",
  "args": ["server.js"],
  "enabled": true
}
'''

manager.add_server_from_json(json_config)
```

### Способ 3: Через бота (в планах)

В будущем можно будет добавлять серверы через Telegram бота:

```
/mcp add my-server
[загрузить JSON файл]
```

## Архитектура

### Общая схема

```
Agent (с включенным MCP)
  ↓
MCP Registry Client (автообнаружение серверов)
  ↓
MCP Server Registry (чтение JSON конфигов)
  ↓
Подключение к включенным серверам:
  ├── mem-agent (локальная память)
  ├── другие MCP серверы
  └── ...
```

### Поток данных

```
1. Пользователь → Telegram Bot → Agent
2. Agent → MCP Registry Client → Обнаружить серверы
3. MCP Registry Client → Подключиться к mem-agent
4. Agent → mem-agent → Сохранить/найти память
5. mem-agent → knowledge_bases/{user_kb}/memory/ → Работа с файлами (per-user)
6. Agent → Telegram Bot → Пользователь
```

## Структура памяти

### user.md - основная информация о пользователе

```markdown
# User Information
- user_name: Иван Иванов
- user_age: 30
- user_location: Москва

## User Relationships
- работодатель: [[entities/company_name.md]]
- друг: [[entities/person_name.md]]

## Preferences
- любимый_язык_программирования: Python
- любимый_фреймворк: FastAPI
```

### entities/ - информация о сущностях

```markdown
# Название компании
- entity_type: Компания
- отрасль: IT
- location: Москва

## Employees
- ceo: [[entities/ceo_name.md]]
```

## Управление серверами

```python
from src.mcp_registry import MCPServersManager

manager = MCPServersManager()
manager.initialize()

# Список всех серверов
for server in manager.get_all_servers():
    status = "включен" if server.enabled else "выключен"
    print(f"{server.name}: {status}")

# Включить/выключить сервер
manager.enable_server("mem-agent")
manager.disable_server("mem-agent")

# Статистика
summary = manager.get_servers_summary()
print(f"Всего: {summary['total']}, Включено: {summary['enabled']}")
```

## Что убрано из оригинальной реализации

### ❌ OpenAI API настройки

**Проверено**: В оригинальном репозитории OpenAI API использовался только для fallback через OpenRouter. В нашей реализации:

- Используются **только локальные модели** (vLLM/MLX/Transformers)
- **Не требуется** OpenAI API key
- **Не требуется** настройка OpenRouter

### ✅ Что оставлено и улучшено

- ✅ Вся логика агента памяти
- ✅ Sandbox для безопасного выполнения кода
- ✅ Система инструментов (tools) для работы с файлами
- ✅ Структура памяти (user.md + entities/)
- ✅ Улучшена: добавлена автоматическая загрузка моделей
- ✅ Улучшена: гибкий выбор бэкенда
- ✅ Улучшена: интеграция через MCP registry

## Настройки по умолчанию

```yaml
# Модель
MEM_AGENT_MODEL: driaforall/mem-agent
MEM_AGENT_MODEL_PRECISION: 4bit

# Бэкенд (авто-выбор)
MEM_AGENT_BACKEND: auto

# Пути
MEM_AGENT_MEMORY_POSTFIX: memory  # Postfix в KB
MCP_SERVERS_POSTFIX: .mcp_servers  # Per-user MCP серверы

# Лимиты
MEM_AGENT_MAX_TOOL_TURNS: 20
MEM_AGENT_FILE_SIZE_LIMIT: 1048576      # 1MB на файл
MEM_AGENT_DIR_SIZE_LIMIT: 10485760      # 10MB на директорию
MEM_AGENT_MEMORY_SIZE_LIMIT: 104857600  # 100MB всего
```

## Продвинутые настройки

### vLLM (Linux с GPU)

```yaml
MEM_AGENT_BACKEND: vllm
MEM_AGENT_VLLM_HOST: 127.0.0.1
MEM_AGENT_VLLM_PORT: 8001
MEM_AGENT_MODEL_PRECISION: fp16  # Лучшее качество
```

### MLX (macOS)

```yaml
MEM_AGENT_BACKEND: mlx
MEM_AGENT_MODEL_PRECISION: 4bit  # Баланс скорость/качество
```

### Увеличить лимиты памяти

```yaml
MEM_AGENT_FILE_SIZE_LIMIT: 5242880      # 5MB на файл
MEM_AGENT_DIR_SIZE_LIMIT: 52428800      # 50MB на директорию
MEM_AGENT_MEMORY_SIZE_LIMIT: 524288000  # 500MB всего
```

## Troubleshooting

### Модель не скачивается

```bash
# Проверить интернет
ping huggingface.co

# Скачать вручную
huggingface-cli download driaforall/mem-agent

# Использовать зеркало (если в Китае)
export HF_ENDPOINT=https://hf-mirror.com
```

### Ошибка подключения к MCP серверу

```bash
# Проверить, что сервер зарегистрирован
cat data/mcp_servers/mem-agent.json

# Проверить, что сервер включен
python -c "
from src.mcp_registry import MCPServersManager
manager = MCPServersManager()
manager.initialize()
server = manager.get_server('mem-agent')
print(f'Enabled: {server.enabled}')
"

# Запустить сервер вручную для отладки
python -m src.mem_agent.server
```

### Проблемы с бэкендом

```bash
# vLLM
python -c "import torch; print(torch.cuda.is_available())"
pip install vllm --no-cache-dir

# MLX (только macOS ARM)
uname -m  # Должно быть arm64
pip install mlx mlx-lm

# Fallback на CPU
export MEM_AGENT_BACKEND=transformers
```

## Документация

Полная документация доступна в:

- [MCP Server Registry](docs_site/agents/mcp-server-registry.md) - Система регистрации MCP серверов
- [Memory Agent Setup](docs_site/agents/mem-agent-setup.md) - Подробная настройка mem-agent
- [MCP Tools](docs_site/agents/mcp-tools.md) - Использование MCP инструментов

## Roadmap

### В планах

- [ ] Команды бота для управления MCP серверами
- [ ] Загрузка пользовательских MCP серверов через бота
- [ ] UI для визуализации памяти
- [ ] Мульти-пользовательская память
- [ ] Синхронизация памяти с облаком

## Заключение

Миграция завершена успешно! Теперь у вас есть:

✅ **Полностью локальный mem-agent** без зависимости от внешних API  
✅ **Гибкая система MCP серверов** с простым добавлением новых  
✅ **Автоматическое управление моделями** через HuggingFace CLI  
✅ **Память per-user в knowledge base** в `{kb_path}/{MEM_AGENT_MEMORY_POSTFIX}/`
✅ **MCP серверы per-user** в `{kb_path}/{MCP_SERVERS_POSTFIX}/`  
✅ **Поддержка всех агентов** через общую MCP прослойку  
✅ **Подробная документация** на русском и английском  

Система готова к использованию! 🚀