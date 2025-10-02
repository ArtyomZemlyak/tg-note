# tg-note

Telegram bot для автоматического создания заметок в базе знаний GitHub с использованием агентных систем.

## Описание

Бот принимает репосты и сообщения (новости, разборы научных статей), анализирует их с помощью агентной системы и автоматически сохраняет важную информацию в базу знаний в формате Markdown файлов.

## Архитектура v0 (MVP)

### Общая схема

```
┌─────────────────┐
│  Telegram Bot   │
│   (pyTelegramBotAPI/aiogram)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Message Queue  │ ◄───┐
│  (in-memory)    │     │
└────────┬────────┘     │
         │              │
         ▼              │
┌─────────────────┐     │
│  Agent System   │     │
│  (LangChain/    │     │
│   CrewAI/       │     │
│   Custom)       │     │
└────────┬────────┘     │
         │              │
         ▼              │
┌─────────────────┐     │
│ Knowledge Base  │     │
│  (.md files)    │     │
│  Git/Local      │     │
└─────────────────┘     │
         │              │
         ▼              │
┌─────────────────┐     │
│ Processing Log  │─────┘
│ (processed.json)│
└─────────────────┘
```

### Компоненты

#### 1. Telegram Bot Layer
- **Библиотека**: pyTelegramBotAPI (telebot) или aiogram
- **Функции**:
  - Прием входящих сообщений и репостов
  - Группировка последовательных сообщений в единый контент
  - Базовая валидация и фильтрация
  - Отправка статусов обработки пользователю

#### 2. Message Processor
- **Функции**:
  - Определение границ многосообщенного контента
  - Агрегация текста, медиа, ссылок
  - Передача контента в агентную систему
  - Управление очередью обработки

#### 3. Agent System (заглушка в MVP)
- **Варианты для будущего**:
  - LangChain + GPT-4/Claude
  - CrewAI
  - Custom agents с OpenAI API
- **MVP функционал**:
  - Простая заглушка для тестирования
  - Минимальная обработка текста
  - Форматирование в Markdown
- **Задачи**:
  - Анализ контента на важность и новизну
  - Извлечение ключевой информации
  - Структурирование в формат базы знаний
  - Категоризация по темам

#### 4. Knowledge Base Manager
- **Структура**:
  ```
  knowledge_base/
  ├── topics/
  │   ├── ai/
  │   ├── biology/
  │   └── physics/
  ├── articles/
  │   └── YYYY-MM-DD-title.md
  └── index.md
  ```
- **Функции**:
  - Создание и обновление .md файлов
  - Управление структурой директорий
  - Git operations (add, commit, push)
  - Генерация метаданных

#### 5. Processing Tracker
- **Формат хранения**: JSON файл (`processed.json`)
- **Структура**:
  ```json
  {
    "processed_messages": [
      {
        "message_id": 12345,
        "chat_id": -100123456789,
        "forward_from_message_id": 67890,
        "content_hash": "sha256_hash",
        "processed_at": "2025-09-30T10:30:00Z",
        "status": "completed",
        "kb_file": "knowledge_base/articles/2025-09-30-new-discovery.md"
      }
    ],
    "pending_groups": [
      {
        "group_id": "temp_uuid",
        "message_ids": [12346, 12347],
        "started_at": "2025-09-30T10:35:00Z"
      }
    ]
  }
  ```

**Решение**: Используем JSON файл с file locking для MVP.

### Структура проекта

```
tg-note/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
├── config/
│   ├── __init__.py
│   └── settings.py          # Конфигурация
├── src/
│   ├── __init__.py
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers.py      # Обработчики событий Telegram
│   │   └── utils.py         # Вспомогательные функции
│   ├── processor/
│   │   ├── __init__.py
│   │   ├── message_aggregator.py  # Группировка сообщений
│   │   └── content_parser.py      # Парсинг контента
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py    # Базовый класс агента
│   │   └── stub_agent.py    # Заглушка для MVP
│   ├── knowledge_base/
│   │   ├── __init__.py
│   │   ├── manager.py       # Управление KB
│   │   └── git_ops.py       # Git операции
│   └── tracker/
│       ├── __init__.py
│       └── processing_tracker.py  # Отслеживание обработки
├── data/
│   └── processed.json       # История обработки (создаётся автоматически)
├── tests/
│   ├── __init__.py
│   ├── test_tracker.py
│   ├── test_content_parser.py
│   └── test_stub_agent.py
└── main.py                  # Точка входа
```

