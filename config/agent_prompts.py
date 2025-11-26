"""
Agent Prompts Configuration (Refactored)

Centralized configuration for all agent prompts and instructions.

This module provides a unified interface for prompt management using the promptic library.
Prompts are stored as versioned files under `config/prompts/` and loaded via the
`PrompticService` from `src.prompts.promptic_service`.

USAGE (Recommended - Single render() call):
    from src.prompts import prompt_service

    # Complete note mode prompt in ONE LINE:
    prompt = prompt_service.render(
        "note_mode_prompt",
        version="latest",
        vars={"text": "User content", "urls": ["https://example.com"]},
        export_to="output/prompt.md"  # optional
    )

    # Complete ask mode prompt in ONE LINE:
    prompt = prompt_service.render(
        "ask_mode_prompt",
        version="latest",
        vars={"question": "What is GPT?", "kb_path": "/kb"}
    )

USAGE (Legacy - individual getters):
    from config.agent_prompts import get_qwen_code_cli_instruction

    instruction = get_qwen_code_cli_instruction(locale="ru")

AICODE-NOTE: This module now wraps the PrompticService for backwards compatibility.
New code should use prompt_service.render() directly for the cleanest API.
"""

from __future__ import annotations

from src.prompts.promptic_service import prompt_service

# ═══════════════════════════════════════════════════════════════════════════════
# Agent Default Instructions (via promptic service)
# ═══════════════════════════════════════════════════════════════════════════════


def get_qwen_code_agent_instruction(locale: str = "en", version: str | None = None) -> str:
    """Get autonomous agent instruction (for QwenCodeAgent)."""
    return prompt_service.render_autonomous_agent_instruction(
        locale=locale, version=version or "latest"
    )


def get_qwen_code_cli_instruction(locale: str = "ru", version: str | None = None) -> str:
    """Get Qwen CLI agent instruction (for QwenCodeCLIAgent - note mode)."""
    return prompt_service.render_agent_instruction(locale=locale, version=version or "latest")


STUB_AGENT_INSTRUCTION = (
    "You are a test agent for development purposes.\n"
    "You simulate agent behavior without calling external services.\n"
)

# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Templates for Content Processing (via promptic service)
# ═══════════════════════════════════════════════════════════════════════════════


def get_content_processing_template(locale: str = "ru", version: str | None = None) -> str:
    """Get content processing template."""
    return prompt_service._legacy_render("content_processing", locale, version or "latest", {})


def get_urls_section_template(locale: str = "ru", version: str | None = None) -> str:
    """Get URLs section template."""
    return prompt_service._legacy_render("urls_section", locale, version or "latest", {})


def get_ask_mode_instruction(locale: str = "ru", version: str | None = None) -> str:
    """Get ask mode agent instruction."""
    return prompt_service.render_ask_instruction(locale=locale, version=version or "latest")


def get_kb_query_template(locale: str = "ru", version: str | None = None) -> str:
    """Get KB query template."""
    return prompt_service._legacy_render("kb_query", locale, version or "latest", {})


def get_media_instruction(locale: str = "ru", version: str | None = None) -> str:
    """Get media handling instruction."""
    return prompt_service.render_media_instruction(locale=locale, version=version or "latest")


# ═══════════════════════════════════════════════════════════════════════════════
# Unified Prompt Rendering (NEW - Recommended API)
# ═══════════════════════════════════════════════════════════════════════════════


def render_note_mode_prompt(
    text: str,
    urls: list | None = None,
    locale: str = "ru",
    version: str = "latest",
    export_to: str | None = None,
) -> str:
    """
    Render complete note mode prompt in ONE LINE.

    This is the recommended way to get prompts for the note processing mode.

    Args:
        text: User text content to process
        urls: List of URLs from the content
        locale: Locale for the prompt
        version: Version specification
        export_to: Optional path to export rendered prompt

    Returns:
        Complete rendered prompt for note mode

    Example:
        prompt = render_note_mode_prompt(
            text="Article about GPT-4...",
            urls=["https://openai.com/research/gpt-4"],
        )
    """
    return prompt_service.render(
        "note_mode_prompt",
        version=version,
        locale=locale,
        vars={"text": text, "urls": urls or []},
        export_to=export_to,
    )


def render_ask_mode_prompt(
    question: str,
    kb_path: str,
    context: str = "",
    locale: str = "ru",
    version: str = "latest",
    export_to: str | None = None,
) -> str:
    """
    Render complete ask mode prompt in ONE LINE.

    This is the recommended way to get prompts for the question answering mode.

    Args:
        question: User's question
        kb_path: Path to the knowledge base
        context: Optional conversation context
        locale: Locale for the prompt
        version: Version specification
        export_to: Optional path to export rendered prompt

    Returns:
        Complete rendered prompt for ask mode

    Example:
        prompt = render_ask_mode_prompt(
            question="What is GPT-4?",
            kb_path="/path/to/kb",
        )
    """
    return prompt_service.render(
        "ask_mode_prompt",
        version=version,
        locale=locale,
        vars={"question": question, "kb_path": kb_path, "context": context},
        export_to=export_to,
    )


# Backward-compatible constants (deprecated): lazy loading to avoid circular imports
# AICODE-NOTE: These constants use lazy loading to prevent circular imports.
# The values are resolved on first access, not at module import time.
# New code should use the functions or prompt_service directly.


