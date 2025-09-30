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

### 2. Создайте виртуальное окружение
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows
```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

---

## ⚙️ Настройка

### 1. Создайте файл конфигурации
```bash
cp .env.example .env
```

### 2. Получите Telegram Bot Token
1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

### 3. Получите свой User ID
1. Откройте [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте любое сообщение
3. Скопируйте свой ID

### 4. Отредактируйте .env
```bash
nano .env  # или любой другой редактор
```

Минимальная конфигурация:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=your_user_id_here
KB_PATH=/path/to/your/knowledge_base_repo
```

### 5. Настройте Knowledge Base репозиторий
```bash
# Клонируйте или создайте отдельный репозиторий для базы знаний
git clone https://github.com/your/knowledge-base.git

# Укажите путь в .env
KB_PATH=/path/to/knowledge-base
```

---

## 🏃 Запуск

### Запустить бота
```bash
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
pytest
```

### Тесты с покрытием
```bash
pytest --cov=src --cov-report=html
```

### Запустить конкретный тест
```bash
pytest tests/test_tracker.py -v
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
python -c "from config import settings; print(settings)"

# Посмотреть статистику обработки
python -c "from src.tracker.processing_tracker import ProcessingTracker; t = ProcessingTracker('./data/processed.json'); print(t.get_stats())"

# Запустить конкретный модуль
python -m pytest tests/test_tracker.py -v

# Форматировать код
black src/ tests/

# Проверить типы
mypy src/
```

---

## 🐛 Troubleshooting

### Ошибка: "TELEGRAM_BOT_TOKEN is required"
→ Добавьте токен в `.env` файл

### Ошибка: "Not a git repository"
→ Проверьте `KB_PATH` в `.env`, путь должен быть git репозиторием

### Ошибка: "ModuleNotFoundError"
→ Активируйте виртуальное окружение: `source venv/bin/activate`

### Тесты не запускаются
→ Установите dev зависимости: `pip install -r requirements.txt`

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