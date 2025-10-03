# Централизованная Конфигурация

## Обзор

Все промпты для агентов, структура базы знаний и форматы названий документов вынесены в централизованные конфигурационные файлы.

## Структура конфигурации

### 1. Agent Prompts Configuration (`config/agent_prompts.py`)

Централизованная конфигурация для всех промптов и инструкций агентов.

#### Промпты агентов

```python
# QwenCodeAgent - агент с API интеграцией
QWEN_CODE_AGENT_INSTRUCTION = """..."""

# QwenCodeCLIAgent - агент с CLI интеграцией
QWEN_CODE_CLI_AGENT_INSTRUCTION = """..."""

# StubAgent - тестовый агент
STUB_AGENT_INSTRUCTION = """..."""
```

#### Шаблоны промптов

```python
# Основной шаблон для обработки контента
CONTENT_PROCESSING_PROMPT_TEMPLATE = """
{instruction}

# Input Content
## Text Content
{text}

{urls_section}

# Task
...
"""

# Шаблон секции URLs
URLS_SECTION_TEMPLATE = """
## URLs
{url_list}
"""
```

#### Ключевые слова категорий

```python
CATEGORY_KEYWORDS = {
    "ai": ["ai", "artificial intelligence", "machine learning", ...],
    "biology": ["biology", "gene", "dna", "protein", ...],
    "physics": ["physics", "quantum", "particle", ...],
    "tech": ["programming", "code", "software", ...],
    "business": ["business", "market", "economy", ...],
    "science": ["science", "research", "experiment", ...],
}

DEFAULT_CATEGORY = "general"
```

#### Стоп-слова для извлечения ключевых слов

```python
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but",
    "in", "on", "at", "to", "for", "of",
    # ... полный список стоп-слов
}
```

#### Настройки генерации Markdown

```python
# Секции в генерируемом markdown
DEFAULT_MARKDOWN_SECTIONS = [
    "Metadata",
    "Summary", 
    "Content",
    "Links",
    "Additional Context",
    "Keywords",
]

# Максимальные длины
MAX_TITLE_LENGTH = 60
MAX_SUMMARY_LENGTH = 200
MAX_KEYWORD_COUNT = 10
MAX_TAG_COUNT = 5
MIN_KEYWORD_LENGTH = 3
```

#### Настройки безопасности инструментов

```python
# Безопасные git команды (только для чтения)
SAFE_GIT_COMMANDS = [
    "status", "log", "diff", "branch", "remote", "show",
]

# Опасные паттерны shell команд для блокировки
DANGEROUS_SHELL_PATTERNS = [
    "rm -rf", "rm -f", "> /dev", "mkfs", "dd if=",
    ":(){ :|:& };:",  # Fork bomb
    "chmod -R", "chown -R", "sudo", "su -",
    "wget", "curl",
]
```

### 2. Knowledge Base Structure Configuration (`config/kb_structure.py`)

Централизованная конфигурация структуры базы знаний и именования документов.

#### Структура директорий

```python
KB_BASE_STRUCTURE = {
    "topics": {
        "general": {},
        "ai": {
            "machine-learning": {},
            "nlp": {},
            "computer-vision": {},
            "reinforcement-learning": {},
        },
        "tech": {
            "programming": {},
            "web-development": {},
            "devops": {},
            "databases": {},
            "cloud": {},
        },
        "science": {
            "physics": {},
            "biology": {},
            "chemistry": {},
            "mathematics": {},
        },
        "business": {
            "management": {},
            "finance": {},
            "marketing": {},
            "entrepreneurship": {},
        },
    },
}

# Категории по умолчанию
DEFAULT_CATEGORIES = [
    "general", "ai", "tech", "science", 
    "business", "biology", "physics",
]

# Маппинг категорий на подкатегории
CATEGORY_SUBCATEGORIES = {
    "ai": ["machine-learning", "nlp", "computer-vision", ...],
    "tech": ["programming", "web-development", "devops", ...],
    "science": ["physics", "biology", "chemistry", ...],
    "business": ["management", "finance", "marketing", ...],
}

# Префикс пути для всех топиков
TOPICS_PATH_PREFIX = "topics"
```

