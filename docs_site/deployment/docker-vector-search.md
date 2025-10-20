# Docker Compose с векторным поиском

Эта конфигурация добавляет возможности семантического поиска в базу знаний с использованием Qdrant (векторная БД) и Infinity (сервис эмбеддингов).

## Архитектура

```
┌─────────────────┐
│  Telegram Bot   │
│  (tg-note-bot)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│   MCP Hub       │─────▶│   Infinity   │
│  (tg-note-hub)  │      │  (embeddings)│
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│    Qdrant       │
│ (vector store)  │
└─────────────────┘
```

## Компоненты

### 1. Qdrant
**Векторная база данных** для хранения и поиска векторных представлений текста.

- **Image**: `qdrant/qdrant:latest`
- **Порты**: 6333 (HTTP API), 6334 (gRPC API)
- **Хранилище**: `./data/qdrant_storage`
- **Функции**:
  - Хранение векторных эмбеддингов
  - Быстрый поиск по семантическому сходству
  - Фильтрация по метаданным
  - Поддержка коллекций (по одной на каждую базу знаний)

### 2. Infinity
**Сервис генерации эмбеддингов** на основе трансформерных моделей.

- **Image**: `michaelf34/infinity:latest`
- **Порт**: 7997
- **Хранилище**: `./data/infinity_cache` (кеш моделей)
- **Функции**:
  - Преобразование текста в векторные представления
  - Поддержка различных моделей HuggingFace
  - Батчинг для ускорения обработки
  - Опциональная поддержка GPU

### 3. MCP Hub
**Центральный шлюз** с инструментами векторного поиска.

- **Инструменты**:
  - `vector_search` - семантический поиск по базе знаний
  - `reindex_vector` - переиндексация базы знаний
- **Логика**:
  - Получает запросы от бота
  - Создает эмбеддинги через Infinity
  - Выполняет поиск в Qdrant
  - Возвращает релевантные результаты

### 4. Telegram Bot
**Telegram бот** управляет процессом векторизации.

- **Логика**:
  - Решает, когда запускать индексацию
  - Определяет момент обновления индекса
  - Выполняет поиск через MCP инструменты
  - Каждая база знаний -> отдельная коллекция в Qdrant

## Быстрый старт

### 1. Подготовка

```bash
# Создайте директории для данных
mkdir -p data/qdrant_storage data/infinity_cache data/vector_index

# Скопируйте файл конфигурации
cp config.example.yaml config.yaml
```

### 2. Настройка переменных окружения

Создайте или обновите `.env` файл:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=123456789

# Qdrant настройки
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_COLLECTION=knowledge_base

# Infinity настройки
INFINITY_PORT=7997
# Выберите модель для эмбеддингов (см. раздел "Модели")
INFINITY_MODEL=BAAI/bge-small-en-v1.5
INFINITY_BATCH_SIZE=32

# MCP Hub
MCP_PORT=8765
```

### 3. Настройка config.yaml

Включите векторный поиск в `config.yaml`:

```yaml
# Векторный поиск
VECTOR_SEARCH_ENABLED: true

# Провайдер эмбеддингов
VECTOR_EMBEDDING_PROVIDER: infinity
VECTOR_EMBEDDING_MODEL: BAAI/bge-small-en-v1.5
VECTOR_INFINITY_API_URL: http://infinity:7997

# Векторное хранилище
VECTOR_STORE_PROVIDER: qdrant
VECTOR_QDRANT_URL: http://qdrant:6333
VECTOR_QDRANT_COLLECTION: knowledge_base

# Настройки чанкинга
VECTOR_CHUNKING_STRATEGY: fixed_size_overlap
VECTOR_CHUNK_SIZE: 512
VECTOR_CHUNK_OVERLAP: 50

# Настройки поиска
VECTOR_SEARCH_TOP_K: 5
```

### 4. Запуск

```bash
# Запустить все сервисы
docker-compose -f docker-compose.vector.yml up -d

# Проверить логи
docker-compose -f docker-compose.vector.yml logs -f

# Проверить статус
docker-compose -f docker-compose.vector.yml ps
```

### 5. Проверка работоспособности

```bash
# Проверить Qdrant
curl http://localhost:6333/healthz

# Проверить Infinity
curl http://localhost:7997/health

