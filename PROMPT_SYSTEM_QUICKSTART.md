# Prompt System Quick Start

## TL;DR

Промпты агентов теперь в YAML файлах с версионностью. Старый код работает без изменений!

## Быстрый старт

### Использование (новый способ)

```python
from config.prompt_loader import PromptLoader

loader = PromptLoader()
instruction = loader.get_instruction("qwen_code_cli_agent")
```

### Использование (старый способ - всё ещё работает!)

```python
from config.agent_prompts import QWEN_CODE_CLI_AGENT_INSTRUCTION
# Работает как раньше!
```

## Структура файлов

```
config/
├── prompts/
│   ├── v1/
│   │   ├── config.yaml              # Конфигурация (категории, стоп-слова)
│   │   ├── qwen_code_agent.yaml     # Английский промпт
│   │   ├── qwen_code_cli_agent.yaml # Русский промпт
│   │   ├── kb_query.yaml            # Промпт для запросов к БЗ
│   │   └── stub_agent.yaml          # Тестовый промпт
│   └── v2/                          # Будущие версии
├── prompt_loader.py                 # Класс загрузчика
└── agent_prompts.py                 # Обратная совместимость
```

## Основные операции

### Получить промпт

```python
loader = PromptLoader()
instruction = loader.get_instruction("qwen_code_cli_agent")
```

### Получить шаблон

```python
template = loader.get_template("qwen_code_agent", "content_processing")
```

### Форматировать шаблон

```python
prompt = loader.format_template(
    "qwen_code_agent",
    "content_processing",
    instruction="Инструкция",
    text="Текст",
    urls_section=""
)
```

### Получить конфигурацию

```python
# Категории
categories = loader.get_category_keywords()

# Настройки markdown
max_title = loader.get_config("markdown.max_title_length")

# Стоп-слова
stop_words = loader.get_stop_words()
```

### Работа с версиями

```python
# Загрузить конкретную версию
loader_v1 = PromptLoader(version="v1")

# Проверить версию
print(loader_v1.version)

# Список версий
versions = loader.list_versions()
```

### Горячая перезагрузка

```python
# Изменить YAML файл
# Затем:
loader.reload()
```

## Обновление промптов

### Обновить существующий промпт

1. Отредактировать файл в `config/prompts/v1/`
2. В development: `loader.reload()`
3. В production: перезапустить приложение

### Создать новую версию

```bash
# 1. Скопировать v1 в v2
cp -r config/prompts/v1 config/prompts/v2

# 2. Обновить версии в YAML файлах
# version: "2.0.0"

# 3. Внести изменения

# 4. Использовать
loader = PromptLoader(version="v2")
```

## Формат YAML

```yaml
version: "1.0.0"
name: "agent_name"
description: "Description"
language: "ru"
created_at: "2025-10-07"

instruction: |
  Инструкция агента...

templates:
  template_name: |
    Шаблон с {переменными}
```

## Полезные команды

```python
# Список агентов
loader.list_agents()
# ['kb_query', 'qwen_code_agent', 'qwen_code_cli_agent', 'stub_agent']

# Список версий
loader.list_versions()
# ['v1', 'v2']

# Метаданные промпта
metadata = loader.get_metadata("qwen_code_cli_agent")
# {'version': '1.0.0', 'language': 'ru', ...}

# Перезагрузка
loader.reload()
```

## Документация

- **Полное руководство**: `PROMPT_REFACTORING_GUIDE.md`
- **Резюме изменений**: `PROMPT_REFACTORING_SUMMARY.md`
- **Примеры кода**: `examples/prompt_loader_example.py`
- **Тесты**: `tests/test_prompt_loader.py`
- **Структура промптов**: `config/prompts/README.md`

## FAQ

**Q: Нужно ли переписывать существующий код?**  
A: Нет! Старый код работает без изменений через `config/agent_prompts.py`.

**Q: Как обновить промпт в production?**  
A: Отредактировать YAML файл и перезапустить приложение.

**Q: Можно ли использовать несколько версий одновременно?**  
A: Да! Создайте несколько экземпляров `PromptLoader` с разными версиями.

**Q: Как откатиться к предыдущей версии?**  
A: `loader = PromptLoader(version="v1")` или откатить изменения в git.

**Q: Поддерживается ли горячая перезагрузка в production?**  
A: Да, вызовите `loader.reload()`, но рекомендуется делать это аккуратно.

## Примеры использования

### В агенте

```python
class MyAgent:
    def __init__(self, prompt_version="v1"):
        self.loader = PromptLoader(version=prompt_version)
        self.instruction = self.loader.get_instruction("qwen_code_agent")
    
    def process(self, content):
        prompt = self.loader.format_template(
            "qwen_code_agent",
            "content_processing",
            instruction=self.instruction,
            text=content["text"],
            urls_section=""
        )
        return prompt
```

### A/B тестирование

```python
# Тестировать разные версии промптов
loader_a = PromptLoader(version="v1")
loader_b = PromptLoader(version="v2")

instruction_a = loader_a.get_instruction("qwen_code_agent")
instruction_b = loader_b.get_instruction("qwen_code_agent")

# Сравнить результаты
```

### Обратная совместимость

```python
# Все эти импорты работают!
from config.agent_prompts import (
    QWEN_CODE_CLI_AGENT_INSTRUCTION,
    CATEGORY_KEYWORDS,
    MAX_TITLE_LENGTH,
    STOP_WORDS
)
```

## Запуск примеров и тестов

```bash
# Примеры
python examples/prompt_loader_example.py

# Тесты
pytest tests/test_prompt_loader.py -v
```

## Поддержка

При возникновении проблем:
1. Проверьте документацию в `PROMPT_REFACTORING_GUIDE.md`
2. Посмотрите примеры в `examples/prompt_loader_example.py`
3. Запустите тесты: `pytest tests/test_prompt_loader.py`