#### Конфигурация именования документов

```python
# Формат даты в именах файлов (YYYY-MM-DD)
FILENAME_DATE_FORMAT = "%Y-%m-%d"

# Шаблон имени файла: {date}-{slug}.md
FILENAME_TEMPLATE = "{date}-{slug}.md"

# Максимальная длина slug части имени файла
MAX_SLUG_LENGTH = 50

# Символы для удаления из slug
SLUG_REMOVE_CHARS = r'[^\w\s-]'

# Символы для замены дефисом в slug
SLUG_REPLACE_CHARS = r'[-\s]+'

# Имя файла по умолчанию если заголовок не может быть сгенерирован
DEFAULT_FILENAME = "untitled"
```

**Примеры имен файлов:**
- `2025-10-03-introduction-to-machine-learning.md`
- `2025-10-03-python-best-practices.md`
- `2025-10-03-quantum-physics-basics.md`

#### Конфигурация frontmatter

```python
# Формат frontmatter (YAML)
FRONTMATTER_FORMAT = "yaml"

# Обязательные поля frontmatter
REQUIRED_FRONTMATTER_FIELDS = [
    "title",
    "category",
    "created_at",
]

# Опциональные поля frontmatter
OPTIONAL_FRONTMATTER_FIELDS = [
    "subcategory",
    "tags",
    "processed_at",
    "agent",
    "version",
]

# Шаблон frontmatter
FRONTMATTER_TEMPLATE = """---
title: {title}
category: {category}
{subcategory_line}
{tags_line}
created_at: {created_at}
{extra_fields}
---"""
```

**Пример frontmatter:**
```yaml
---
title: Introduction to Machine Learning
category: ai
subcategory: machine-learning
tags: [python, tensorflow, neural-networks]
created_at: 2025-10-03T12:00:00
---
```

#### Управление индексом

```python
# Имя файла индекса
INDEX_FILENAME = "index.md"

# Заголовок индекса
INDEX_HEADER = "# Knowledge Base Index\n\n"

# Шаблон записи в индексе
INDEX_ENTRY_TEMPLATE = "- [{title}]({relative_path}) - {date} - `{category}`\n"
```

#### Контент начальных файлов

```python
# README.md - полное описание структуры KB
README_CONTENT = """# Knowledge Base

This is an automated knowledge base created by tg-note.

## Structure
...
"""

# .gitignore - паттерны игнорирования
GITIGNORE_CONTENT = """# OS files
.DS_Store
Thumbs.db
...
"""
```

#### Вспомогательные функции

```python
def generate_filename(title: str, date: Optional[datetime] = None) -> str:
    """Генерирует имя файла из заголовка и даты"""
    
def slugify(text: str) -> str:
    """Преобразует текст в URL-friendly slug"""
    
def get_relative_path(
    category: str,
    subcategory: Optional[str] = None,
    custom_path: Optional[str] = None
) -> str:
    """Получает относительный путь для документа"""
    
def create_frontmatter(
    title: str,
    category: str,
    subcategory: Optional[str] = None,
    tags: Optional[List[str]] = None,
    extra_fields: Optional[dict] = None
) -> str:
    """Создает YAML frontmatter для документа"""
    
def get_valid_categories() -> List[str]:
    """Получает список валидных категорий"""
    
def get_valid_subcategories(category: str) -> List[str]:
    """Получает список валидных подкатегорий для категории"""
    
def is_valid_category(category: str) -> bool:
    """Проверяет валидность категории"""
    
def is_valid_subcategory(category: str, subcategory: str) -> bool:
    """Проверяет валидность подкатегории для категории"""
```

## Использование в коде

### Импорт промптов агентов

