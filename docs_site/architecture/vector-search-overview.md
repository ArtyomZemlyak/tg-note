# Vector Search Overview

**Status:** ✅ Production Ready  
**Version:** 1.0.0

## What is Vector Search?

Vector search enables semantic search through your knowledge base - finding relevant content by meaning, not just keywords. This allows the bot to understand context and find related information even when exact word matches aren't present.

## Key Features

✅ **MCP Integration** - Vector search through MCP Hub  
✅ **Event-Driven** - Reactive reindexing (~2 sec)  
✅ **Git Triggers** - Works for all agent types  
✅ **Batching** - Multiple changes → single indexing  
✅ **Fallback** - Periodic monitoring (5 min)  
✅ **Multi-language** - Russian and English support

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

## How It Works

### For Autonomous Agent

```python
# Agent creates file
file_create("note.md", "# Content")
# → KB_FILE_CREATED event
# → Reindexing in 2 sec ✅

# Agent commits
git.commit("Update")
# → KB_GIT_COMMIT event  
# → Reindexing in 2 sec ✅
```

### For Qwen CLI Agent

```python
# Qwen CLI works (we don't see file operations)
qwen_cli.run("Update knowledge base")

# But when it finishes:
git.auto_commit_and_push("Done")
# → KB_GIT_COMMIT event
# → Reindexing in 2 sec ✅
```

### For Any Agent

**Git commit = universal trigger point!**

If your agent does `git commit` after work - reindexing will start automatically.

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

## Quick Start

### 1. Enable Vector Search

```yaml
# config.yaml
vector_search:
  enabled: true
```

### 2. Install Dependencies

```bash
pip install sentence-transformers faiss-cpu
```

### 3. Restart

```bash
docker-compose up -d
```

**Done!** Vector search works automatically.

## Configuration

### Minimal

```yaml
vector_search:
  enabled: true
```

### Full

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

### Old Way (without events)

```python
from src.knowledge_base.git_ops import GitOps

git_ops = GitOps(repo_path)
```

### New Way (with events) ✅

```python
from src.knowledge_base.git_ops_with_events import create_git_ops_for_user

git_ops = create_git_ops_for_user(
    repo_path=kb_path,
    user_id=user_id,
    with_events=True  # default
)
```

**Everything else works the same!**

```python
git_ops.commit("Update")          # → Publishes event
git_ops.auto_commit_and_push()   # → Publishes event
```

## Custom Events

### Publishing Events

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

### Subscribing to Events

```python
from src.core.events import EventType, get_event_bus

def my_handler(event):
    print(f"File changed: {event.file_path}")

get_event_bus().subscribe(EventType.KB_FILE_CREATED, my_handler)
```

## Examples

### Example 1: Simple Usage

```python
# Agent makes changes
Path("kb/note.md").write_text("# New Note")

# Agent commits
git_ops.commit("Add note")

# → Automatic reindexing in 2 sec!
```

### Example 2: Qwen CLI

```python
# Qwen CLI works with KB (its own tools)
qwen_cli.run("Organize knowledge base")

# Final commit
git_ops.auto_commit_and_push("Qwen completed")

# → All changes indexed!
```

### Example 3: Manual Trigger

```python
# Can trigger manually
from src.bot.vector_search_manager import vector_search_manager

await vector_search_manager.trigger_reindex()
```

## Troubleshooting

### Vector search not working?

```bash
# 1. Check configuration
grep VECTOR_SEARCH config.yaml

# 2. Check dependencies
pip list | grep -E "sentence|faiss|qdrant"

# 3. Check logs
docker-compose logs -f bot | grep -i vector
docker-compose logs -f mcp-hub | grep -i vector
```

### Events not publishing?

```python
# Check EventBus
from src.core.events import get_event_bus
bus = get_event_bus()
print(f"Subscribers: {bus.get_subscriber_count()}")

# Check GitOps
# Make sure you're using GitOpsWithEvents!
from src.knowledge_base.git_ops_with_events import create_git_ops_for_user
```

### Reindexing not starting?

```bash
# Check that vector search is available in MCP Hub
curl http://localhost:8765/health | jq '.builtin_tools'

# Should have: vector_search, reindex_vector
```

## FAQ

**Q: Do I need to change anything in existing code?**  
A: No! Everything works automatically. Optionally you can switch to `GitOpsWithEvents`.

**Q: Does it work with Qwen CLI?**  
A: Yes! Special support implemented through git commit events.

**Q: What's the overhead from events?**  
A: ~2ms per event - negligible.

**Q: What if EventBus is unavailable?**  
A: Graceful degradation - git operations continue to work.

**Q: Can I disable events?**  
A: Yes: `create_git_ops_for_user(..., with_events=False)`

## Documentation

📚 **Complete Documentation:**

1. [Vector Search MCP Integration](vector-search-mcp-integration.md) - Technical documentation
2. [Docker Vector Search Setup](../deployment/docker-vector-search.md) - Docker deployment
3. [Vector Search Quick Start](../getting-started/vector-search-quickstart.md) - Quick start guide

📝 **Examples:**

- `examples/vector_search_git_events_example.py` - Working examples
- `examples/vector_search_example.py` - Basic usage

🧪 **Tests:**

- `tests/test_bot_vector_search.py` - 15+ unit tests
- `tests/test_vector_search.py` - Integration tests

## What's New

### Version 1.0.0 (2025-10-20)

✅ **MCP Integration**
- Vector search integrated with MCP Hub
- Automatic checking and indexing

✅ **Event-Driven Reindexing**
- 150x faster than periodic monitoring
- SOLID architecture
- Smart batching

✅ **Git Commit Events**
- Works for ALL agent types
- Universal trigger point
- Qwen CLI support

---

**Ready to use!** ✅

Just enable in config and restart - everything works automatically.