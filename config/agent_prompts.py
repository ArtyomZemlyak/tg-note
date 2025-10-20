"""
Agent Prompts Configuration (Refactored)
Centralized configuration for all agent prompts and instructions.

Prompts are stored as versioned files under `config/prompts/` and loaded via
`src.prompts.registry.prompt_registry`. This module keeps non-prompt constants
and exposes helper accessors plus backward-compatible constants for existing imports.
"""

from __future__ import annotations

from src.prompts.registry import prompt_registry

# ═══════════════════════════════════════════════════════════════════════════════
# Agent Default Instructions (via registry)
# ═══════════════════════════════════════════════════════════════════════════════


def get_qwen_code_agent_instruction(locale: str = "en", version: str | None = None) -> str:
    return prompt_registry.get("autonomous_agent.instruction", locale=locale, version=version)


def get_qwen_code_cli_instruction(locale: str = "ru", version: str | None = None) -> str:
    return prompt_registry.get("qwen_code_cli.instruction", locale=locale, version=version)


STUB_AGENT_INSTRUCTION = (
    "You are a test agent for development purposes.\n"
    "You simulate agent behavior without calling external services.\n"
)

# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Templates for Content Processing (via registry)
# ═══════════════════════════════════════════════════════════════════════════════


def get_content_processing_template(locale: str = "ru", version: str | None = None) -> str:
    return prompt_registry.get("content_processing.template", locale=locale, version=version)


def get_urls_section_template(locale: str = "ru", version: str | None = None) -> str:
    return prompt_registry.get("content_processing.urls_section", locale=locale, version=version)


def get_ask_mode_instruction(locale: str = "ru", version: str | None = None) -> str:
    return prompt_registry.get("ask_mode.instruction", locale=locale, version=version)


def get_kb_query_template(locale: str = "ru", version: str | None = None) -> str:
    return prompt_registry.get("kb_query.template", locale=locale, version=version)


def get_note_mode_instruction(locale: str = "ru", version: str | None = None) -> str:
    return prompt_registry.get("note_mode.instruction", locale=locale, version=version)


# Backward-compatible constants (deprecated): resolve at import time
QWEN_CODE_AGENT_INSTRUCTION = get_qwen_code_agent_instruction("en")
QWEN_CODE_CLI_AGENT_INSTRUCTION = get_qwen_code_cli_instruction("ru")
CONTENT_PROCESSING_PROMPT_TEMPLATE = get_content_processing_template("ru")
URLS_SECTION_TEMPLATE = get_urls_section_template("ru")
ASK_MODE_AGENT_INSTRUCTION = get_ask_mode_instruction("ru")
KB_QUERY_PROMPT_TEMPLATE = get_kb_query_template("ru")

# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mode Instruction (kept inline; single authoritative definition)
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_MODE_INSTRUCTION = """Ты автономный агент для работы с Базой Знаний.
Твой основной язык - РУССКИЙ!

🔴 КРИТИЧНО: ВСЕГДА сначала ищи существующую информацию в базе знаний!

Ты можешь выполнять ЛЮБЫЕ задачи с базой знаний:
- Отвечать на вопросы пользователя
- Добавлять новую информацию
- Редактировать существующие заметки
- Переструктурировать базу знаний
- Создавать новые файлы и папки
- Удалять или перемещать файлы
- Искать информацию в интернете и добавлять ее
- Анализировать и улучшать структуру базы знаний

## Твои возможности:

### Поиск существующей информации (ОБЯЗАТЕЛЬНО ПЕРВЫМ ДЕЛОМ):
- kb_search_content - поиск по содержимому файлов (ОСНОВНОЙ инструмент)
- kb_search_files - поиск файлов по названию и шаблону
- kb_list_directory - просмотр структуры папок
- kb_read_file - чтение конкретных файлов

### Дополнительные инструменты поиска:
- Просматривай структуру базы знаний (ls, find, glob)
- Читай содержимое файлов (read)
- Ищи информацию по ключевым словам (grep, rg)

### Создание и редактирование:
- Создавай файлы (file_create)
- Редактируй файлы (file_edit)
- Удаляй файлы (file_delete)
- Перемещай файлы (file_move)
- Создавай папки (folder_create)
- Удаляй папки (folder_delete)
- Перемещай папки (folder_move)

### Дополнительные инструменты:
- Ищи дополнительную информацию в интернете (web_search)
- Анализируй контент (analyze_content)
- Выполняй git команды (git_command)

## Процесс работы:

1. **ОБЯЗАТЕЛЬНЫЙ ПОИСК СУЩЕСТВУЮЩЕЙ ИНФОРМАЦИИ**: 
   - Используй kb_search_content с разными поисковыми терминами
   - Используй kb_search_files для поиска файлов по названию
   - Изучи структуру с помощью kb_list_directory
   - Прочитай найденные файлы с помощью kb_read_file
   - Определи, есть ли уже информация по этому вопросу
2. **ТЩАТЕЛЬНЫЙ АНАЛИЗ И СРАВНЕНИЕ**:
   - Сравни новую информацию с существующей
   - Оцени полноту и качество существующей информации
   - Определи, что можно дополнить или улучшить
   - Выяви пробелы и возможности для улучшения
3. **ИНТЕЛЛЕКТУАЛЬНОЕ ПРИНЯТИЕ РЕШЕНИЯ**:
   - Если информации нет - создай новую
   - Если информация неполная - дополни существующую более полной информацией
   - Если информация полная - добавь ссылки или создай перекрестные ссылки
   - Если новая информация лучше - замени существующую
4. **ВЫПОЛНЕНИЕ ЗАДАЧИ**: Используй нужные инструменты
5. **ПРОВЕРКА РЕЗУЛЬТАТА**: Убедись что задача выполнена качественно
6. **СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЮ**: Опиши что ты сделал

## Важные правила:

- ЯЗЫК: РУССКИЙ для всех файлов и ответов!
- Работай автономно, не задавай вопросов
- Используй ТОЛЬКО относительные пути от корня базы знаний
- index.md и README.md в корне не изменяй (если не попросили специально)
- Будь thorough и внимательным
- Если что-то непонятно - используй здравый смысл

## Формат ответа:

В конце своей работы ОБЯЗАТЕЛЬНО верни результат в таком формате:

```agent-result
{
  "summary": "Краткое описание выполненной работы",
  "answer": "ОТВЕТ пользователю (если это был вопрос) на РУССКОМ языке",
  "files_created": ["путь/к/файлу1.md"],
  "files_edited": ["путь/к/файлу2.md"],
  "files_deleted": ["путь/к/файлу3.md"],
  "folders_created": ["путь/к/папке"],
  "metadata": {
    "task_type": "question|note|restructure|other",
    "topics": ["тема1", "тема2"],
    "sources": ["источник1", "источник2"]
  }
}
```

Поле "answer" обязательно заполняй если пользователь задал вопрос!

НАЧИНАЙ РАБОТУ!
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Category Detection Keywords
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_KEYWORDS = {
    "ai": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "neural network",
        "deep learning",
        "llm",
        "gpt",
        "transformer",
        "model",
        "training",
        "inference",
        "nlp",
        "natural language",
        "computer vision",
        "reinforcement learning",
    ],
    "biology": [
        "biology",
        "gene",
        "dna",
        "protein",
        "cell",
        "organism",
        "evolution",
        "genetics",
        "molecular",
        "enzyme",
        "chromosome",
        "rna",
        "mutation",
        "species",
        "ecology",
    ],
    "physics": [
        "physics",
        "quantum",
        "particle",
        "relativity",
        "energy",
        "force",
        "matter",
        "mechanics",
        "thermodynamics",
        "electromagnetic",
        "atom",
        "photon",
        "wave",
        "field",
    ],
    "tech": [
        "programming",
        "code",
        "software",
        "development",
        "python",
        "javascript",
        "api",
        "database",
        "algorithm",
        "framework",
        "library",
        "backend",
        "frontend",
        "devops",
        "cloud",
    ],
    "business": [
        "business",
        "market",
        "economy",
        "finance",
        "investment",
        "strategy",
        "management",
        "startup",
        "revenue",
        "profit",
        "customer",
        "sales",
        "marketing",
        "entrepreneur",
    ],
    "science": [
        "science",
        "research",
        "experiment",
        "study",
        "analysis",
        "hypothesis",
        "theory",
        "method",
        "data",
        "observation",
        "measurement",
        "discovery",
        "phenomenon",
    ],
}

DEFAULT_CATEGORY = "general"

# ═══════════════════════════════════════════════════════════════════════════════
# Stop Words for Keyword Extraction
# ═══════════════════════════════════════════════════════════════════════════════

STOP_WORDS = {
    # Articles
    "the",
    "a",
    "an",
    # Conjunctions
    "and",
    "or",
    "but",
    "nor",
    "so",
    "yet",
    # Prepositions
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "into",
    "about",
    "against",
    "between",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "under",
    "over",
    # Pronouns
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "them",
    "their",
    "this",
    "that",
    "these",
    "those",
    "who",
    "what",
    "which",
    "where",
    "when",
    "why",
    "how",
    # Verbs
    "is",
    "am",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "having",
    "do",
    "does",
    "did",
    "doing",
    "will",
    "would",
    "should",
    "could",
    "can",
    "may",
    "might",
    "must",
    "shall",
    # Other common words
    "not",
    "no",
    "yes",
    "all",
    "any",
    "some",
    "many",
    "much",
    "more",
    "most",
    "less",
    "least",
    "few",
    "several",
    "each",
    "every",
    "both",
    "either",
    "neither",
    "other",
    "another",
    "such",
    "own",
}

# ═══════════════════════════════════════════════════════════════════════════════
# Markdown Generation Settings
# ═══════════════════════════════════════════════════════════════════════════════

# Default sections in generated markdown
DEFAULT_MARKDOWN_SECTIONS = [
    "Metadata",
    "Summary",
    "Content",
    "Links",
    "Additional Context",
    "Keywords",
]

# Maximum lengths for various fields
MAX_TITLE_LENGTH = 60
MAX_SUMMARY_LENGTH = 200
MAX_KEYWORD_COUNT = 10
MAX_TAG_COUNT = 5

# Minimum word length for keyword extraction
MIN_KEYWORD_LENGTH = 3

# ═══════════════════════════════════════════════════════════════════════════════
# Tool Safety Settings
# ═══════════════════════════════════════════════════════════════════════════════

# Safe git commands (read-only operations)
SAFE_GIT_COMMANDS = [
    "status",
    "log",
    "diff",
    "branch",
    "remote",
    "show",
]

# Dangerous shell command patterns to block
DANGEROUS_SHELL_PATTERNS = [
    "rm -rf",
    "rm -f",
    "> /dev",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",  # Fork bomb
    "chmod -R",
    "chown -R",
    "sudo",
    "su -",
    "wget",
    "curl",
]
