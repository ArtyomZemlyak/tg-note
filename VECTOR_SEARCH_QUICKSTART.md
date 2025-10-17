# Быстрый запуск с векторным поиском

Краткая инструкция по запуску системы с поддержкой семантического векторного поиска.

## Что это дает?

- 🔍 **Семантический поиск**: поиск по смыслу, а не по ключевым словам
- 🚀 **Автоматическая индексация**: база знаний автоматически векторизуется
- 🎯 **Точные результаты**: находит релевантные документы даже без точного совпадения слов
- 🌐 **Мультиязычность**: поддержка русского и английского языков

## Архитектура

```
Bot → MCP Hub → Infinity (эмбеддинги) → Qdrant (векторная БД)
```

## Быстрый старт

### 1. Подготовка файлов

```bash
# Скопировать примеры конфигурации
cp .env.vector.example .env
cp config.example.yaml config.yaml

# Создать директории для данных
mkdir -p data/qdrant_storage data/infinity_cache
```

### 2. Настроить .env

Отредактировать `.env`, минимально нужно указать:

```env
# Ваш Telegram бот токен
TELEGRAM_BOT_TOKEN=your_bot_token_here

# ID разрешенных пользователей
ALLOWED_USER_IDS=123456789

# Модель для эмбеддингов (для русского + английского)
INFINITY_MODEL=BAAI/bge-m3
```

### 3. Настроить config.yaml

Включить векторный поиск в `config.yaml`:

```yaml
# Включить векторный поиск
VECTOR_SEARCH_ENABLED: true

# Настройки эмбеддингов
VECTOR_EMBEDDING_PROVIDER: infinity
VECTOR_EMBEDDING_MODEL: BAAI/bge-m3
VECTOR_INFINITY_API_URL: http://infinity:7997

# Настройки Qdrant
VECTOR_STORE_PROVIDER: qdrant
VECTOR_QDRANT_URL: http://qdrant:6333
VECTOR_QDRANT_COLLECTION: knowledge_base
```

### 4. Запустить

```bash
# Запустить все сервисы
docker-compose -f docker-compose.vector.yml up -d

# Посмотреть логи (дождаться загрузки модели ~1-2 минуты)
docker-compose -f docker-compose.vector.yml logs -f infinity
```

### 5. Проверить работу

```bash
# Проверить статус всех сервисов
docker-compose -f docker-compose.vector.yml ps

# Должны быть запущены:
# - tg-note-qdrant (healthy)
# - tg-note-infinity (healthy)
# - tg-note-hub (healthy)
# - tg-note-bot (running)
```

## Использование

### Через Telegram бота

1. Отправьте документы боту (текст, PDF, DOCX и т.д.)
2. Бот автоматически их проиндексирует
3. Задавайте вопросы - бот будет использовать семантический поиск

### Пример

```
👤 Пользователь: Как работают трансформеры в NLP?

🤖 Бот: [находит релевантные разделы в базе знаний используя векторный поиск]
```

## Выбор модели

### Для русского + английского (рекомендуется)

```env
INFINITY_MODEL=BAAI/bge-m3
```

### Только для английского (быстрее)

```env
INFINITY_MODEL=BAAI/bge-small-en-v1.5
```

### Другие варианты

| Модель | Языки | Качество | Скорость |
|--------|-------|----------|----------|
| `BAAI/bge-m3` | Мультиязычная | ⭐⭐⭐⭐⭐ | ⚡⚡ |
| `BAAI/bge-small-en-v1.5` | English | ⭐⭐⭐⭐ | ⚡⚡⚡ |
| `BAAI/bge-base-en-v1.5` | English | ⭐⭐⭐⭐⭐ | ⚡⚡ |

## Управление

### Просмотр логов

```bash
# Все логи
docker-compose -f docker-compose.vector.yml logs -f

# Только конкретный сервис
docker-compose -f docker-compose.vector.yml logs -f infinity
```

### Перезапуск

```bash
# Перезапустить все
docker-compose -f docker-compose.vector.yml restart

# Перезапустить конкретный сервис
docker-compose -f docker-compose.vector.yml restart infinity
```

### Остановка

```bash
# Остановить все сервисы
docker-compose -f docker-compose.vector.yml down

# Остановить и удалить данные (будьте осторожны!)
docker-compose -f docker-compose.vector.yml down -v
```

## Требования к ресурсам

### Минимальные требования

- **RAM**: 4 GB (с моделью `bge-small`)
- **Диск**: 5 GB (для моделей и данных)
- **CPU**: 2 ядра

### Рекомендуемые требования

- **RAM**: 8 GB (с моделью `bge-m3`)
- **Диск**: 10 GB
- **CPU**: 4 ядра
- **GPU** (опционально): Ускоряет обработку в 5-10 раз

## GPU ускорение (опционально)

Для ускорения обработки раскомментируйте в `docker-compose.vector.yml`:

```yaml
infinity:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Требования:
- NVIDIA GPU
- nvidia-docker установлен

## Проблемы и решения

### Infinity не запускается

**Проблема**: Контейнер infinity перезапускается

**Решение**: Проверьте логи и дайте время на загрузку модели (1-2 минуты)

```bash
docker-compose -f docker-compose.vector.yml logs infinity
```

### Недостаточно памяти

**Проблема**: Out of memory

**Решение**: Используйте меньшую модель

```env
INFINITY_MODEL=BAAI/bge-small-en-v1.5
INFINITY_BATCH_SIZE=16
```

### Vector search not available

**Проблема**: "Vector search is not available"

**Решение**: Проверьте config.yaml

```yaml
VECTOR_SEARCH_ENABLED: true
```

## Дополнительная документация

Полная документация: [docs_site/deployment/docker-vector-search.md](docs_site/deployment/docker-vector-search.md)

## Логика работы

1. **Bot** получает документ от пользователя
2. **Bot** вызывает `reindex_vector` через MCP Hub
3. **MCP Hub** отправляет текст в **Infinity** для создания эмбеддингов
4. **MCP Hub** сохраняет векторы в **Qdrant**
5. При поиске **Bot** вызывает `vector_search`
6. **MCP Hub** получает эмбеддинг запроса от **Infinity**
7. **MCP Hub** ищет похожие векторы в **Qdrant**
8. **Bot** получает релевантные результаты

Каждая база знаний пользователя → отдельная коллекция в Qdrant.

## AICODE-NOTE

- Bot управляет логикой векторизации (когда индексировать, когда искать)
- MCP Hub предоставляет инструменты (vector_search, reindex_vector)
- Infinity генерирует эмбеддинги (преобразует текст в векторы)
- Qdrant хранит векторы (отдельная коллекция на каждую базу знаний)
