# 🚀 Быстрый старт tg-note

## ✅ Phase 1 реализована!

База проекта готова. Вот что нужно сделать для запуска:

---

## 📦 Установка

### 1. Клонируйте репозиторий (если ещё не сделали)
```bash
git clone https://github.com/ArtyomZemlyak/tg-note.git
cd tg-note
```

### 2. Установите Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
# или используя pipx:
# pipx install poetry
```

### 3. Установите зависимости
```bash
poetry install
```

Poetry автоматически создаст виртуальное окружение и установит все зависимости.

---

## ⚙️ Настройка

### 1. Создайте файлы конфигурации

**config.yaml** (для основных настроек):
```bash
cp config.example.yaml config.yaml
```

**.env** (для credentials):
```bash
cp .env.example .env  # если есть .env.example
# или создайте новый .env файл
```

### 2. Получите Telegram Bot Token
1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

### 3. Получите свой User ID (опционально)
1. Откройте [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте любое сообщение
3. Скопируйте свой ID

### 4. Настройте config.yaml (основные настройки)
```bash
nano config.yaml  # или любой другой редактор
```

```yaml
# Knowledge Base Settings
KB_PATH: ./knowledge_base  # или путь к вашему KB репозиторию
KB_GIT_ENABLED: true
KB_GIT_AUTO_PUSH: true

# Processing Settings
MESSAGE_GROUP_TIMEOUT: 30

# Logging Settings
LOG_LEVEL: INFO
LOG_FILE: ./logs/bot.log

# User Access Control (опционально)
ALLOWED_USER_IDS: ""  # пусто = все пользователи разрешены
```

### 5. Настройте .env (credentials)
```bash
nano .env  # или любой другой редактор
```

**Обязательно:**
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

**Опционально:**
```env
# API ключи для будущих агентов
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Переопределение настроек из config.yaml (если нужно)
# LOG_LEVEL=DEBUG
# MESSAGE_GROUP_TIMEOUT=60
```

### 6. Настройте Knowledge Base репозиторий
```bash
# Клонируйте или создайте отдельный репозиторий для базы знаний
git clone https://github.com/your/knowledge-base.git

# Укажите путь в config.yaml
KB_PATH: /path/to/knowledge-base
```

**💡 Подсказка по приоритету настроек:**
- **ENV переменные** > **.env файл** > **config.yaml**
- Храните чувствительные данные в `.env`, остальное в `config.yaml`
- См. [YAML_CONFIGURATION.md](YAML_CONFIGURATION.md) для деталей

---

## 🏃 Запуск

### Запустить бота
```bash
poetry run python main.py
# или активируйте окружение Poetry:
poetry shell
python main.py
```

Вы должны увидеть:
```
INFO - Starting tg-note bot...
INFO - Configuration validated successfully
INFO - Processing tracker initialized: ./data/processed.json
INFO - Knowledge base manager initialized: ./knowledge_base
INFO - Git operations initialized (enabled: True)
INFO - Bot initialization completed (stub mode)
INFO - Press Ctrl+C to stop
```

### Остановить бота
Нажмите `Ctrl+C`

---

## 🧪 Тестирование

### Запустить все тесты
```bash
poetry run pytest
```

### Тесты с покрытием
```bash
poetry run pytest --cov=src --cov-report=html
```

### Запустить конкретный тест
```bash
poetry run pytest tests/test_tracker.py -v
```

---

## 📁 Структура проекта

```
tg-note/
├── config/              ← Конфигурация
├── src/
│   ├── bot/            ← Telegram бот (TODO)
│   ├── processor/      ← Обработка сообщений ✅
│   ├── agents/         ← AI агенты (заглушка) ✅
│   ├── knowledge_base/ ← Управление базой знаний ✅
│   └── tracker/        ← Отслеживание обработки ✅
├── tests/              ← Unit тесты
├── data/               ← JSON хранилище (создаётся автоматически)
├── logs/               ← Логи
└── main.py            ← Точка входа
```

---

## ⚠️ Текущие ограничения

**Phase 1 завершена**, но для полноценной работы нужна **Phase 2-3**:

- ❌ Telegram bot handlers не реализованы (скелет готов)
- ❌ Нет интеграции компонентов в основной цикл
- ❌ Agent system - простая заглушка (без LLM)

**Можно протестировать**:
- ✅ Конфигурацию (валидация)
- ✅ Processing Tracker (JSON хранилище)
- ✅ Content Parser (извлечение текста, URLs, хеши)
- ✅ Message Aggregator (группировка сообщений)
- ✅ Stub Agent (базовое форматирование)
- ✅ KB Manager (создание .md файлов)
- ✅ Git Operations (add, commit, push)

---

## 📚 Документация

- **README.md** - полное описание проекта и архитектуры
- **PHASE1_IMPLEMENTATION.md** - детальный отчёт о Phase 1
- **.env.example** - все доступные настройки
- **Inline комментарии** - в каждом модуле

---

## 🔧 Полезные команды

```bash
# Проверить конфигурацию
poetry run python -c "from config import settings; print(settings)"

# Посмотреть статистику обработки
poetry run python -c "from src.tracker.processing_tracker import ProcessingTracker; t = ProcessingTracker('./data/processed.json'); print(t.get_stats())"

# Запустить конкретный модуль
poetry run pytest tests/test_tracker.py -v

# Форматировать код
poetry run black src/ tests/

# Проверить типы
poetry run mypy src/
```

---

## 🐛 Troubleshooting

### Ошибка: "TELEGRAM_BOT_TOKEN is required"
→ Добавьте токен в `.env` файл

### Ошибка: "Not a git repository"
→ Проверьте `KB_PATH` в `.env`, путь должен быть git репозиторием

### Ошибка: "ModuleNotFoundError"
→ Активируйте виртуальное окружение Poetry: `poetry shell`

### Тесты не запускаются
→ Установите зависимости: `poetry install`

---

## 📞 Поддержка

- 📖 Читайте **README.md** для деталей архитектуры
- 📝 Смотрите **PHASE1_IMPLEMENTATION.md** для технических деталей
- 🐛 Issues: [GitHub Issues](https://github.com/ArtyomZemlyak/tg-note/issues)

---

## 🎯 Следующие шаги

После завершения **Phase 2-3**, бот будет готов к использованию:

1. **Phase 2**: Реализация Telegram bot handlers
2. **Phase 3**: Интеграция всех компонентов
3. **Phase 4**: Тестирование с реальным ботом
4. **Phase 5**: Deployment

---

**Статус**: Phase 1 ✅ | Phase 2-3 ⏳ | Production ❌

Удачи! 🚀