# Проверить MCP Hub
curl http://localhost:8765/health
```

**Важно**: При использовании external embedding providers (infinity или openai), локальная установка `sentence-transformers` **не требуется**, так как эмбеддинги генерируются внешним сервисом. Требуется только установка vector store backend (faiss-cpu или qdrant-client).

## Модели эмбеддингов

### Рекомендуемые модели для Infinity

#### Английский язык

| Модель | Размер | Качество | Скорость | Использование |
|--------|--------|----------|----------|---------------|
| `BAAI/bge-small-en-v1.5` | 384 dim | Хорошее | ⚡⚡⚡ | По умолчанию, быстро |
| `BAAI/bge-base-en-v1.5` | 768 dim | Отличное | ⚡⚡ | Сбалансированный выбор |
| `BAAI/bge-large-en-v1.5` | 1024 dim | Превосходное | ⚡ | Максимальное качество |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 dim | Хорошее | ⚡⚡⚡ | Легковесная альтернатива |

#### Мультиязычные модели

| Модель | Размер | Языки | Рекомендации |
|--------|--------|-------|--------------|
| `BAAI/bge-m3` | 1024 dim | 100+ | Лучший выбор для мультиязычности |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 dim | 50+ | Компактная альтернатива |

#### Русский язык

| Модель | Размер | Описание |
|--------|--------|----------|
| `BAAI/bge-m3` | 1024 dim | Отлично работает с русским |
| `intfloat/multilingual-e5-large` | 1024 dim | Хорошее качество для русского |

### Смена модели

Изменить модель можно в `.env`:

```env
INFINITY_MODEL=BAAI/bge-m3
```

После изменения модели:

```bash
# Перезапустить Infinity для загрузки новой модели
docker-compose -f docker-compose.vector.yml restart infinity

# Переиндексировать базу знаний (через бота или MCP API)
```

## Использование

### Через Telegram бота

Бот автоматически управляет векторным поиском:

1. **Автоматическая индексация**: при добавлении новых документов
2. **Семантический поиск**: бот использует векторный поиск для ответов на вопросы
3. **Переиндексация**: бот решает, когда нужно обновить индекс

### Через MCP API

#### Векторный поиск

```bash
# Поиск по семантическому сходству
curl -X POST http://localhost:8765/tools/vector_search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "как работают нейронные сети",
    "top_k": 5
  }'
```

Ответ:
```json
{
  "success": true,
  "query": "как работают нейронные сети",
  "top_k": 5,
  "results": [
    {
      "file_path": "topics/ml/neural-networks.md",
      "text": "Нейронные сети - это...",
      "score": 0.89,
      "chunk_index": 0
    }
  ],
  "results_count": 5
}
```

#### Переиндексация

```bash
# Переиндексировать базу знаний
curl -X POST http://localhost:8765/tools/reindex_vector \
  -H "Content-Type: application/json" \
  -d '{
    "force": false
  }'
```

Ответ:
```json
{
  "success": true,
  "files_processed": 42,
  "files_skipped": 5,
  "chunks_indexed": 1234,
  "time_elapsed": "12.5s"
}
```

## Управление данными

### Хранилище данных

```
./data/
├── qdrant_storage/     # Векторная база данных Qdrant
├── infinity_cache/     # Кеш моделей Infinity
└── vector_index/       # Метаданные индекса (для FAISS)
```

### Очистка данных

```bash
# Остановить сервисы
docker-compose -f docker-compose.vector.yml down