### Конфигурация

Переменные окружения (`.env`):
```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
ALLOWED_USER_IDS=123456789,987654321

# Agent System (для будущего)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Knowledge Base
KB_PATH=./knowledge_base
KB_GIT_ENABLED=true
KB_GIT_AUTO_PUSH=true
KB_GIT_REMOTE=origin
KB_GIT_BRANCH=main

# Processing
MESSAGE_GROUP_TIMEOUT=30  # секунды
PROCESSED_LOG_PATH=./data/processed.json

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/bot.log
```

### Технологический стек

- **Python**: 3.11+
- **Telegram Bot**: pyTelegramBotAPI или aiogram
- **Agent System** (будущее): LangChain, CrewAI, или Custom
- **Git**: GitPython
- **Config**: python-dotenv
- **Data**: JSON (stdlib), filelock

### Безопасность

1. **Аутентификация**: Проверка `ALLOWED_USER_IDS`
2. **Rate limiting**: Базовое ограничение на количество сообщений
3. **Валидация входных данных**: Проверка типов сообщений
4. **Git credentials**: Использование SSH keys или tokens из env

---

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/ArtyomZemlyak/tg-note.git
cd tg-note
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить `.env`

```bash
cp .env.example .env
# Отредактировать .env и добавить токены
```

Минимально необходимые настройки:
- `TELEGRAM_BOT_TOKEN` - токен бота из @BotFather
- `ALLOWED_USER_IDS` - ID пользователей через запятую

### 5. Запустить бота

```bash
python main.py
```

### 6. Настроить базу знаний в Telegram

После запуска бота:
1. Отправьте `/start` боту
2. Настройте базу знаний одним из способов:
   - **Локальная KB**: `/setkb my-notes` - создаст новую базу знаний
   - **GitHub KB**: `/setkb https://github.com/user/knowledge-base` - клонирует существующий репозиторий
3. Проверьте настройки: `/kb`
4. Начните отправлять сообщения - они будут автоматически сохраняться в вашу базу знаний!

### 7. Запустить тесты

```bash
pytest
```

## Использование

### Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/setkb <название|github_url>` - Настроить базу знаний
  - Локальная: `/setkb my-notes`
  - GitHub: `/setkb https://github.com/user/repo`
- `/kb` - Информация о текущей базе знаний
- `/status` - Статистика обработки

### Работа с контентом

Просто отправляйте боту:
- Текстовые сообщения
- Репосты из каналов
- Фотографии с описанием
- Документы

Бот автоматически:
1. Проанализирует контент
2. Определит категорию (AI, biology, physics, tech, general)
3. Создаст структурированную заметку в Markdown
4. Сохранит в соответствующую категорию базы знаний
5. Создаст git commit (если включено)

---

## Статус реализации

### ✅ Phase 1: Базовая инфраструктура (ЗАВЕРШЕНО)
- ✅ Создана структура проекта (директории, файлы)
- ✅ Настроен `requirements.txt` с зависимостями
- ✅ Создан `.env.example` и конфигурация
- ✅ Реализован `config/settings.py` для загрузки настроек
- ✅ Настроен `.gitignore`
- ✅ Созданы базовые модули для всех компонентов
- ✅ Добавлены unit тесты

### ✅ Phase 2: Processing Tracker (ЗАВЕРШЕНО)
- ✅ Реализован `ProcessingTracker` класс
- ✅ Добавлены методы сохранения/загрузки из JSON
- ✅ Реализован file locking для concurrent access
- ✅ Добавлены методы проверки обработки по hash
- ✅ Написаны unit тесты для tracker

