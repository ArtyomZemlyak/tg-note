# Реализация: Managed vs Autonomous Agents

## Дата: 2025-10-03

## Реализовано

### 1. Managed Agents (✅ ГОТОВО)

**Агенты:** QwenCodeAgent, OpenAIAgent

**Реализация:**
- ✅ Добавлен `KBChangesTracker` для отслеживания изменений
- ✅ `AutonomousAgent` инициализирует tracker
- ✅ File/folder tools автоматически регистрируют изменения
- ✅ `process()` возвращает `files: [...]` если есть изменения
- ✅ Backward compatibility: возвращает single file если нет изменений

**Как работает:**
```python
# Агент создает файлы через tools
agent._tool_file_create({"path": "ai/models/gpt4.md", "content": "..."})
# ↓ Автоматически регистрируется в tracker
agent.kb_changes.add_file_created(...)

# В конце process()
if agent.kb_changes.has_changes():
    return {"files": agent.kb_changes.get_files_report()}
```

### 2. Autonomous External Agents (🔄 В ПРОЦЕССЕ)

**Агенты:** QwenCodeCLIAgent

**План реализации:**
1. ✅ CLI работает в working_directory = KB root
2. ⏳ После выполнения - сканировать созданные файлы
3. ⏳ Парсить их для извлечения metadata
4. ⏳ Вернуть отчет в формате `files: [...]`

**Следующий шаг:** Реализовать сканирование файлов в QwenCodeCLIAgent

---

## Текущий статус

**Managed Agents:** READY ✅
**Autonomous Agents:** IN PROGRESS 🔄
**Tests:** TODO ⏳
**Documentation:** IN PROGRESS 📝
