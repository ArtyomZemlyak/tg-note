# Рефакторинг: Структура базы знаний задаётся агентной системой

## Обзор

Проведён рефакторинг системы для того, чтобы структура базы знаний (категории, подкатегории, теги, расположение файлов) определялась агентной системой на основе анализа контента, а не была жёстко закодирована в коде.

## Ключевые изменения

### 1. Расширена агентная система

#### `src/agents/base_agent.py`
- Добавлен класс `KBStructure` для определения структуры KB:
  - `category` - основная категория (ai, biology, physics, tech, general)
  - `subcategory` - опциональная подкатегория (machine-learning, genetics, etc.)
  - `tags` - список тегов для контента
  - `custom_path` - опциональный пользовательский путь
- Метод `get_relative_path()` генерирует относительный путь на основе структуры
- `BaseAgent.process()` теперь возвращает `kb_structure` в результате

#### `src/agents/stub_agent.py`
- Добавлен метод `_determine_kb_structure()` для определения структуры на основе ключевых слов
- Простая эвристика для MVP:
  - AI-темы → `topics/ai/machine-learning/`
  - Biology → `topics/biology/`
  - Physics → `topics/physics/`
  - Programming → `topics/tech/programming/`
  - Остальное → `topics/general/`

### 2. Система управления репозиториями

#### `src/knowledge_base/repository.py`
Новый модуль для управления локальными и GitHub репозиториями:

**Основные функции:**
- `init_local_kb(kb_name)` - создание локальной базы знаний с git
- `clone_github_kb(github_url, kb_name, credentials)` - клонирование репозитория из GitHub
- `pull_updates(kb_path)` - обновление локальной копии из remote
- `get_kb_path(kb_name)` - получение пути к существующей KB
- `list_knowledge_bases()` - список всех доступных KB

**Структура хранения:**
```
./knowledge_bases/
  ├── my-notes/          # Локальная KB
  │   ├── .git/
  │   ├── topics/
  │   └── README.md
  └── github-kb/         # Склонированная из GitHub
      ├── .git/
      ├── topics/
      └── README.md
```

#### `src/knowledge_base/user_settings.py`
Новый модуль для хранения настроек пользователей:

**Формат данных:**
```json
{
  "user_id": {
    "kb_name": "my-notes",
    "kb_type": "local" | "github",
    "github_url": "https://github.com/user/repo",
    "has_credentials": false
  }
}
```

**Функции:**
- `get_user_kb(user_id)` - получить настройки KB пользователя
- `set_user_kb(user_id, kb_name, kb_type, ...)` - установить KB для пользователя
- `remove_user_kb(user_id)` - удалить настройки

### 3. Обновлён KnowledgeBaseManager

#### `src/knowledge_base/manager.py`
- `create_article()` теперь принимает `KBStructure` вместо `category`
- Путь к статье определяется агентом через `kb_structure.get_relative_path()`
- Frontmatter включает:
  - `category` и `subcategory`
  - `tags` в виде массива
  - `created_at`
  - кастомные метаданные
- `update_index()` добавляет информацию о категории в индекс

**Пример структуры файла:**
```markdown
---
title: Machine Learning Basics
category: ai
subcategory: machine-learning
tags: [ai, ml, neural-networks]
created_at: 2025-10-02T10:30:00
---

# Содержимое статьи...
```

### 4. Telegram Bot команды

#### Новые команды:

**`/setkb <название|github_url>`**
- Настройка базы знаний для пользователя
- Локальная: `/setkb my-notes` - создаёт новую KB с git
- GitHub: `/setkb https://github.com/user/repo` - клонирует репозиторий

**`/kb`**
- Информация о текущей базе знаний пользователя
- Показывает: название, тип, GitHub URL, локальный путь

**Обновлённые команды:**

**`/status`**
- Добавлена информация о настроенной KB пользователя

#### `src/bot/handlers.py`
- `BotHandlers` теперь принимает `RepositoryManager` и `UserSettings`
- `_process_message_group()` обновлён:
  1. Проверяет, настроена ли KB для пользователя
  2. Получает путь к KB пользователя
  3. Создаёт KBManager для конкретной KB
  4. Использует `kb_structure` от агента для сохранения
  5. Показывает категорию и теги в уведомлении