### ✅ Phase 3: Telegram Bot (ЗАВЕРШЕНО)
- ✅ Инициализирован Telegram bot (pyTelegramBotAPI)
- ✅ Реализованы базовые handlers (start, help, status)
- ✅ Добавлена проверка ALLOWED_USER_IDS
- ✅ Реализован прием текстовых сообщений
- ✅ Реализован прием репостов (forwarded messages)
- ✅ Добавлены уведомления о статусе обработки
- ✅ Полная async поддержка

### ✅ Phase 4: Message Processor (ЗАВЕРШЕНО)
- ✅ Реализован `MessageAggregator` для группировки сообщений
- ✅ Добавлена логика timeout для закрытия группы
- ✅ Реализован `ContentParser` для извлечения текста, ссылок
- ✅ Добавлена генерация content hash (SHA256)
- ✅ Реализована очередь обработки с background tasks

### ✅ Phase 5: Agent System Stub (ЗАВЕРШЕНО)
- ✅ Создан `BaseAgent` абстрактный класс
- ✅ Добавлен `KBStructure` для определения структуры KB
- ✅ Реализован `StubAgent` для MVP
- ✅ StubAgent форматирует текст в базовый Markdown
- ✅ Агент определяет категорию контента автоматически
- ✅ Placeholder для будущей интеграции LLM готов

### ✅ Phase 6: Knowledge Base Manager (ЗАВЕРШЕНО)
- ✅ Реализован `KnowledgeBaseManager` класс
- ✅ Добавлено создание .md файлов с метаданными
- ✅ Структура определяется агентной системой
- ✅ Добавлена генерация имен файлов (YYYY-MM-DD-title.md)
- ✅ Реализовано обновление index.md
- ✅ Поддержка категорий, подкатегорий и тегов

### ✅ Phase 7: Git Integration (ЗАВЕРШЕНО)
- ✅ Добавлен GitPython в зависимости
- ✅ Реализован `GitOperations` класс
- ✅ Добавлены методы: add, commit, push
- ✅ Добавлена проверка git credentials
- ✅ Реализован error handling для git операций
- ✅ Добавлена опциональность git (KB_GIT_ENABLED)

### ✅ Phase 8: Integration & Main Loop (ЗАВЕРШЕНО)
- ✅ Создан `main.py` с точкой входа
- ✅ Интегрированы все компоненты
- ✅ Реализован полный workflow: прием → группировка → обработка → сохранение
- ✅ Добавлен graceful shutdown
- ✅ Добавлено полное логирование

### ✅ Phase 9: Repository Management (НОВОЕ - ЗАВЕРШЕНО)
- ✅ Реализован `RepositoryManager` для управления KB
- ✅ Поддержка локальных баз знаний
- ✅ Поддержка GitHub репозиториев (clone/pull)
- ✅ Реализован `UserSettings` для персональных настроек
- ✅ Команды `/setkb`, `/kb` для управления KB
- ✅ Каждый пользователь может иметь свою KB
- ✅ Автоматическая инициализация git для локальных KB

---

## TODO

### Следующие шаги

1. **Интеграция Telegram Bot**
   - Выбрать между pyTelegramBotAPI vs aiogram
   - Реализовать базовые обработчики команд
   - Добавить обработку сообщений и репостов

2. **Завершение основного workflow**
   - Связать все компоненты вместе
   - Реализовать цикл: прием → группировка → обработка → сохранение
   - Добавить обработку ошибок

3. **Тестирование**
   - Интеграционные тесты
   - Тестирование с реальным Telegram ботом
   - Проверка группировки сообщений

### Future Enhancements (после MVP)
- [ ] Интеграция с LangChain/CrewAI
- [ ] Добавить обработку изображений
- [ ] Добавить обработку PDF файлов
- [ ] Реализовать веб-интерфейс для просмотра KB
- [ ] Добавить PostgreSQL вместо JSON
- [ ] Добавить систему backup
- [ ] Реализовать поиск по базе знаний
- [ ] Добавить метрики и мониторинг
- [ ] Добавить CI/CD pipeline
- [ ] Реализовать векторное хранилище для semantic search

---

## Лицензия

MIT License - см. LICENSE файл

## Контрибуция

Проект в активной разработке. Pull requests приветствуются!