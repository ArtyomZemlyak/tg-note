# Vector Search - Quick Reference

**Статус:** ✅ Production Ready  
**Версия:** 1.0.0  

## Quick Start

### 1. Включить векторный поиск

```yaml
# config.yaml
vector_search:
  enabled: true
```

### 2. Установить зависимости

```bash
pip install sentence-transformers faiss-cpu
```

### 3. Перезапустить

```bash
docker-compose up -d
```

**Готово!** Векторный поиск работает автоматически.

## Как это работает

### Для Autonomous Agent

```python
# Agent создает файл
file_create("note.md", "# Content")
# → KB_FILE_CREATED событие
# → Реиндексация через 2 сек ✅

# Agent коммитит
git.commit("Update")
# → KB_GIT_COMMIT событие  
# → Реиндексация через 2 сек ✅
```

### Для Qwen CLI Agent

```python
# Qwen CLI работает (мы не видим операции с файлами)
qwen_cli.run("Update knowledge base")

# Но когда завершает работу:
git.auto_commit_and_push("Done")
# → KB_GIT_COMMIT событие
# → Реиндексация через 2 сек ✅
```

### Для любого агента

**Git commit = универсальная точка триггера!**

Если ваш агент делает `git commit` после работы - реиндексация запустится автоматически.

## Features

✅ **MCP Integration** - векторный поиск через MCP Hub  
✅ **Event-Driven** - реактивная реиндексация (~2 сек)  
✅ **Git Triggers** - работает для всех агентов  
✅ **Batching** - множественные изменения → одна индексация  
✅ **Fallback** - периодический мониторинг (5 мин)  

## Architecture

```
Agent → Makes changes → Git commit
                          ↓
                    KB_GIT_COMMIT event
                          ↓
                      EventBus
                          ↓
               BotVectorSearchManager
                          ↓
                Batch (2 sec window)
                          ↓
                      Reindex!
```

## Configuration

### Минимальная

```yaml
vector_search:
  enabled: true
```

### Полная

```yaml
vector_search:
  enabled: true
  
  embedding:
    provider: sentence_transformers  # or openai, infinity
    model: all-MiniLM-L6-v2
  
  vector_store:
    provider: faiss  # or qdrant
  
  chunking:
    strategy: fixed_size_overlap
    chunk_size: 512
    chunk_overlap: 50
  
  search:
    top_k: 5
```

## Using GitOps with Events

### Старый способ (без событий)

```python
from src.knowledge_base.git_ops import GitOps

git_ops = GitOps(repo_path)
```

### Новый способ (с событиями) ✅

```python
from src.knowledge_base.git_ops_with_events import create_git_ops_for_user

git_ops = create_git_ops_for_user(
    repo_path=kb_path,
    user_id=user_id,
    with_events=True  # default
)
```

**Все остальное работает так же!**

```python
git_ops.commit("Update")          # → Публикует событие
git_ops.auto_commit_and_push()   # → Публикует событие
```

## Custom Events

### Публикация события

```python
from src.core.events import EventType, KBChangeEvent, get_event_bus

event = KBChangeEvent(
    event_type=EventType.KB_FILE_CREATED,
    file_path=Path("new_file.md"),
    user_id=123,
    source="my_tool"
)
get_event_bus().publish(event)
```

### Подписка на события

```python
from src.core.events import EventType, get_event_bus

def my_handler(event):
    print(f"File changed: {event.file_path}")

get_event_bus().subscribe(EventType.KB_FILE_CREATED, my_handler)
```

## Performance

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| File change | 0-300 sec | ~2 sec | **150x faster** |
| Git commit | 0-300 sec | ~2 sec | **150x faster** |
| Multiple changes | N × delay | ~2 sec | **Batched** |

## Supported Agents

