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

**Альтернативные варианты хранения**:

1. **JSON файл** (рекомендуется для MVP) ✅
   - ➕ Простота реализации
   - ➕ Не требует дополнительных зависимостей
   - ➕ Легко читать и редактировать вручную
   - ➕ Достаточно надежно для 2-3 пользователей
   - ➖ Может быть проблема с concurrent access (решается file locking)

2. **SQLite**
   - ➕ ACID гарантии
   - ➕ Удобные запросы
   - ➕ Лучше для масштабирования
   - ➖ Дополнительная зависимость
   - ➖ Излишне для минимальной версии

3. **CONTENT.md файл**
   - ➕ Максимально просто
   - ➕ Человекочитаемый формат
   - ➖ Сложно парсить
   - ➖ Нет структуры для метаданных
   - ➖ Медленный поиск

4. **PostgreSQL/MySQL**
   - ➖ Избыточно для MVP
   - ➖ Требует развертывания и настройки

**Решение**: Используем JSON файл с file locking для MVP.

### Workflow обработки сообщений

1. **Прием сообщения**
   ```
   User → Bot → Check if processed (hash check)
   ```

2. **Группировка**
   ```
   Если следующее сообщение приходит < 30 секунд
   → Добавить в группу
   Иначе
   → Закрыть группу и отправить на обработку
   ```

3. **Обработка**
   ```
   Message Group → Agent System → Analysis → KB Entry
   ```

4. **Сохранение**
   ```
   KB Entry → Git commit → Update processed.json → Notify user
   ```

### Структура проекта

```
tg-note/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── config/
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
├── knowledge_base/          # База знаний (может быть git submodule)
│   ├── topics/
│   ├── articles/
│   └── index.md
├── data/
│   └── processed.json       # История обработки
├── tests/
│   └── ...
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

### Ограничения MVP

1. Нет веб-интерфейса
2. Нет БД (только JSON)
3. Агентная система - заглушка
4. Нет продвинутой обработки медиа
5. Нет backup системы
6. Минимальное логирование
7. Нет метрик и мониторинга

---

## TODO

### Phase 1: Базовая инфраструктура (неделя 1)
- [ ] Создать структуру проекта (директории, файлы)
- [ ] Настроить `requirements.txt` с зависимостями
- [ ] Создать `.env.example` и конфигурацию
- [ ] Реализовать `config/settings.py` для загрузки настроек
- [ ] Настроить `.gitignore`
- [ ] Создать базовую структуру knowledge_base/

### Phase 2: Processing Tracker (неделя 1)
- [ ] Реализовать `ProcessingTracker` класс
- [ ] Добавить методы сохранения/загрузки из JSON
- [ ] Реализовать file locking для concurrent access
- [ ] Добавить методы проверки обработки по hash
- [ ] Написать unit тесты для tracker

### Phase 3: Telegram Bot (неделя 1-2)
- [ ] Инициализировать Telegram bot (выбрать библиотеку)
- [ ] Реализовать базовые handlers (start, help)
- [ ] Добавить проверку ALLOWED_USER_IDS
- [ ] Реализовать прием текстовых сообщений
- [ ] Реализовать прием репостов (forwarded messages)
- [ ] Добавить уведомления о статусе обработки

### Phase 4: Message Processor (неделя 2)
- [ ] Реализовать `MessageAggregator` для группировки сообщений
- [ ] Добавить логику timeout для закрытия группы
- [ ] Реализовать `ContentParser` для извлечения текста, ссылок
- [ ] Добавить генерацию content hash (SHA256)
- [ ] Реализовать очередь обработки (in-memory)

### Phase 5: Agent System Stub (неделя 2)
- [ ] Создать `BaseAgent` абстрактный класс
- [ ] Реализовать `StubAgent` для MVP
- [ ] StubAgent должен форматировать текст в базовый Markdown
- [ ] Добавить placeholder для будущей интеграции LLM

### Phase 6: Knowledge Base Manager (неделя 2-3)
- [ ] Реализовать `KnowledgeBaseManager` класс
- [ ] Добавить создание .md файлов с метаданными
- [ ] Реализовать структуру директорий (topics, articles)
- [ ] Добавить генерацию имен файлов (YYYY-MM-DD-title.md)
- [ ] Реализовать обновление index.md

### Phase 7: Git Integration (неделя 3)
- [ ] Добавить GitPython в зависимости
- [ ] Реализовать `GitOperations` класс
- [ ] Добавить методы: add, commit, push
- [ ] Добавить проверку git credentials
- [ ] Реализовать error handling для git операций
- [ ] Добавить опциональность git (KB_GIT_ENABLED)

### Phase 8: Integration & Main Loop (неделя 3)
- [ ] Создать `main.py` с точкой входа
- [ ] Интегрировать все компоненты
- [ ] Реализовать основной workflow: прием → группировка → обработка → сохранение
- [ ] Добавить graceful shutdown
- [ ] Добавить базовое логирование

### Phase 9: Testing & Documentation (неделя 4)
- [ ] Написать интеграционные тесты
- [ ] Протестировать с реальным Telegram ботом
- [ ] Протестировать группировку multi-message контента
- [ ] Протестировать git operations
- [ ] Обновить README с инструкциями по запуску
- [ ] Создать документацию API компонентов

### Phase 10: Deployment (неделя 4)
- [ ] Выбрать метод деployмента (VPS, Docker, etc.)
- [ ] Создать deployment скрипты
- [ ] Настроить systemd service или Docker compose
- [ ] Настроить git credentials на сервере
- [ ] Провести финальное тестирование

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

## Быстрый старт (после реализации)

1. Клонировать репозиторий:
```bash
git clone https://github.com/ArtyomZemlyak/tg-note.git
cd tg-note
```

2. Создать виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows
```

3. Установить зависимости:
```bash
pip install -r requirements.txt
```

4. Настроить `.env`:
```bash
cp .env.example .env
# Отредактировать .env и добавить токены
```

5. Запустить бота:
```bash
python main.py
```

## Лицензия

MIT License - см. LICENSE файл

## Контрибуция

Проект в активной разработке. Pull requests приветствуются!