### 5. Обновлены зависимости

#### `main.py`
- Инициализирует `RepositoryManager` и `UserSettings`
- Передаёт их в `TelegramBot`

#### `src/bot/telegram_bot.py`
- Конструктор принимает `RepositoryManager` и `UserSettings` вместо `KnowledgeBaseManager`

## Workflow

### Настройка базы знаний:

1. **Локальная KB:**
   ```
   Пользователь → /setkb my-notes
   Bot → создаёт ./knowledge_bases/my-notes/
       → инициализирует git
       → создаёт структуру (topics/, README.md)
       → сохраняет настройки пользователя
   ```

2. **GitHub KB:**
   ```
   Пользователь → /setkb https://github.com/user/kb
   Bot → клонирует репозиторий в ./knowledge_bases/kb/
       → сохраняет настройки пользователя
   ```

### Обработка сообщения:

```
Сообщение → Парсинг → Агент
                        ↓
                    Анализирует контент
                        ↓
                    Определяет:
                    - category (ai)
                    - subcategory (machine-learning)
                    - tags ([ai, ml])
                        ↓
                    KBStructure
                        ↓
KBManager → Создаёт файл по пути:
            ./knowledge_bases/user-kb/topics/ai/machine-learning/2025-10-02-title.md
                        ↓
                    Git commit & push
```

## Преимущества

1. **Гибкость структуры** - агент может создавать любую структуру на лету
2. **Персональные KB** - каждый пользователь может иметь свою базу знаний
3. **GitHub интеграция** - легко работать с существующими репозиториями
4. **Масштабируемость** - легко добавить новые категории без изменения кода
5. **Семантическая организация** - контент организуется по смыслу, а не по шаблону

## Будущие улучшения

1. **LLM агенты** - использовать GPT/Claude для умной категоризации
2. **Иерархические категории** - поддержка глубокой вложенности
3. **Автоматические теги** - извлечение тегов из контента
4. **Связи между статьями** - автоматическое создание внутренних ссылок
5. **GitHub credentials** - безопасное хранение токенов для push
6. **Pull requests** - создание PR вместо прямого push
7. **Множественные KB** - поддержка нескольких KB для одного пользователя

## Тестирование

### Проверка импортов:
```bash
python3 -c "from src.agents.stub_agent import StubAgent; print('OK')"
python3 -c "from src.knowledge_base.repository import RepositoryManager; print('OK')"
python3 -c "from src.knowledge_base.user_settings import UserSettings; print('OK')"
```

### Проверка синтаксиса:
```bash
python3 -m py_compile src/knowledge_base/repository.py
python3 -m py_compile src/knowledge_base/user_settings.py
python3 -m py_compile src/agents/base_agent.py
python3 -m py_compile src/agents/stub_agent.py
```

### Тестирование workflow:
1. Запустить бота: `python3 main.py`
2. Настроить KB: `/setkb test-kb`
3. Отправить сообщение с контентом
4. Проверить созданную структуру в `./knowledge_bases/test-kb/topics/`

## Файлы изменены

### Новые файлы:
- `src/knowledge_base/repository.py` - управление репозиториями
- `src/knowledge_base/user_settings.py` - настройки пользователей
- `AGENT_KB_REFACTORING.md` - эта документация

### Изменённые файлы:
- `src/agents/base_agent.py` - добавлен KBStructure
- `src/agents/stub_agent.py` - определение структуры KB
- `src/knowledge_base/manager.py` - использование KBStructure
- `src/bot/handlers.py` - команды /setkb, /kb и новый workflow
- `src/bot/telegram_bot.py` - обновлённый конструктор
- `main.py` - инициализация новых компонентов
- `src/knowledge_base/__init__.py` - экспорт новых классов
- `src/agents/__init__.py` - экспорт KBStructure

## Совместимость

- Старые KB структуры всё ещё работают
- Можно мигрировать существующую KB через `/setkb`
- Все существующие настройки в config.yaml поддерживаются
- Git операции остаются опциональными (KB_GIT_ENABLED)
