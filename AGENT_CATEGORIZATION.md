# Категоризация и рефакторинг агентов

## Дата: 2025-10-03

## Категории агентов

### Категория 1: Управляемые агенты (Managed Agents)
**Логика агентности на нашей стороне**

Характеристики:
- Мы предоставляем tools для работы с файлами
- Мы контролируем agent loop
- Мы собираем отчет об изменениях ПО ХОДУ РАБОТЫ
- Файлы создаются через наши tools (file_create, folder_create)

**Агенты:**
1. **QwenCodeAgent** (наследует AutonomousAgent)
   - Базируется на нашем autonomous_agent
   - Использует наши tools
   - ✅ УЖЕ ИМЕЕТ file_create, folder_create
   - ❌ НЕ собирает отчет об изменениях

2. **OpenAIAgent** (наследует AutonomousAgent)
   - Базируется на нашем autonomous_agent
   - Использует OpenAI function calling
   - Использует наши tools
   - ✅ УЖЕ ИМЕЕТ file_create, folder_create в schema
   - ❌ НЕ собирает отчет об изменениях

3. **StubAgent** (наследует BaseAgent)
   - Простейший агент без AI
   - НЕ использует tools
   - Возвращает один markdown
   - ⚠️ ОСТАВИТЬ КАК ЕСТЬ (простейший, для тестов)

### Категория 2: Автономные агенты (Autonomous External Agents)
**Логика агентности на стороне агента**

Характеристики:
- Агент сам реализует всю логику
- Агент сам управляет файлами
- Мы даем задачу, агент выполняет
- Агент возвращает ОТЧЕТ о том, что сделал

**Агенты:**
1. **QwenCodeCLIAgent**
   - Использует внешний qwen CLI
   - CLI сам реализует агентность
   - CLI сам может создавать файлы
   - ❌ СЕЙЧАС возвращает только текст
   - ✅ НУЖНО: вернуть структурированный отчет

## Задачи рефакторинга

### Для Категории 1 (Managed Agents)

**Цель:** Собирать отчет об изменениях ПО ХОДУ РАБОТЫ

**Что нужно:**

1. **Добавить трекинг изменений в AutonomousAgent:**
   ```python
   class AutonomousAgent:
       def __init__(self):
           self.kb_changes = KBChangesTracker()  # Новый класс
       
       async def process(self):
           # ... agent loop ...
           
           # В конце вернуть отчет
           if self.kb_changes.has_changes():
               return {
                   "files": self.kb_changes.get_files_report(),
                   "metadata": {...}
               }
   ```

2. **Обновить file/folder tools для автоматического трекинга:**
   ```python
   async def _tool_file_create(self, params):
       # Создать файл
       full_path = ...
       
       # АВТОМАТИЧЕСКИ добавить в трекер
       self.kb_changes.add_file_created(
           path=relative_path,
           title=extracted_title,
           kb_structure=inferred_kb_structure
       )
   ```

3. **QwenCodeAgent и OpenAIAgent автоматически получат этот функционал**
   - Они наследуют AutonomousAgent
   - Tools автоматически будут трекать изменения

### Для Категории 2 (Autonomous External Agents)

**Цель:** Получить от агента структурированный отчет

**Что нужно:**

1. **QwenCodeCLIAgent - изменить промпт:**
   ```python
   # Промпт должен просить CLI вернуть JSON с отчетом
   PROMPT = """
   Выполни задачу и верни результат в JSON формате:
   {
       "summary": "краткое описание что сделано",
       "files_created": [
           {
               "path": "relative/path/to/file.md",
               "title": "File Title",
               "category": "ai",
               "subcategory": "models",
               "tags": ["tag1", "tag2"]
           }
       ],
       "folders_created": ["ai/models", "tech/frameworks"],
       "files_edited": ["existing/file.md"]
   }
   """
   ```

2. **QwenCodeCLIAgent - парсить JSON результат:**
   ```python
   def _parse_qwen_result(self, result_text):
       # Попытаться извлечь JSON
       try:
           report = json.loads(result_text)
           
           # Конвертировать в наш формат
           files = []
           for file_info in report.get("files_created", []):
               files.append({
                   "markdown": self._read_created_file(file_info["path"]),
                   "title": file_info["title"],
                   "kb_structure": KBStructure(
                       category=file_info["category"],
                       subcategory=file_info.get("subcategory"),
                       tags=file_info.get("tags", [])
                   )
               })
           
           return {
               "files": files,
               "metadata": {...}
           }
       except:
           # Fallback к старому поведению
   ```

## Новый класс: KBChangesTracker

