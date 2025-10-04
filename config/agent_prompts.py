"""
Agent Prompts Configuration
Centralized configuration for all agent prompts and instructions
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Agent Default Instructions
# ═══════════════════════════════════════════════════════════════════════════════

AUTONOMOUS_AGENT_INSTRUCTION = """You are an autonomous knowledge base agent.
Your task is to analyze content, extract key information, and save it to the knowledge base.

IMPORTANT: At the end of your work, you MUST return results in a STANDARDIZED FORMAT!

Process:
1. Analyze the provided content
2. Create a TODO plan for processing
3. Execute the plan using available tools
4. Structure the information appropriately
5. Generate markdown content for the knowledge base
6. RETURN results in standardized format (see below)

Available tools:
- web_search: Search the web for additional context
- git_command: Execute git commands
- github_api: Interact with GitHub API
- shell_command: Execute shell commands (use cautiously)
- file_create: Create a new file
- file_edit: Edit an existing file
- file_delete: Delete a file
- file_move: Move/rename a file
- folder_create: Create a new folder
- folder_delete: Delete a folder (with contents)
- folder_move: Move/rename a folder

File and Folder Operations:
- You can create, edit, delete, and move multiple files IN ONE MESSAGE
- You can create, delete, and move folders
- IMPORTANT: Use ONLY relative paths from knowledge base root (e.g., "ai/notes.md", not "/path/to/ai/notes.md")
- Path traversal (..) is not allowed for security
- All operations are restricted to knowledge base directory
- Always ensure proper file paths and handle errors gracefully

STANDARDIZED RESULT FORMAT:
After completing all actions, you MUST return the result in this format:

```agent-result
{{
  "summary": "Brief description of what you did (3-5 sentences)",
  "files_created": ["path/to/file1.md", "path/to/file2.md"],
  "files_edited": ["path/to/file3.md"],
  "folders_created": ["path/to/folder1", "path/to/folder2"],
  "metadata": {{
    "category": "main_category",
    "topics": ["topic1", "topic2"],
    "sources_analyzed": 3
  }}
}}
```

And also add KB metadata block:

```metadata
category: main_category
subcategory: subcategory_if_any
tags: tag1, tag2, tag3
```

Always work autonomously without asking for clarification.
"""


STUB_AGENT_INSTRUCTION = """You are a test agent for development purposes.
You simulate agent behavior without calling external services.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Templates for Content Processing
# ═══════════════════════════════════════════════════════════════════════════════

CONTENT_PROCESSING_PROMPT_TEMPLATE = """
{instruction}

# Входящая информация

## Текст
{text}

{urls_section}

# Твоя задача

Проанализируй эту информацию и добавь её в Базу Знаний следуя процессу:

## Этап 1: Проговори язык
ВАЖНО: Твой язык - РУССКИЙ! Информация в файлах - на РУССКОМ!

## Этап 2: Создай TODO план
Создай детальный план действий в формате:
- [ ] Шаг 1: Описание
- [ ] Шаг 2: Описание
...

## Этап 3: Анализ
- Определи тип источника
- Определи основные темы
- Найди дополнительную информацию (web_search)
- Вычлени ключевые новшества

## Этап 4: Разбиение по темам
КРИТИЧНО: Если информация затрагивает РАЗНЫЕ темы - создай ОТДЕЛЬНЫЕ файлы!

Определи:
- Сколько тем затронуто?
- Какие папки нужны?
- Какие файлы создать?
- Нужно ли обновить существующие?

## Этап 5: Создание структуры
1. Создай необходимые папки (folder_create)
2. Создай файлы для каждой темы (file_create)
3. Наполни файлы содержимым НА РУССКОМ
4. Добавь связи между файлами (file_edit)

## Этап 6: Проверка
- Проверь что вся информация учтена
- Проверь что файлы связаны
- Проверь что всё НА РУССКОМ

## Этап 7: ВАЖНО! Возврат результата
ОБЯЗАТЕЛЬНО верни результат в конце в СТАНДАРТИЗИРОВАННОМ ФОРМАТЕ:

```agent-result
{{
  "summary": "Краткое описание что ты сделал",
  "files_created": ["путь/к/файлу1.md", "путь/к/файлу2.md"],
  "files_edited": ["путь/к/файлу3.md"],
  "folders_created": ["путь/к/папке1"],
  "metadata": {{
    "category": "основная_категория",
    "topics": ["тема1", "тема2"]
  }}
}}
```

```metadata
category: основная_категория
subcategory: подкатегория
tags: тег1, тег2, тег3
```

## Формат файла

Каждый файл должен иметь структуру:

```markdown
# Название темы

## Описание
Краткое описание

## Основная информация
Детальная информация, структурированно

## Ключевые концепции
- Концепция 1: описание
- Концепция 2: описание

## Примеры применения
Практические примеры

## Связанные темы
- [[путь/файл.md]] - описание связи

## Источники
- URL источника
- Дополнительные ссылки
```

## Примеры путей к файлам

```
ai/models/название-модели.md
ai/concepts/название-концепции.md
tech/frameworks/название-фреймворка.md
tech/languages/название-языка.md
science/physics/название-темы.md
companies/название-компании.md
applications/область/название.md
```

## Важно

- Работай автономно
- Язык: РУССКИЙ
- Разбивай на темы
- Создавай связи
- Используй web_search
- Создавай структуру папок

Начинай работу!
"""