| Agent | Events | Latency | Status |
|-------|--------|---------|--------|
| Autonomous Agent | ✅ All events | ~2 sec | ✅ Works |
| Qwen CLI | ✅ Git only | ~2 sec | ✅ Works |
| Custom | ✅ Configurable | ~2 sec | ✅ Works |

## Troubleshooting

### Векторный поиск не работает?

```bash
# 1. Проверить конфигурацию
grep VECTOR_SEARCH config.yaml

# 2. Проверить зависимости
pip list | grep -E "sentence|faiss|qdrant"

# 3. Проверить логи
docker-compose logs -f bot | grep -i vector
docker-compose logs -f mcp-hub | grep -i vector
```

### События не публикуются?

```python
# Проверить EventBus
from src.core.events import get_event_bus
bus = get_event_bus()
print(f"Subscribers: {bus.get_subscriber_count()}")

# Проверить GitOps
# Убедитесь что используете GitOpsWithEvents!
from src.knowledge_base.git_ops_with_events import create_git_ops_for_user
```

### Реиндексация не запускается?

```bash
# Проверить что vector search доступен в MCP Hub
curl http://localhost:8765/health | jq '.builtin_tools'

# Должны быть: vector_search, reindex_vector
```

## Documentation

📚 **Полная документация:**

1. **VECTOR_SEARCH_COMPLETE_REFACTORING.md** - Полный обзор
2. **VECTOR_SEARCH_MCP_REFACTORING.md** - MCP интеграция
3. **VECTOR_SEARCH_EVENT_DRIVEN.md** - Event-driven архитектура  
4. **VECTOR_SEARCH_GIT_INTEGRATION.md** - Git commit события
5. **docs_site/architecture/vector-search-mcp-integration.md** - Техническая документация

📝 **Примеры:**

- `examples/vector_search_git_events_example.py` - Working examples
- `examples/vector_search_example.py` - Basic usage

🧪 **Тесты:**

- `tests/test_bot_vector_search.py` - 15+ unit tests
- `tests/test_vector_search.py` - Integration tests

## What's New

### Version 1.0.0 (2025-10-20)

✅ **MCP Integration**
- Векторный поиск интегрирован с MCP Hub
- Автоматическая проверка и индексация

✅ **Event-Driven Reindexing**
- 150x faster than periodic monitoring
- SOLID architecture
- Smart batching

✅ **Git Commit Events**
- Works for ALL agent types
- Universal trigger point
- Qwen CLI support

## Examples

### Example 1: Simple Usage

```python
# Agent делает изменения
Path("kb/note.md").write_text("# New Note")

# Agent коммитит
git_ops.commit("Add note")

# → Автоматическая реиндексация через 2 сек!
```

### Example 2: Qwen CLI

```python
# Qwen CLI работает с KB (свои тулзы)
qwen_cli.run("Organize knowledge base")

# Финальный коммит
git_ops.auto_commit_and_push("Qwen completed")

# → Все изменения проиндексированы!
```

### Example 3: Manual Trigger

```python
# Можно триггернуть вручную
from src.bot.vector_search_manager import vector_search_manager

await vector_search_manager.trigger_reindex()
```

## FAQ

**Q: Нужно ли что-то менять в существующем коде?**  
A: Нет! Все работает автоматически. Опционально можно переключиться на `GitOpsWithEvents`.

**Q: Работает ли с Qwen CLI?**  
A: Да! Специально реализована поддержка через git commit events.

**Q: Какой overhead от событий?**  
A: ~2ms per event - negligible.

**Q: Что если EventBus недоступен?**  
A: Graceful degradation - git операции продолжат работать.

**Q: Можно ли отключить события?**  
A: Да: `create_git_ops_for_user(..., with_events=False)`

## Support

- 📖 Documentation: See files above
- 🐛 Issues: Check logs first
- 💬 Questions: Read FAQ
- 🎯 Examples: See `examples/` folder

---

**Ready to use!** ✅

Just enable in config and restart - everything works automatically.
