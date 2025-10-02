# Pull Request: Архитектура и TODO для MVP версии бота

## 🔗 Ссылка для создания PR
Перейдите по ссылке для создания Pull Request:
```
https://github.com/ArtyomZemlyak/tg-note/pull/new/arch-init-v0
```

## 📋 Заголовок PR
```
Архитектура и TODO для MVP версии бота
```

## 📝 Описание для PR

```markdown
## Описание

Добавлена подробная архитектура минимальной версии Telegram бота для создания заметок в базе знаний.

## Что включено

### Архитектура
- 📐 Общая схема компонентов с ASCII диаграммой
- 🔧 Детальное описание 5 основных компонентов:
  - **Telegram Bot Layer** - прием и фильтрация сообщений
  - **Message Processor** - группировка и агрегация контента
  - **Agent System** (заглушка для MVP) - анализ и обработка
  - **Knowledge Base Manager** - управление .md файлами
  - **Processing Tracker** - отслеживание обработанных сообщений
- 📊 Workflow обработки сообщений (прием → группировка → обработка → сохранение)
- 📁 Полная структура проекта с описанием каждой директории
- ⚙️ Технологический стек и конфигурация (env переменные)
- 🔒 Базовые меры безопасности

### Анализ хранения данных
Проведен детальный анализ **4 вариантов** хранения информации об обработанных сообщениях:

1. ✅ **JSON файл** (рекомендовано)
   - Простота реализации
   - Не требует дополнительных зависимостей
   - Легко читать и редактировать
   - Достаточно надежно для 2-3 пользователей

2. **SQLite**
   - ACID гарантии, но избыточно для MVP

3. **CONTENT.md**
   - Максимально просто, но нет структуры для метаданных

4. **PostgreSQL/MySQL**
   - Излишне сложно для начальной версии

**Решение**: JSON с file locking для обеспечения thread-safety

### TODO List
Подробный план разработки разбитый на **10 фаз** (~4 недели):

1. **Phase 1**: Базовая инфраструктура (структура проекта, requirements, config)
2. **Phase 2**: Processing Tracker (JSON хранилище с file locking)
3. **Phase 3**: Telegram Bot (handlers, authentication)
4. **Phase 4**: Message Processor (группировка, парсинг контента)
5. **Phase 5**: Agent System Stub (заглушка с базовым форматированием)
6. **Phase 6**: Knowledge Base Manager (создание .md файлов)
7. **Phase 7**: Git Integration (add, commit, push)
8. **Phase 8**: Integration & Main Loop (сборка всех компонентов)
9. **Phase 9**: Testing & Documentation (тесты, документация)
10. **Phase 10**: Deployment (настройка на сервере)

**+ Future Enhancements**: список улучшений для развития после MVP (LLM интеграция, веб-интерфейс, векторный поиск, и т.д.)

## Технологии
- **Python** 3.11+
- **Telegram**: pyTelegramBotAPI/aiogram
- **Git**: GitPython
- **Storage**: JSON + filelock
- **Future**: LangChain/CrewAI для агентной системы

## Структура проекта
```
tg-note/
├── src/
│   ├── bot/              # Telegram bot handlers
│   ├── processor/        # Message aggregation & parsing
│   ├── agents/           # Agent system (stub for MVP)
│   ├── knowledge_base/   # KB management & git ops
│   └── tracker/          # Processing history tracker
├── knowledge_base/       # .md files (git submodule опционально)
├── data/
│   └── processed.json    # Processing history
└── config/               # Configuration & settings
```

## Следующие шаги
После мержа можно начинать реализацию:
1. Phase 1: Создание структуры проекта
2. Phase 2: Реализация Processing Tracker
3. Phase 3: Базовый Telegram bot с аутентификацией

## Вопросы для обсуждения
- Выбор между pyTelegramBotAPI vs aiogram?
- Использовать git submodule для knowledge_base/?
- Deployment: Docker или systemd service?
```

## ✅ Что сделано

1. ✅ Создана ветка `arch-init-v0`
2. ✅ Разработана архитектура MVP версии
3. ✅ Проанализированы варианты хранения данных
4. ✅ Создан детальный TODO list на 10 фаз
5. ✅ Ветка запушена в удаленный репозиторий
6. ✅ Добавлен PR template для будущих PR

## 🚀 Инструкция по созданию PR

1. Откройте браузер и перейдите по ссылке:
   ```
   https://github.com/ArtyomZemlyak/tg-note/pull/new/arch-init-v0
   ```

2. Скопируйте заголовок из раздела выше

3. Скопируйте описание из раздела выше в поле описания PR

4. Нажмите "Create Pull Request"

## 📊 Статистика изменений

- **Файлы изменены**: 2
  - `README.md` - полная переработка (~400 строк)
  - `.github/pull_request_template.md` - новый файл
  
- **Коммиты**: 2
  - "Add architecture and TODO for MVP version"
  - "Add PR template"

---

**Ветка**: `arch-init-v0`  
**Base**: `main`  
**Status**: Готово к review ✅