```python
from config.agent_prompts import (
    QWEN_CODE_AGENT_INSTRUCTION,
    QWEN_CODE_CLI_AGENT_INSTRUCTION,
    CATEGORY_KEYWORDS,
    DEFAULT_CATEGORY,
    STOP_WORDS,
    SAFE_GIT_COMMANDS,
    DANGEROUS_SHELL_PATTERNS,
    MAX_TITLE_LENGTH,
    MAX_SUMMARY_LENGTH,
)

# Использование в агенте
class QwenCodeAgent(BaseAgent):
    DEFAULT_INSTRUCTION = QWEN_CODE_AGENT_INSTRUCTION
    
    def _detect_category(self, text: str) -> str:
        categories = CATEGORY_KEYWORDS
        # ...
        return DEFAULT_CATEGORY
```

### Импорт структуры KB

```python
from config.kb_structure import (
    generate_filename,
    create_frontmatter,
    get_relative_path,
    KB_BASE_STRUCTURE,
    README_CONTENT,
    FILENAME_DATE_FORMAT,
)

# Использование в менеджере KB
class KnowledgeBaseManager:
    def create_article(self, content, title, kb_structure, metadata):
        # Генерация имени файла
        filename = generate_filename(title)
        
        # Создание frontmatter
        frontmatter = create_frontmatter(
            title=title,
            category=kb_structure.category,
            subcategory=kb_structure.subcategory,
            tags=kb_structure.tags,
            extra_fields=metadata
        )
```

## Преимущества централизации

### 1. Единая точка управления
- Все промпты и настройки в одном месте
- Легко находить и изменять конфигурацию
- Нет дублирования кода

### 2. Консистентность
- Одинаковые настройки для всех агентов
- Единый формат документов
- Согласованная структура KB

### 3. Гибкость
- Легко добавлять новые категории
- Простое изменение промптов
- Быстрая настройка форматов

### 4. Тестирование
- Легко тестировать с разными конфигурациями
- Можно создавать тестовые наборы настроек
- Изоляция конфигурации от логики

### 5. Документация
- Конфигурация сама по себе является документацией
- Понятные имена и комментарии
- Примеры использования в коде

## Миграция существующего кода

Все существующие компоненты обновлены для использования централизованной конфигурации:

### Обновленные файлы
1. ✅ `src/agents/qwen_code_agent.py` - использует `config/agent_prompts.py`
2. ✅ `src/agents/qwen_code_cli_agent.py` - использует `config/agent_prompts.py`
3. ✅ `src/knowledge_base/manager.py` - использует `config/kb_structure.py`
4. ✅ `src/knowledge_base/repository.py` - использует `config/kb_structure.py`

### Удаленный дублированный код
- Промпты агентов больше не хардкодятся в классах
- Функции `_slugify()` и `_create_frontmatter()` заменены на функции из config
- Ключевые слова категорий и стоп-слова вынесены в config
- Настройки безопасности инструментов вынесены в config

## Расширение конфигурации

### Добавление новой категории

```python
# В config/kb_structure.py

# 1. Добавить в структуру
KB_BASE_STRUCTURE = {
    "topics": {
        # ...
        "new_category": {
            "subcategory1": {},
            "subcategory2": {},
        },
    },
}

# 2. Добавить в список категорий
DEFAULT_CATEGORIES = [
    # ...
    "new_category",
]

# 3. Добавить подкатегории
CATEGORY_SUBCATEGORIES = {
    # ...
    "new_category": ["subcategory1", "subcategory2"],
}
```

### Добавление ключевых слов категории

```python
# В config/agent_prompts.py

CATEGORY_KEYWORDS = {
    # ...
    "new_category": [
        "keyword1", "keyword2", "keyword3",
    ],
}
```

### Изменение промпта агента

```python
# В config/agent_prompts.py

QWEN_CODE_AGENT_INSTRUCTION = """
Новая инструкция для агента...
"""
```

## Заключение

Централизованная конфигурация обеспечивает:
- **Простоту управления** - все настройки в двух файлах
- **Гибкость** - легко изменять и расширять
- **Консистентность** - единые стандарты везде
- **Поддерживаемость** - понятная структура и документация
- **Тестируемость** - изолированная конфигурация

Все промпты, структура KB и форматы документов теперь полностью централизованы!