class _LazyPromptLoader:
    """Lazy loader for backward-compatible prompt constants."""

    _cache = {}

    @classmethod
    def get(cls, name: str):
        """Get a lazily-loaded prompt constant."""
        if name not in cls._cache:
            if name == "QWEN_CODE_AGENT_INSTRUCTION":
                cls._cache[name] = get_qwen_code_agent_instruction("en")
            elif name == "QWEN_CODE_CLI_AGENT_INSTRUCTION":
                cls._cache[name] = get_qwen_code_cli_instruction("ru")
            elif name == "CONTENT_PROCESSING_PROMPT_TEMPLATE":
                cls._cache[name] = get_content_processing_template("ru")
            elif name == "URLS_SECTION_TEMPLATE":
                cls._cache[name] = get_urls_section_template("ru")
            elif name == "ASK_MODE_AGENT_INSTRUCTION":
                cls._cache[name] = get_ask_mode_instruction("ru")
            elif name == "KB_QUERY_PROMPT_TEMPLATE":
                cls._cache[name] = get_kb_query_template("ru")
            else:
                raise KeyError(f"Unknown lazy prompt constant: {name}")
        return cls._cache[name]


# AICODE-NOTE: Use __getattr__ for lazy loading of module-level constants
# This prevents circular imports when the module is first loaded
def __getattr__(name: str):
    """Lazy load prompt constants on first access."""
    if name in (
        "QWEN_CODE_AGENT_INSTRUCTION",
        "QWEN_CODE_CLI_AGENT_INSTRUCTION",
        "CONTENT_PROCESSING_PROMPT_TEMPLATE",
        "URLS_SECTION_TEMPLATE",
        "ASK_MODE_AGENT_INSTRUCTION",
        "KB_QUERY_PROMPT_TEMPLATE",
    ):
        return _LazyPromptLoader.get(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mode Instruction (kept inline; single authoritative definition)
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_MODE_INSTRUCTION = """Ты автономный агент для работы с Базой Знаний.
Твой основной язык - РУССКИЙ!

Ты можешь выполнять ЛЮБЫЕ задачи с базой знаний:
- Отвечать на вопросы пользователя
- Добавлять новую информацию
- Редактировать существующие заметки
- Переструктурировать базу знаний
- Создавать новые файлы и папки
- Удалять или перемещать файлы
- Искать информацию в интернете и добавлять ее
- Анализировать и улучшать структуру базы знаний

## КРИТИЧНО: Многоэтапная стратегия поиска

Когда тебе нужно найти информацию в базе знаний, ВСЕГДА следуй этому 3-этапному подходу:

### Этап 1: Файловый поиск
- Извлеки ключевые термины из своего запроса
- Ищи файлы по шаблонам имён (например, "*gpt*.md", "*нейронн*")
- Найди релевантные имена файлов на основе тем/ключевых слов
- Это даст тебе быстрый список потенциально релевантных файлов

### Этап 2: Семантический векторный поиск
- Выполни семантический поиск с твоим запросом на естественном языке
- Это находит семантически похожий контент по всей базе знаний
- Получи топ 5-10 наиболее релевантных документов
- Отметь, какие файлы появляются в результатах - они семантически связаны

### Этап 3: Уточняющий поиск по содержимому
- Объедини результаты Этапа 1 и Этапа 2
- Ищи конкретные термины внутри перспективных файлов
- Прочитай наиболее релевантные файлы полностью
- Если нужно, сделай ещё один семантический поиск с уточнённым запросом

## Твои возможности:

### Многоэтапный поиск:
- Файловый поиск по шаблонам имён
- Семантический векторный поиск (AI-powered)
- Поиск по содержимому файлов
- Чтение файлов полностью

### Чтение и анализ:
- Просматривай структуру базы знаний (ls, find, glob)
- Читай содержимое файлов (read)
- Ищи информацию по ключевым словам (grep, rg)

### Модификация:
- Создавай файлы (file_create)
- Редактируй файлы (file_edit)
- Удаляй файлы (file_delete)
- Перемещай файлы (file_move)
- Создавай папки (folder_create)
- Удаляй папки (folder_delete)
- Перемещай папки (folder_move)

### Поиск информации:
- Ищи дополнительную информацию в интернете (web_search)
- Анализируй ссылки из источников

## Процесс работы:

1. **Пойми задачу**: Внимательно прочитай запрос пользователя
2. **Составь план**: Определи что нужно сделать
3. **Исследуй базу**: Изучи текущую структуру и содержимое используя многоэтапный поиск (файловый → векторный → уточняющий)
4. **Выполни задачу**: Используй нужные инструменты
5. **Проверь результат**: Убедись что задача выполнена
6. **Сообщи пользователю**: Опиши что ты сделал

## КРИТИЧНО: Ссылки на источники

**ОБЯЗАТЕЛЬНОЕ ТРЕБОВАНИЕ:** При создании или редактировании файлов ты ДОЛЖЕН максимально ссылаться на источники!

### Как добавлять ссылки:

1. **Inline-цитирование** - прямо в тексте рядом с информацией:
   - Формат: `Согласно [название](URL), ...` или `... как описано в [источнике](URL)`
   - Пример: `GPT-4 использует архитектуру трансформера ([OpenAI Report](https://openai.com/research/gpt-4))`

2. **Раздел "Источники"** - ОБЯЗАТЕЛЬНО в конце КАЖДОГО файла:
   ```markdown
   ## Источники

   1. [Название источника 1](URL) - краткое описание
   2. [Название источника 2](URL) - краткое описание
   ```

3. **Дополнительные материалы** - если нашёл через web_search:
   ```markdown
   ## См. также

   - [Дополнительный материал](URL) - описание
   ```

**ПОМНИ:**
- Раздел "Источники" должен быть в КАЖДОМ создаваемом файле
- Чем больше ссылок - тем лучше
- Сохраняй все URL из исходных материалов

## Важные правила:

- ЯЗЫК: РУССКИЙ для всех файлов и ответов!
- **КРИТИЧНО: ВСЕГДА добавляй ссылки на источники в каждый файл!**
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
