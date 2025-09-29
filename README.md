# TG-Note: Intelligent Telegram Bot for Knowledge Management

Telegram bot for creating and managing notes in GitHub knowledge base using AI agents.

## 🎯 Цель проекта

Автоматизировать процесс сбора, анализа и структурирования информации из Telegram сообщений в организованную базу знаний на GitHub в виде Markdown файлов.

## 🏗️ Архитектура системы

### Компоненты системы

```mermaid
graph TD
    A[Telegram Bot] --> B[Message Processor]
    B --> C[Agent System]
    C --> D[Content Analyzer]
    D --> E[Knowledge Classifier]
    E --> F[GitHub Integration]
    F --> G[Knowledge Base Repository]
    
    H[Database] --> B
    H --> F
    
    I[Configuration Manager] --> A
    I --> C
    I --> F
```

### 1. Telegram Bot Layer
- **Функции**: Прием сообщений, репостов, медиафайлов
- **Технологии**: `python-telegram-bot`, `asyncio`
- **Возможности**:
  - Обработка текстовых сообщений
  - Обработка пересланных сообщений
  - Обработка медиафайлов (изображения, документы)
  - Команды управления ботом
  - Аутентификация пользователей

### 2. Agent System (AI Processing)
- **Функции**: Анализ и обработка контента
- **Варианты реализации**:
  - **OpenAI GPT-4/GPT-3.5**: Высокое качество, платный API
  - **Anthropic Claude**: Альтернатива OpenAI
  - **Local LLM**: Ollama с моделями Llama/Mistral для приватности
  - **Hybrid**: Комбинация для разных задач
- **Задачи агента**:
  - Извлечение ключевой информации
  - Категоризация контента
  - Генерация заголовков и тегов
  - Структурирование в Markdown
  - Определение релевантности

### 3. GitHub Integration Layer
- **Функции**: Управление файлами в репозитории
- **Технологии**: `PyGithub`, GitHub API
- **Возможности**:
  - Создание/обновление .md файлов
  - Организация по папкам и категориям
  - Коммиты с осмысленными сообщениями
  - Управление ветками для разных типов контента

### 4. Database Layer
- **Функции**: Хранение метаданных и истории
- **Технология**: SQLite/PostgreSQL
- **Схема данных**:
  - Сообщения и их статус обработки
  - Маппинг сообщений на файлы в GitHub
  - Пользователи и права доступа
  - Логи обработки

### 5. Configuration System
- **Функции**: Управление настройками
- **Компоненты**:
  - Environment variables
  - YAML конфигурации
  - Динамические настройки через команды бота

## 🚀 План реализации

### Фаза 1: Базовая инфраструктура (1-2 недели)
1. ✅ Настройка проекта и зависимостей
2. ⏳ Создание базового Telegram бота
3. ⏳ Настройка системы конфигурации
4. ⏳ Базовая обработка сообщений

### Фаза 2: AI Integration (2-3 недели)
1. ⏳ Интеграция с выбранным LLM API
2. ⏳ Создание промптов для анализа контента
3. ⏳ Система классификации и категоризации
4. ⏳ Генерация структурированного Markdown

### Фаза 3: GitHub Integration (1-2 недели)
1. ⏳ Модуль работы с GitHub API
2. ⏳ Система организации файлов
3. ⏳ Автоматические коммиты и PR
4. ⏳ Управление конфликтами и версионированием

### Фаза 4: Database & Persistence (1 неделя)
1. ⏳ Дизайн и создание схемы БД
2. ⏳ ORM модели и миграции
3. ⏳ Система кэширования
4. ⏳ Backup и recovery

### Фаза 5: Advanced Features (2-3 недели)
1. ⏳ Обработка медиафайлов
2. ⏳ Система тегов и поиска
3. ⏳ Пользовательские настройки
4. ⏳ Аналитика и статистика

### Фаза 6: Production Ready (1-2 недели)
1. ⏳ Comprehensive тестирование
2. ⏳ Docker контейнеризация
3. ⏳ CI/CD pipeline
4. ⏳ Мониторинг и логирование
5. ⏳ Документация

## 🛠️ Технологический стек

### Backend
- **Python 3.11+**
- **python-telegram-bot** - Telegram Bot API
- **FastAPI** - Web framework для webhooks
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **PyGithub** - GitHub API client
- **Pydantic** - Data validation

### AI/ML
- **OpenAI API** / **Anthropic API** / **Ollama**
- **LangChain** - LLM framework
- **tiktoken** - Token counting

### Infrastructure
- **Docker** & **Docker Compose**
- **PostgreSQL** / **SQLite**
- **Redis** - Caching и queue
- **GitHub Actions** - CI/CD

### Monitoring & Logging
- **structlog** - Structured logging
- **Sentry** - Error tracking
- **Prometheus** + **Grafana** - Metrics

## 📁 Структура проекта

```
tg-note/
├── src/
│   ├── bot/
│   │   ├── handlers/
│   │   ├── middlewares/
│   │   └── utils/
│   ├── agents/
│   │   ├── analyzers/
│   │   ├── classifiers/
│   │   └── generators/
│   ├── github/
│   │   ├── client.py
│   │   ├── file_manager.py
│   │   └── commit_manager.py
│   ├── database/
│   │   ├── models/
│   │   ├── repositories/
│   │   └── migrations/
│   └── config/
├── tests/
├── docker/
├── docs/
├── knowledge_base/ (example structure)
├── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔧 Конфигурация

### Environment Variables
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# AI Service
OPENAI_API_KEY=your_openai_key
# or
ANTHROPIC_API_KEY=your_anthropic_key
# or
OLLAMA_BASE_URL=http://localhost:11434

# GitHub
GITHUB_TOKEN=your_github_token
GITHUB_REPO_OWNER=your_username
GITHUB_REPO_NAME=knowledge-base

# Database
DATABASE_URL=postgresql://user:pass@localhost/tg_note

# Other
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## 📝 Использование

### Команды бота
- `/start` - Инициализация и приветствие
- `/help` - Справка по командам
- `/settings` - Настройки пользователя
- `/status` - Статус последних обработок
- `/categories` - Управление категориями
- `/search <query>` - Поиск в базе знаний

### Типы обрабатываемого контента
1. **Текстовые сообщения** - прямой анализ и сохранение
2. **Пересланные сообщения** - с сохранением источника
3. **Ссылки** - извлечение и анализ контента
4. **Изображения с текстом** - OCR + анализ
5. **Документы** - извлечение текста + анализ

## 🤖 Логика работы агента

### Анализ контента
1. **Предварительная обработка**: Очистка, нормализация
2. **Извлечение сущностей**: Люди, места, даты, концепции
3. **Определение типа контента**: Заметка, статья, цитата, идея
4. **Категоризация**: Автоматическое определение категории
5. **Генерация метаданных**: Заголовок, теги, краткое описание

### Структурирование
```markdown
# [Generated Title]

## Metadata
- **Source**: Telegram message from @username
- **Date**: 2024-01-15 14:30:00
- **Category**: [Auto-detected category]
- **Tags**: #tag1 #tag2 #tag3

## Content
[Processed and structured content]

## Key Points
- [Extracted key point 1]
- [Extracted key point 2]

## Related Topics
[Links to related notes if found]
```

## 🔒 Безопасность

- Аутентификация пользователей Telegram
- Валидация входных данных
- Rate limiting
- Secure API key management
- Audit logging всех операций

## 📊 Мониторинг

- Метрики обработки сообщений
- Статистика использования AI API
- Мониторинг ошибок и производительности
- Dashboard с ключевыми показателями

## 🤝 Contributing

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
