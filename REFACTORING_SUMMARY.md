# Рефакторинг: Инкапсуляция логики тулзов и агента

## Обзор

Проведён полный рефакторинг архитектуры тулзов автономного агента для обеспечения лучшей инкапсуляции и соблюдения принципа единственной ответственности (Single Responsibility Principle).

## Проблемы до рефакторинга

1. **Разделение метаданных и логики**: Описания тулзов, схемы параметров и другие метаданные находились в `registry.py`, а логика выполнения - в отдельных файлах тулзов
2. **Дублирование кода**: Множество wrapper методов в `autonomous_agent.py` дублировали вызовы к ToolManager
3. **Плохая инкапсуляция**: Каждый тулз не был самодостаточным - его метаданные и логика были разнесены по разным местам

## Решение

### 1. Создан базовый класс `BaseTool`

**Файл**: `src/agents/tools/base_tool.py`

```python
class BaseTool(ABC):
    """Базовый класс для всех тулзов"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя тулза"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Описание для LLM"""
        pass
    
    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON схема параметров"""
        pass
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Выполнение тулза"""
        pass
```

**Преимущества**:
- Каждый тулз инкапсулирует свои метаданные И логику
- Единая точка определения всех аспектов тулза
- Легко добавлять новые тулзы без изменения registry

### 2. Рефакторинг всех тулзов

Все тулзы теперь наследуются от `BaseTool` и являются самодостаточными:

#### KB Reading Tools (`kb_reading_tools.py`)
- `KBReadFileTool` - чтение файлов
- `KBListDirectoryTool` - листинг директорий
- `KBSearchFilesTool` - поиск файлов
- `KBSearchContentTool` - поиск по содержимому

#### File Tools (`file_tools.py`)
- `FileCreateTool` - создание файлов
- `FileEditTool` - редактирование файлов
- `FileDeleteTool` - удаление файлов
- `FileMoveTool` - перемещение файлов

#### Folder Tools (`folder_tools.py`)
- `FolderCreateTool` - создание папок
- `FolderDeleteTool` - удаление папок
- `FolderMoveTool` - перемещение папок

#### Planning Tools (`planning_tools.py`)
- `PlanTodoTool` - создание TODO планов
- `AnalyzeContentTool` - анализ контента

#### Web Tools (`web_tools.py`)
- `WebSearchTool` - веб-поиск

#### Git Tools (`git_tools.py`)
- `GitCommandTool` - выполнение git команд

#### GitHub Tools (`github_tools.py`)
- `GitHubAPITool` - работа с GitHub API

#### Shell Tools (`shell_tools.py`)
- `ShellCommandTool` - выполнение shell команд

#### Vector Search Tools (`vector_search_tools.py`)
- `VectorSearchTool` - векторный поиск
- `VectorReindexTool` - реиндексация

**Каждый модуль экспортирует**: `ALL_TOOLS = [Tool1(), Tool2(), ...]`

### 3. Упрощение Registry

**Файл**: `src/agents/tools/registry.py`

Registry теперь только:
- Регистрирует тулзы из модулей
- Управляет выполнением
- Строит OpenAI схемы

**Автоматическое обнаружение тулзов**:
```python
# Автоматически импортирует и регистрирует
from . import planning_tools
manager.register_many(planning_tools.ALL_TOOLS)
```

### 4. Упрощение Autonomous Agent

**Файл**: `src/agents/autonomous_agent.py`

**Удалено**:
- Все wrapper методы типа `_tool_plan_todo()`, `_tool_kb_read_file()` и т.д.
- Дублирующий код валидации путей
- Прямые импорты логики тулзов

**Осталось**:
- Только использование `ToolManager` для выполнения тулзов
- Чистая бизнес-логика агента

## Архитектура после рефакторинга

```
src/agents/tools/
├── base_tool.py          # BaseTool, ToolContext, ToolSpec
├── registry.py           # ToolManager (регистрация и выполнение)
├── __init__.py           # Экспорт базовых классов
│
├── kb_reading_tools.py   # KB тулзы (4 класса)
├── file_tools.py         # Файловые тулзы (4 класса)
├── folder_tools.py       # Папочные тулзы (3 класса)
├── planning_tools.py     # Планирующие тулзы (2 класса)
├── web_tools.py          # Веб тулзы (1 класс)
├── git_tools.py          # Git тулзы (1 класс)
├── github_tools.py       # GitHub тулзы (1 класс)
├── shell_tools.py        # Shell тулзы (1 класс)
└── vector_search_tools.py # Векторные тулзы (2 класса)
```

## Принципы, которым следует новая архитектура

1. **Single Responsibility Principle** - каждый тулз отвечает только за свою логику
2. **Encapsulation** - метаданные и логика инкапсулированы в одном месте
3. **Open/Closed Principle** - легко добавлять новые тулзы без изменения существующих
4. **Dependency Injection** - зависимости передаются через ToolContext
5. **Auto-discovery** - Registry автоматически находит и регистрирует тулзы

## Как добавить новый тулз

1. Создать класс, наследующий `BaseTool`:
```python
class MyNewTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_new_tool"
    
    @property
    def description(self) -> str:
        return "Описание тулза"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        # Логика выполнения
        return {"success": True, ...}
```

2. Добавить в список `ALL_TOOLS` в соответствующем модуле:
```python
ALL_TOOLS = [
    ExistingTool(),
    MyNewTool(),  # ← новый тулз
]
```

3. Готово! Registry автоматически обнаружит и зарегистрирует тулз.

## Преимущества новой архитектуры

1. ✅ **Лучшая инкапсуляция** - всё о тулзе в одном месте
2. ✅ **Меньше кода** - нет дублирования, нет wrapper методов
3. ✅ **Проще поддержка** - изменения тулза локализованы
4. ✅ **Легче тестирование** - каждый тулз - независимая единица
5. ✅ **Масштабируемость** - легко добавлять новые тулзы
6. ✅ **Читаемость** - ясная структура и назначение каждого файла

## Проверка

Все файлы проверены на синтаксис:
```bash
✓ base_tool.py syntax OK
✓ kb_reading_tools.py syntax OK
✓ file_tools.py syntax OK
✓ folder_tools.py syntax OK
✓ planning_tools.py syntax OK
✓ web_tools.py syntax OK
✓ git_tools.py syntax OK
✓ github_tools.py syntax OK
✓ shell_tools.py syntax OK
✓ vector_search_tools.py syntax OK
✓ registry.py syntax OK
✓ autonomous_agent.py syntax OK
```

## Обратная совместимость

Изменения полностью обратно совместимы:
- API `ToolManager` не изменился
- `build_default_tool_manager()` работает как раньше
- `AutonomousAgent` использует те же методы выполнения тулзов

Единственное различие - внутренняя организация кода стала чище и логичнее.
