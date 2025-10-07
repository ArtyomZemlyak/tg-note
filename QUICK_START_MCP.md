# 🚀 Quick Start: MCP для Qwen CLI

## Что это дает?

Ваш Telegram бот теперь может **запоминать информацию** между сообщениями!

LLM получает доступ к инструментам:
- 💾 `store_memory` - Сохранить информацию
- 🔍 `retrieve_memory` - Найти сохраненное
- 📋 `list_categories` - Показать категории

## 3 простых шага

### 1️⃣ Включить MCP в конфиге

```yaml
# config.yaml
AGENT_TYPE: "qwen_code_cli"
AGENT_ENABLE_MCP: true  # ← Добавить
```

### 2️⃣ Создать агента

```python
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent

agent = QwenCodeCLIAgent(
    config={
        "enable_mcp": True,
        "user_id": 123
    },
    working_directory="/path/to/kb"
)

# ✅ Автоматически настроено!
```

### 3️⃣ Использовать

```
User → Bot: Запомни: deadline 15 декабря
Bot: ✅ Сохранено в памяти

User → Bot: Какие у меня дедлайны?
Bot: 📅 Deadline: 15 декабря
```

## Проверить установку

```bash
# 1. Проверить конфиг
cat ~/.qwen/settings.json

# 2. Запустить пример
python examples/qwen_mcp_integration_example.py

# 3. Запустить тесты
pytest tests/test_qwen_mcp_integration.py -v
```

## Где хранятся данные?

```
data/memory/user_123/memory.json
```

## Документация

📚 **[IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)** - Полный обзор  
📖 **[docs/QWEN_MCP_SETUP_GUIDE.md](docs/QWEN_MCP_SETUP_GUIDE.md)** - Детальное руководство  
💻 **[examples/qwen_mcp_integration_example.py](examples/qwen_mcp_integration_example.py)** - Примеры кода

---

**Готово!** 🎉
