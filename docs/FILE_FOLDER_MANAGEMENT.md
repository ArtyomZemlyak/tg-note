# File and Folder Management для Агента

## Обзор

Добавлена поддержка операций с файлами и папками для агента базы знаний. Агент теперь может автономно управлять структурой базы знаний, создавая, редактируя, удаляя и перемещая файлы и папки.

## Безопасность

**Все операции с файлами и папками работают ТОЛЬКО с относительными путями от корня базы знаний.**

### Правила безопасности:

1. ✅ **Разрешено**: Относительные пути от корня БЗ
   - `ai/machine-learning/notes.md`
   - `tech/python/tutorial.md`
   - `projects/myproject/README.md`

2. ❌ **Запрещено**: Абсолютные пути
   - `/home/user/knowledge_base/ai/notes.md`
   - `C:\Users\knowledge_base\tech\notes.md`

3. ❌ **Запрещено**: Обход директорий (path traversal)
   - `../../../etc/passwd`
   - `ai/../../../secrets.txt`

4. 🔒 **Защита**: Все операции ограничены корневой директорией БЗ
   - Попытка выхода за пределы БЗ блокируется
   - Нельзя удалить сам корень БЗ

## Доступные операции

### Управление файлами

#### 1. Создание файла
```python
file_create(path="ai/notes.md", content="# My Notes\n...")
```
- Создает новый файл с содержимым
- Автоматически создает родительские директории
- Ошибка, если файл уже существует

#### 2. Редактирование файла
```python
file_edit(path="ai/notes.md", content="# Updated Notes\n...")
```
- Заменяет содержимое существующего файла
- Ошибка, если файл не существует

#### 3. Удаление файла
```python
file_delete(path="ai/notes.md")
```
- Удаляет файл
- Ошибка, если файл не существует

#### 4. Перемещение/переименование файла
```python
file_move(source="ai/old.md", destination="ai/new.md")
```
- Перемещает или переименовывает файл
- Автоматически создает родительские директории
- Ошибка, если источник не существует или назначение уже существует

### Управление папками

#### 1. Создание папки
```python
folder_create(path="ai/new-topic")
```
- Создает новую папку
- Автоматически создает родительские директории
- Ошибка, если папка уже существует

#### 2. Удаление папки
```python
folder_delete(path="ai/old-topic")
```
- Удаляет папку и все её содержимое
- Ошибка, если папка не существует
- Нельзя удалить корневую директорию БЗ

#### 3. Перемещение/переименование папки
```python
folder_move(source="ai/old-name", destination="ai/new-name")
```
- Перемещает или переименовывает папку со всем содержимым
- Автоматически создает родительские директории
- Ошибка, если источник не существует или назначение уже существует
- Нельзя переместить корневую директорию БЗ

## Настройки

### В config/settings.py

```python
AGENT_ENABLE_FILE_MANAGEMENT: bool = Field(
    default=True,
    description="Enable file operations (create, edit, delete, move files)"
)

AGENT_ENABLE_FOLDER_MANAGEMENT: bool = Field(
    default=True,
    description="Enable folder operations (create, delete, move folders)"
)
```

### В config.example.yaml

```yaml
# Управление файлами
AGENT_ENABLE_FILE_MANAGEMENT: true

# Управление папками
AGENT_ENABLE_FOLDER_MANAGEMENT: true
```

## Инструкции для агента

Агент получает обновленные инструкции, включающие:

### QWEN_CODE_AGENT_INSTRUCTION
- Список доступных инструментов с файловыми операциями
- Правила безопасности для путей
- Примеры использования относительных путей

### QWEN_CODE_CLI_AGENT_INSTRUCTION
- Описание доступных операций
- Правила безопасности для файловых операций
- Рекомендации по организации контента

## Примеры использования

### Пример 1: Создание структуры для новой темы
```python
# Создать папку
folder_create(path="ai/transformers")

# Создать файлы
file_create(
    path="ai/transformers/overview.md",
    content="# Transformers Overview\n..."
)
file_create(
    path="ai/transformers/bert.md",
    content="# BERT Model\n..."
)
```

