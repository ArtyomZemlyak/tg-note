# Интеграция Qwen Code CLI

## Обзор

Реализована полная интеграция с [qwen-code](https://github.com/QwenLM/qwen-code) CLI инструментом для автономной обработки контента с использованием Qwen3-Coder моделей.

## Возможности

### ✅ Реализованные функции

1. **Прямая интеграция с qwen-code CLI** - Python wrapper для вызова qwen CLI
2. **Автономный режим** - агент работает без запросов к пользователю
3. **TODO планирование** - qwen-code генерирует и выполняет план обработки
4. **Встроенные инструменты** - web search, git, github, shell commands (через qwen-code)
5. **Настраиваемые инструкции** - кастомизация поведения агента
6. **Fallback режим** - базовая обработка при недоступности CLI

## Архитектура

```
┌─────────────────────┐
│  Telegram Bot       │
│  (получает сообщ.)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  QwenCodeCLIAgent   │  ◄── Python wrapper
│  (подготовка)       │
└──────────┬──────────┘
           │ prompt
           ▼
┌─────────────────────┐
│  qwen CLI           │  ◄── Node.js CLI
│  (обработка)        │
└──────────┬──────────┘
           │ markdown + metadata
           ▼
┌─────────────────────┐
│  Knowledge Base     │
│  (сохранение)       │
└─────────────────────┘
```

## Установка

### 1. Установка Node.js (если не установлен)

```bash
# Проверить установку
node --version

# Установить Node.js 20+ (если нужно)
curl -qL https://www.npmjs.com/install.sh | sh
```

### 2. Установка qwen-code CLI

```bash
# Глобальная установка
npm install -g @qwen-code/qwen-code@latest

# Проверить установку
qwen --version
```

### 3. Настройка аутентификации

#### Вариант A: Qwen OAuth (Рекомендуется)

**Преимущества:**
- 2000 запросов в день бесплатно
- 60 запросов в минуту
- Нет ограничений на токены
- Автоматическое управление credentials

```bash
# Первый запуск - интерактивная аутентификация
qwen

# Следуйте инструкциям для аутентификации через qwen.ai
```

#### Вариант B: OpenAI-совместимый API

```bash
# Для использования с другими API (ModelScope, OpenRouter, и др.)
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="your-base-url"

# Или добавить в .env
echo "OPENAI_API_KEY=your-api-key" >> .env
echo "OPENAI_BASE_URL=your-base-url" >> .env
```

#### Вариант C: ModelScope (Материковый Китай)

```bash
# 2000 бесплатных вызовов в день
export MODELSCOPE_API_KEY="your-modelscope-key"
```

## Конфигурация

### config.yaml

```yaml
# Agent Configuration
AGENT_TYPE: "qwen_code_cli"  # Использовать qwen-code CLI
AGENT_QWEN_CLI_PATH: "qwen"  # Путь к qwen CLI (или полный путь)
AGENT_TIMEOUT: 300  # Timeout в секундах (5 минут)

# Настройки инструментов
AGENT_ENABLE_WEB_SEARCH: true
AGENT_ENABLE_GIT: true
AGENT_ENABLE_GITHUB: true
AGENT_ENABLE_SHELL: false

# Опциональная кастомная инструкция
# AGENT_INSTRUCTION: "Ваша кастомная инструкция..."
```

### .env (для API ключей)

```bash
# GitHub токен (для GitHub API)
GITHUB_TOKEN=your_github_token

# OpenAI-совместимый API (опционально)
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=your_base_url
```

## Использование

### Автоматическое использование с Telegram ботом

После настройки, агент автоматически используется ботом:

```bash
# 1. Настроить config.yaml
cp config.example.yaml config.yaml
nano config.yaml  # установить AGENT_TYPE: "qwen_code_cli"

# 2. Установить qwen CLI
npm install -g @qwen-code/qwen-code@latest

# 3. Аутентифицироваться
qwen  # следовать инструкциям

# 4. Запустить бота
python main.py
```

Бот автоматически:
1. Получает сообщения от пользователя
2. Передает их QwenCodeCLIAgent
3. Агент вызывает qwen CLI для обработки
4. Результат сохраняется в базу знаний

### Программное использование

```python
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

# Создать агент
agent = QwenCodeCLIAgent(
    instruction="Кастомная инструкция для агента",
    enable_web_search=True,
    enable_git=True,
    enable_github=True,
    timeout=300
)

# Обработать контент
content = {
    "text": "Статья о машинном обучении и нейронных сетях...",
    "urls": ["https://arxiv.org/abs/12345"]
}

result = await agent.process(content)

# Результат содержит:
print(result["markdown"])      # Отформатированный markdown
print(result["title"])         # Заголовок
print(result["kb_structure"])  # Структура для KB
print(result["metadata"])      # Метаданные обработки
```

### Проверка установки

```python
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

# Проверить установку qwen CLI
if QwenCodeCLIAgent.check_installation():
    print("✓ qwen CLI установлен")
else:
    print("✗ qwen CLI не найден")
    print(QwenCodeCLIAgent.get_installation_instructions())
```

## Как это работает

### 1. Подготовка промпта

Агент создает структурированный промпт для qwen CLI:

```markdown
{INSTRUCTION}

# Input Content

## Text Content
{текст от пользователя}

## URLs
- {URL 1}
- {URL 2}

# Task

1. Create a TODO checklist for processing this content
2. Analyze the content and extract key information
3. Determine the category
4. Extract relevant tags
5. Generate structured markdown document

Work autonomously and provide complete output.
```

### 2. Вызов qwen CLI

```python
# Агент вызывает qwen CLI через subprocess
process = await asyncio.create_subprocess_exec(
    "qwen",
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)

stdout, stderr = await asyncio.wait_for(
    process.communicate(input=prompt.encode()),
    timeout=300
)
```

### 3. Парсинг результата

Агент извлекает из вывода qwen CLI:

- **Markdown контент** - основной отформатированный текст
- **Metadata блок** - категория, теги, подкатегория
- **TODO план** - чеклист выполненных задач
- **Заголовок** - первый # heading

```markdown
# Заголовок статьи

## Metadata
```metadata
category: ai
subcategory: machine-learning
tags: neural-networks, deep-learning, transformers
```

## TODO Plan
- [x] Analyze content
- [x] Extract key topics
- [x] Generate summary
- [x] Structure content

## Content
{основной контент}
```

### 4. Сохранение в KB

Результат передается в Knowledge Base Manager для сохранения.

## Возможности qwen-code

### Встроенные инструменты

qwen-code CLI имеет встроенную поддержку:

1. **Code Understanding** - анализ кода за пределами контекстного окна
2. **File Operations** - чтение и редактирование файлов
3. **Git Operations** - работа с git репозиториями
4. **Shell Commands** - выполнение команд оболочки
5. **Web Search** - поиск информации в интернете
6. **Vision Model** - анализ изображений

### Автоматическое планирование

qwen-code автоматически:
- Создает план выполнения задачи
- Разбивает на подзадачи
- Выполняет шаг за шагом
- Использует необходимые инструменты

### Адаптивность

qwen-code оптимизирован для Qwen3-Coder моделей, которые:
- Понимают сложный код
- Генерируют качественный код
- Работают с большими кодовыми базами
- Поддерживают multiple programming languages

## Кастомизация

### Изменение инструкции

```python
agent = QwenCodeCLIAgent()

# Установить свою инструкцию
agent.set_instruction("""
Вы - специализированный агент для научных статей.
Фокусируйтесь на:
- Методологии исследования
- Результатах и выводах
- Новизне работы
- Практическом применении

Формат вывода: структурированный markdown с секциями:
- Summary, Methodology, Results, Conclusions, References
""")

# Использовать
result = await agent.process(content)
```

### Изменение timeout

```yaml
# config.yaml
AGENT_TIMEOUT: 600  # 10 минут для длинных задач
```

```python
# Или в коде
agent = QwenCodeCLIAgent(timeout=600)
```

### Указание пути к qwen CLI

Если qwen установлен не глобально:

```yaml
# config.yaml
AGENT_QWEN_CLI_PATH: "/usr/local/bin/qwen"
```

```python
# Или в коде
agent = QwenCodeCLIAgent(qwen_cli_path="/path/to/qwen")
```

## Fallback режим

Если qwen CLI недоступен или возвращает ошибку, агент автоматически использует fallback:

```python
def _fallback_processing(self, prompt: str) -> str:
    """Базовая обработка без qwen CLI"""
    # Извлекает текст из промпта
    # Генерирует простой markdown
    # Определяет категорию по ключевым словам
    # Возвращает структурированный результат
```

Это гарантирует, что система продолжит работать даже при проблемах с CLI.

## Производительность

### Типичное время обработки

- **Короткий текст** (< 500 слов): 5-15 секунд
- **Средний текст** (500-2000 слов): 15-45 секунд
- **Длинный текст** (> 2000 слов): 45-120 секунд

### Факторы, влияющие на скорость

- Длина контента
- Сложность задачи
- Количество URL для анализа
- Использование vision model (для изображений)
- Загруженность API
- Скорость интернет-соединения

### Оптимизация

```yaml
# Для более быстрой обработки
AGENT_TIMEOUT: 120  # Меньший timeout

# Отключить ненужные инструменты
AGENT_ENABLE_WEB_SEARCH: false  # Если не нужен поиск
```

## Мониторинг и отладка

### Логирование

```python
import logging

# Включить DEBUG логи
logging.getLogger("src.agents.qwen_code_cli_agent").setLevel(logging.DEBUG)

# Логи будут содержать:
# - Проверку доступности CLI
# - Подготовку промпта
# - Вызов CLI
# - Парсинг результата
# - Ошибки и fallback
```

### Метаданные результата

```python
result = await agent.process(content)

metadata = result["metadata"]
print(f"Agent: {metadata['agent']}")
print(f"Processed at: {metadata['processed_at']}")
print(f"TODO plan: {metadata['todo_plan']}")
print(f"Tools enabled: {metadata['tools_enabled']}")
```

### Отладка CLI

```bash
# Тестировать qwen CLI напрямую
echo "Explain machine learning" | qwen

# Проверить аутентификацию
qwen /auth

# Проверить конфигурацию
cat ~/.qwen/config.json
```

## Сравнение вариантов агентов

### qwen_code_cli (Рекомендуется) ✅

**Преимущества:**
- ✅ Прямое использование qwen-code CLI
- ✅ Все встроенные инструменты qwen-code
- ✅ Автоматическое планирование
- ✅ Оптимизация для Qwen3-Coder
- ✅ Бесплатный tier (2000 req/day)
- ✅ Постоянные обновления от QwenLM

**Недостатки:**
- ⚠️ Требует Node.js
- ⚠️ Внешняя зависимость

**Когда использовать:** По умолчанию для production

### qwen_code

**Преимущества:**
- ✅ Pure Python
- ✅ Гибкая кастомизация
- ✅ Свои инструменты

**Недостатки:**
- ⚠️ Требует свою реализацию инструментов
- ⚠️ Нет автоматического планирования qwen-code

**Когда использовать:** Если нужна полная кастомизация

### stub

**Преимущества:**
- ✅ Нет внешних зависимостей
- ✅ Быстрый
- ✅ Простой

**Недостатки:**
- ⚠️ Базовая обработка
- ⚠️ Нет AI анализа
- ⚠️ Простая категоризация

**Когда использовать:** Для тестирования или MVP

## Troubleshooting

### Проблема: "Qwen CLI not found"

```bash
# Проверить установку
which qwen

# Если не найден, установить
npm install -g @qwen-code/qwen-code@latest

# Проверить PATH
echo $PATH

# Добавить в PATH если нужно
export PATH="$PATH:$HOME/.npm-global/bin"
```

### Проблема: "Authentication failed"

```bash
# Переаутентифицироваться
qwen /auth

# Или удалить старые credentials
rm -rf ~/.qwen
qwen  # аутентифицироваться заново
```

### Проблема: "Timeout exceeded"

```yaml
# Увеличить timeout в config.yaml
AGENT_TIMEOUT: 600  # 10 минут
```

### Проблема: "Empty result from qwen CLI"

Агент автоматически использует fallback режим. Проверить:

```bash
# Тестировать CLI напрямую
echo "Test prompt" | qwen

# Проверить логи
tail -f logs/bot.log
```

### Проблема: "Rate limit exceeded"

```bash
# Проверить лимиты для вашего аккаунта
# Qwen OAuth: 60 req/min, 2000 req/day
# Подождать или использовать другой API endpoint
```

## Примеры использования

### Пример 1: Обработка научной статьи

```python
agent = QwenCodeCLIAgent(
    instruction="""
    Специализация: Научные статьи
    
    Извлекай:
    - Основную гипотезу
    - Методологию
    - Результаты
    - Выводы
    - Ограничения исследования
    """
)

content = {
    "text": """
    Новое исследование показывает, что трансформеры...
    Методология: использовали датасет...
    Результаты: точность 95.3%...
    """,
    "urls": ["https://arxiv.org/abs/12345"]
}

result = await agent.process(content)
# qwen CLI проанализирует статью и структурирует информацию
```

### Пример 2: Анализ GitHub репозитория

```python
content = {
    "text": "Анализ репозитория QwenLM/Qwen3-Coder",
    "urls": ["https://github.com/QwenLM/Qwen3-Coder"]
}

# qwen CLI автоматически:
# - Получит информацию о репозитории
# - Проанализирует README
# - Извлечет ключевые features
# - Сгенерирует структурированный обзор
result = await agent.process(content)
```

### Пример 3: Обработка технической документации

```python
agent = QwenCodeCLIAgent(
    instruction="""
    Специализация: Техническая документация
    
    Создай:
    - Краткий обзор
    - Ключевые концепции
    - Примеры использования
    - Best practices
    - Common pitfalls
    """
)

content = {
    "text": "Документация по FastAPI...",
    "urls": ["https://fastapi.tiangolo.com/"]
}

result = await agent.process(content)
```

## Roadmap

- [ ] Поддержка стриминга результатов
- [ ] Кэширование часто используемых промптов
- [ ] Batch обработка множества сообщений
- [ ] Интеграция с vision моделями для изображений
- [ ] Статистика использования токенов
- [ ] Auto-retry при ошибках
- [ ] Поддержка custom tools через qwen CLI

## Ресурсы

- [Qwen Code GitHub](https://github.com/QwenLM/qwen-code)
- [Qwen Code Docs](https://qwenlm.github.io/qwen-code-docs/)
- [Qwen3-Coder](https://github.com/QwenLM/Qwen3-Coder)
- [Qwen.ai](https://qwen.ai)
- [ModelScope](https://www.modelscope.cn/)

## Лицензия

MIT License - см. LICENSE файл

## Контрибуция

Для улучшения интеграции с qwen-code:
1. Fork репозиторий
2. Создать feature branch
3. Коммит изменений
4. Push и создать Pull Request