# Удалить векторные данные
rm -rf data/qdrant_storage/*
rm -rf data/vector_index/*

# Кеш моделей можно оставить для ускорения следующего запуска
# rm -rf data/infinity_cache/*

# Запустить заново
docker-compose -f docker-compose.vector.yml up -d
```

### Резервное копирование

```bash
# Остановить Qdrant для консистентного бэкапа
docker-compose -f docker-compose.vector.yml stop qdrant

# Создать бэкап
tar -czf qdrant_backup_$(date +%Y%m%d).tar.gz data/qdrant_storage/

# Запустить Qdrant
docker-compose -f docker-compose.vector.yml start qdrant
```

## Производительность

### Настройка батчинга Infinity

```env
# Больше = быстрее, но больше памяти
INFINITY_BATCH_SIZE=32  # По умолчанию

# Для больших моделей или ограниченной памяти
INFINITY_BATCH_SIZE=16

# Для мощного железа
INFINITY_BATCH_SIZE=64
```

### GPU ускорение

Раскомментируйте в `docker-compose.vector.yml`:

```yaml
infinity:
  # ...
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
- CUDA драйверы

### Оптимизация размера чанков

В `config.yaml`:

```yaml
# Меньше чанки = точнее поиск, но медленнее индексация
VECTOR_CHUNK_SIZE: 256

# Больше чанки = быстрее индексация, но менее точный поиск
VECTOR_CHUNK_SIZE: 1024

# Сбалансированный вариант (рекомендуется)
VECTOR_CHUNK_SIZE: 512
```

## Мониторинг

### Просмотр логов

```bash
# Все сервисы
docker-compose -f docker-compose.vector.yml logs -f

# Только Qdrant
docker-compose -f docker-compose.vector.yml logs -f qdrant

# Только Infinity
docker-compose -f docker-compose.vector.yml logs -f infinity

# Только MCP Hub
docker-compose -f docker-compose.vector.yml logs -f mcp-hub
```

### Проверка статуса Qdrant

```bash
# Получить информацию о коллекциях
curl http://localhost:6333/collections

# Информация о конкретной коллекции
curl http://localhost:6333/collections/knowledge_base
```

### Проверка Infinity

```bash
# Проверить доступные модели
curl http://localhost:7997/models

# Протестировать эмбеддинг
curl -X POST http://localhost:7997/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "BAAI/bge-small-en-v1.5",
    "input": ["test text"]
  }'
```

## Troubleshooting

### Infinity не запускается

**Проблема**: `Model download failed`

**Решение**:
```bash
# Проверить логи
docker-compose -f docker-compose.vector.yml logs infinity

# Очистить кеш и перезапустить
rm -rf data/infinity_cache/*
docker-compose -f docker-compose.vector.yml restart infinity
```

### Qdrant занимает много места

**Решение**:
```bash
# Проверить размер
du -sh data/qdrant_storage/

# Оптимизировать (запустить из контейнера Qdrant)
docker exec tg-note-qdrant curl -X POST http://localhost:6333/collections/knowledge_base/optimize
```

### Медленная индексация

**Возможные причины**:
1. Большая модель эмбеддингов
2. Много файлов
3. Маленький батч размер

**Решения**:
```bash
# 1. Использовать меньшую модель
INFINITY_MODEL=BAAI/bge-small-en-v1.5

# 2. Увеличить батч размер
INFINITY_BATCH_SIZE=64

# 3. Использовать GPU (см. раздел "GPU ускорение")
```

### Vector search not available

**Проблема**: Ошибка "Vector search is not available"

**Решение**:
1. Проверить `VECTOR_SEARCH_ENABLED=true` в config.yaml
2. Проверить правильность настройки `VECTOR_EMBEDDING_PROVIDER`:
   - Для `infinity` или `openai`: НЕ требуется установка `sentence-transformers`
   - Для `sentence_transformers`: требуется `pip install sentence-transformers`
3. Убедиться, что установлен хотя бы один vector store:
   - `pip install faiss-cpu` ИЛИ `pip install qdrant-client`
4. Убедиться, что Qdrant и Infinity запущены
5. Проверить сетевое подключение между контейнерами

```bash
# Проверить сеть
docker network inspect tg-note-network

# Проверить, что все контейнеры в одной сети
docker-compose -f docker-compose.vector.yml ps
```

## Переход с простой конфигурации

Если вы использовали `docker-compose.simple.yml`:

```bash
# 1. Остановить текущие сервисы
docker-compose -f docker-compose.simple.yml down

# 2. Обновить config.yaml (включить VECTOR_SEARCH_ENABLED)

# 3. Запустить с векторным поиском
docker-compose -f docker-compose.vector.yml up -d

# 4. Индексировать существующую базу знаний
# (через бота или вызвать reindex_vector API)
```

## Интеграция с существующей базой знаний

При первом запуске с векторным поиском:

1. Все существующие документы будут автоматически проиндексированы
2. Индекс сохраняется в Qdrant
3. При добавлении новых документов индекс обновляется автоматически

## Безопасность

### Qdrant API Key

Для продакшена рекомендуется включить аутентификацию:

```yaml
qdrant:
  environment:
    - QDRANT__SERVICE__API_KEY=your-secret-key
```

И обновить в `.env`:
```env
VECTOR_QDRANT_API_KEY=your-secret-key
```

### Infinity API Key

Если нужна аутентификация для Infinity:

```yaml
infinity:
  environment:
    - INFINITY_API_KEY=your-secret-key
```

И в `.env`:
```env
VECTOR_INFINITY_API_KEY=your-secret-key
```

## Дополнительные ресурсы

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Infinity GitHub](https://github.com/michaelfeil/infinity)
- [BGE Models](https://huggingface.co/BAAI)
- [Sentence Transformers](https://www.sbert.net/)

## AICODE-NOTE

Логика работы:
- **Bot** управляет процессом: решает когда индексировать, когда искать
- **MCP Hub** предоставляет инструменты: vector_search, reindex_vector
- **Qdrant** хранит векторы: отдельная коллекция для каждой базы знаний
- **Infinity** генерирует эмбеддинги: преобразует текст в векторы

Каждая база знаний пользователя получает свою коллекцию в Qdrant, что обеспечивает изоляцию данных.