### Пример 2: Реорганизация контента
```python
# Переместить файл в другую категорию
file_move(
    source="general/ml-notes.md",
    destination="ai/machine-learning/notes.md"
)

# Переименовать папку
folder_move(
    source="ai/old-structure",
    destination="ai/new-structure"
)
```

### Пример 3: Обновление существующего контента
```python
# Прочитать и обновить файл
file_edit(
    path="ai/notes.md",
    content="# Updated Notes\n\nNew information..."
)
```

### Пример 4: Очистка устаревшего контента
```python
# Удалить устаревший файл
file_delete(path="ai/old-notes.md")

# Удалить устаревшую категорию
folder_delete(path="deprecated")
```

## Обработка ошибок

Все инструменты возвращают `ToolResult` с полями:
- `success`: `True`/`False` - успешность операции
- `output`: Словарь с результатами (при успехе)
- `error`: Сообщение об ошибке (при неудаче)

### Типичные ошибки:

1. **Неверный путь**: `"Path traversal (..) is not allowed"`
2. **Файл существует**: `"File already exists: ai/notes.md"`
3. **Файл не найден**: `"File does not exist: ai/notes.md"`
4. **Попытка выхода за пределы БЗ**: `"Path must be within knowledge base root: /path/to/kb"`
5. **Попытка удалить корень БЗ**: `"Cannot delete knowledge base root folder"`

## Интеграция с AgentFactory

`AgentFactory` автоматически передает настройки файлового управления:

```python
config = {
    "enable_file_management": settings.AGENT_ENABLE_FILE_MANAGEMENT,
    "enable_folder_management": settings.AGENT_ENABLE_FOLDER_MANAGEMENT,
    "kb_path": settings.KB_PATH,
    # ... другие настройки
}
```

## Логирование

Все операции логируются:

```
INFO: Created file: ai/notes.md
INFO: Edited file: tech/python.md
INFO: Deleted file: old/deprecated.md
INFO: Moved file: ai/old.md -> ai/new.md
INFO: Created folder: ai/new-topic
INFO: Deleted folder: ai/old-topic
INFO: Moved folder: ai/old -> ai/new
```

## Технические детали

### Проверка безопасности путей

```python
def _validate_safe_path(self, relative_path: str) -> tuple[bool, Optional[Path], str]:
    """
    Проверяет безопасность пути:
    1. Удаляет начальные слеши
    2. Проверяет на path traversal (..)
    3. Преобразует в абсолютный путь
    4. Проверяет, что путь внутри корня БЗ
    """
```

### Корневой путь БЗ

При инициализации агента:
```python
self.kb_root_path = kb_root_path or Path("./knowledge_base")
self.kb_root_path = self.kb_root_path.resolve()  # Абсолютный путь
```

Все относительные пути разрешаются относительно `kb_root_path`.

## Рекомендации

1. **Используйте осмысленные пути**: `ai/machine-learning/transformers.md`
2. **Создавайте иерархию папок**: категория → подкатегория → файл
3. **Используйте описательные имена**: `bert-architecture.md`, а не `doc1.md`
4. **Группируйте связанный контент**: все файлы по теме в одной папке
5. **Регулярно реорганизуйте**: используйте `folder_move` для улучшения структуры

## Ограничения

1. Работа только с текстовыми файлами (UTF-8)
2. Нет версионирования на уровне инструментов (используйте Git)
3. Нет блокировок файлов (возможны race conditions)
4. Нет квот на размер или количество файлов
5. Операции не атомарны для множественных файлов

## Будущие улучшения

- [ ] Batch операции (множественное создание/удаление)
- [ ] Поиск файлов по шаблону
- [ ] Чтение содержимого файла
- [ ] Копирование файлов/папок
- [ ] Получение списка файлов в директории
- [ ] Проверка существования файла/папки
- [ ] Получение метаданных файла (размер, дата изменения)