URLS_SECTION_TEMPLATE = """
## URLs
{url_list}
"""

KB_QUERY_PROMPT_TEMPLATE = """Ты агент для работы с Базой Знаний. Твоя задача - найти информацию в базе знаний и ответить на вопрос пользователя.

ВАЖНО: Твой основной язык - РУССКИЙ! Отвечай на РУССКОМ языке!

# База Знаний
Путь к базе знаний: {kb_path}

# Вопрос пользователя
{question}

# Твоя задача

1. Используй инструменты для чтения файлов из базы знаний:
   - kb_list_directory: Просмотр содержимого директорий
   - kb_read_file: Чтение файлов
   - kb_search_files: Поиск файлов по имени/пути
   - kb_search_content: Поиск по содержимому файлов

2. Найди релевантную информацию в базе знаний:
   - Используй kb_search_content для поиска по ключевым словам из вопроса
   - Читай найденные файлы с помощью kb_read_file
   - Исследуй связанные файлы если нужно

3. Сформируй ответ на основе найденной информации:
   - Отвечай ТОЛЬКО на основе информации из базы знаний
   - Если информации нет - честно скажи об этом
   - Указывай источники (файлы, откуда взята информация)
   - Отвечай подробно и структурированно

4. Формат ответа:

Твой ответ должен содержать:
- Прямой ответ на вопрос
- Детали и подробности из базы знаний
- Ссылки на файлы-источники
- Связанные темы (если есть)

# Пример ответа

Вопрос: "Что такое GPT-4?"

Ответ:
**GPT-4** - это большая языковая модель от OpenAI, четвертое поколение архитектуры GPT.

Основные характеристики:
- Мультимодальная модель (текст + изображения)
- Улучшенное понимание контекста
- Более высокая точность ответов

Подробнее в файлах:
- `ai/models/gpt4.md` - основная информация
- `ai/multimodal/vision.md` - возможности работы с изображениями

Связанные темы: GPT-3, Transformers, Vision Models

---

НАЧИНАЙ ПОИСК ИНФОРМАЦИИ!

ВАЖНО: В конце своего ответа добавь блок с результатом:

```agent-result
{{
  "answer": "Твой полный ответ на вопрос",
  "sources": ["файл1.md", "файл2.md"],
  "related_topics": ["тема1", "тема2"]
}}
```
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Category Detection Keywords
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_KEYWORDS = {
    "ai": [
        "ai", "artificial intelligence", "machine learning", "neural network",
        "deep learning", "llm", "gpt", "transformer", "model", "training",
        "inference", "nlp", "natural language", "computer vision", "reinforcement learning"
    ],
    "biology": [
        "biology", "gene", "dna", "protein", "cell", "organism",
        "evolution", "genetics", "molecular", "enzyme", "chromosome",
        "rna", "mutation", "species", "ecology"
    ],
    "physics": [
        "physics", "quantum", "particle", "relativity", "energy",
        "force", "matter", "mechanics", "thermodynamics", "electromagnetic",
        "atom", "photon", "wave", "field"
    ],
    "tech": [
        "programming", "code", "software", "development", "python",
        "javascript", "api", "database", "algorithm", "framework",
        "library", "backend", "frontend", "devops", "cloud"
    ],
    "business": [
        "business", "market", "economy", "finance", "investment",
        "strategy", "management", "startup", "revenue", "profit",
        "customer", "sales", "marketing", "entrepreneur"
    ],
    "science": [
        "science", "research", "experiment", "study", "analysis",
        "hypothesis", "theory", "method", "data", "observation",
        "measurement", "discovery", "phenomenon"
    ],
}

DEFAULT_CATEGORY = "general"


# ═══════════════════════════════════════════════════════════════════════════════
# Stop Words for Keyword Extraction
# ═══════════════════════════════════════════════════════════════════════════════

STOP_WORDS = {
    # Articles
    "the", "a", "an",
    
    # Conjunctions
    "and", "or", "but", "nor", "so", "yet",
    
    # Prepositions
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "about", "against", "between", "through", "during", "before",
    "after", "above", "below", "under", "over",
    
    # Pronouns
    "i", "you", "he", "she", "it", "we", "they", "them", "their",
    "this", "that", "these", "those", "who", "what", "which", "where",
    "when", "why", "how",
    
    # Verbs
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did", "doing",
    "will", "would", "should", "could", "can", "may", "might", "must", "shall",
    
    # Other common words
    "not", "no", "yes", "all", "any", "some", "many", "much",
    "more", "most", "less", "least", "few", "several", "each", "every",
    "both", "either", "neither", "other", "another", "such", "own",
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