```python
class KBChangesTracker:
    """
    Отслеживает изменения в базе знаний во время работы агента
    """
    
    def __init__(self, kb_root_path: Path):
        self.kb_root_path = kb_root_path
        self.files_created = []
        self.files_edited = []
        self.folders_created = []
    
    def add_file_created(self, path: str, title: str, kb_structure: KBStructure):
        """Зарегистрировать создание файла"""
        full_path = self.kb_root_path / path
        
        # Прочитать контент
        content = full_path.read_text(encoding="utf-8") if full_path.exists() else ""
        
        self.files_created.append({
            "path": path,
            "markdown": content,
            "title": title,
            "kb_structure": kb_structure
        })
    
    def add_folder_created(self, path: str):
        """Зарегистрировать создание папки"""
        self.folders_created.append(path)
    
    def add_file_edited(self, path: str):
        """Зарегистрировать редактирование файла"""
        self.files_edited.append(path)
    
    def has_changes(self) -> bool:
        """Проверить есть ли изменения"""
        return bool(
            self.files_created or 
            self.files_edited or 
            self.folders_created
        )
    
    def get_files_report(self) -> List[Dict]:
        """
        Получить отчет о созданных файлах в формате для handlers
        
        Returns:
            List of file dicts with markdown, title, kb_structure
        """
        return self.files_created
    
    def get_summary(self) -> str:
        """Получить текстовое резюме изменений"""
        summary = []
        
        if self.files_created:
            summary.append(f"Создано файлов: {len(self.files_created)}")
            for f in self.files_created:
                summary.append(f"  • {f['path']}")
        
        if self.folders_created:
            summary.append(f"Создано папок: {len(self.folders_created)}")
            for folder in self.folders_created:
                summary.append(f"  • {folder}")
        
        if self.files_edited:
            summary.append(f"Изменено файлов: {len(self.files_edited)}")
            for f in self.files_edited:
                summary.append(f"  • {f}")
        
        return "\n".join(summary)
```

## Интеграция с tools

```python
# В AutonomousAgent
async def _tool_file_create(self, params: Dict[str, Any]) -> ToolResult:
    relative_path = params.get("path", "")
    content = params.get("content", "")
    
    # Создать файл (существующий код)
    # ...
    
    # АВТОМАТИЧЕСКИ зарегистрировать
    title = self._extract_title_from_content(content)
    kb_structure = self._infer_kb_structure_from_path(relative_path)
    
    self.kb_changes.add_file_created(
        path=relative_path,
        title=title,
        kb_structure=kb_structure
    )
    
    return ToolResult(success=True, ...)
```

## Итоговое поведение

### Managed Agents (QwenCodeAgent, OpenAIAgent)

```python
# Пример работы
agent = QwenCodeAgent(...)
result = await agent.process(content)

# Если агент создал файлы через tools:
{
    "files": [
        {
            "markdown": "...",
            "title": "GPT-4",
            "kb_structure": KBStructure(category="ai", subcategory="models")
        },
        {
            "markdown": "...",
            "title": "Vision Models",
            "kb_structure": KBStructure(category="ai", subcategory="multimodal")
        }
    ],
    "metadata": {
        "agent": "QwenCodeAgent",
        "kb_changes_summary": "Создано файлов: 2\n  • ai/models/gpt4.md\n  • ai/multimodal/vision.md"
    }
}

# Если агент НЕ создал файлы (backward compatibility):
{
    "markdown": "...",
    "title": "...",
    "kb_structure": ...
}
```

### Autonomous Agents (QwenCodeCLIAgent)

```python
# Пример работы
agent = QwenCodeCLIAgent(...)
result = await agent.process(content)

# CLI создал файлы и вернул отчет:
{
    "files": [
        {
            "markdown": "...",  # Прочитано из созданного файла
            "title": "GPT-4",
            "kb_structure": KBStructure(category="ai", subcategory="models")
        }
    ],
    "metadata": {
        "agent": "QwenCodeCLIAgent",
        "cli_summary": "Created 2 files, 1 folder"
    }
}
```

## Преимущества нового подхода

1. **Полная видимость изменений:**
   - Handlers знают о ВСЕХ созданных файлах
   - Git коммитит ВСЕ файлы
   - Telegram показывает ВСЕ изменения
   - Tracker сохраняет ВСЕ пути

2. **Автоматический трекинг:**
   - Managed agents автоматически трекают через tools
   - Не нужно вручную собирать отчет
   - Изменения отслеживаются ПО ХОДУ работы

3. **Унификация:**
   - Все агенты возвращают одинаковый формат
   - Handlers обрабатывают единообразно
   - Backward compatibility сохранена

4. **Гибкость:**
   - Агенты могут создавать 0, 1 или много файлов
   - Автоматическая адаптация формата результата
   - Поддержка как managed, так и autonomous агентов
