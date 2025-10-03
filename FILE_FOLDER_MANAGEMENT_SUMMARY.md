# Сводка изменений: Управление файлами и папками для агента

## Что добавлено

### 1. Промпты агента обновлены (`config/agent_prompts.py`)

**QWEN_CODE_AGENT_INSTRUCTION:**
- Добавлены инструменты: `file_create`, `file_edit`, `file_delete`, `file_move`
- Добавлены инструменты: `folder_create`, `folder_delete`, `folder_move`
- Добавлены правила безопасности для работы с путями

**QWEN_CODE_CLI_AGENT_INSTRUCTION:**
- Описаны доступные операции с файлами и папками
- Добавлены правила безопасности для файловых операций
- Указано требование использовать только относительные пути

### 2. Настройки приложения (`config/settings.py`)

Добавлены новые настройки:

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

### 3. Конфигурация YAML (`config.example.yaml`)

Добавлены подробные комментарии для новых настроек:

```yaml
AGENT_ENABLE_FILE_MANAGEMENT: true
AGENT_ENABLE_FOLDER_MANAGEMENT: true
```

С описанием:
- Какие операции доступны
- Правила безопасности
- Рекомендации по использованию

### 4. Агент QwenCodeAgent (`src/agents/qwen_code_agent.py`)

#### Новые параметры конструктора:
- `enable_file_management: bool = True`
- `enable_folder_management: bool = True`
- `kb_root_path: Optional[Path] = None`

#### Метод проверки безопасности:
```python
def _validate_safe_path(self, relative_path: str) -> tuple[bool, Optional[Path], str]:
    """
    Проверяет:
    - Относительность пути
    - Отсутствие path traversal (..)
    - Нахождение внутри корня БЗ
    """
```

#### Инструменты для файлов:
- `_tool_file_create()` - создание файла
- `_tool_file_edit()` - редактирование файла
- `_tool_file_delete()` - удаление файла
- `_tool_file_move()` - перемещение/переименование файла

#### Инструменты для папок:
- `_tool_folder_create()` - создание папки
- `_tool_folder_delete()` - удаление папки (с содержимым)
- `_tool_folder_move()` - перемещение/переименование папки

### 5. Фабрика агентов (`src/agents/agent_factory.py`)

Обновлены методы:
- `_create_qwen_agent()` - передаёт новые параметры
- `from_settings()` - читает настройки из конфига

### 6. Документация (`docs/FILE_FOLDER_MANAGEMENT.md`)

Полная документация по:
- Безопасности и правилам работы с путями
- Доступным операциям с примерами
- Настройкам и интеграции
- Обработке ошибок
- Рекомендациям по использованию

## Безопасность

### ✅ Реализованные защиты:

1. **Только относительные пути**: Агент должен указывать путь относительно корня БЗ
2. **Блокировка path traversal**: Символы `..` в пути запрещены
3. **Проверка границ**: Все пути проверяются на нахождение внутри корня БЗ
4. **Защита корня БЗ**: Нельзя удалить или переместить корневую директорию
5. **Разрешение абсолютных путей**: Все пути преобразуются в абсолютные и проверяются

### Примеры:

✅ **Разрешено:**
```
"ai/notes.md"
"tech/python/tutorial.md"
"projects/myproject/README.md"
```

❌ **Запрещено:**
```
"/etc/passwd"
"../../../secrets.txt"
"C:\Windows\System32\config"
"/home/user/knowledge_base/notes.md"  # Абсолютный путь
```

## Использование

### Для агента:

Агент может выполнять операции, указывая только относительные пути:

```python
# Создать файл
file_create(path="ai/transformers.md", content="# Transformers\n...")

# Создать папку
folder_create(path="ai/new-topic")

# Переместить файл
file_move(source="general/note.md", destination="ai/note.md")

# Удалить папку
folder_delete(path="deprecated")
```

### Для пользователей:

В `config.yaml`:

```yaml
# Включить управление файлами
AGENT_ENABLE_FILE_MANAGEMENT: true

# Включить управление папками
AGENT_ENABLE_FOLDER_MANAGEMENT: true

# Путь к базе знаний
KB_PATH: ./knowledge_base
```

## Файлы изменены

1. ✅ `config/agent_prompts.py` - промпты агента
2. ✅ `config/settings.py` - настройки приложения
3. ✅ `config.example.yaml` - пример конфигурации
4. ✅ `src/agents/qwen_code_agent.py` - реализация инструментов
5. ✅ `src/agents/agent_factory.py` - интеграция с фабрикой
6. ✅ `docs/FILE_FOLDER_MANAGEMENT.md` - документация
7. ✅ `FILE_FOLDER_MANAGEMENT_SUMMARY.md` - эта сводка

## Тестирование

Для проверки синтаксиса:
```bash
python3 -m py_compile config/agent_prompts.py
python3 -m py_compile config/settings.py
python3 -m py_compile src/agents/qwen_code_agent.py
python3 -m py_compile src/agents/agent_factory.py
```

Все проверки пройдены успешно ✅

## Совместимость

- Обратная совместимость: ✅ (настройки по умолчанию включены)
- Существующие агенты: ✅ (работают без изменений)
- Новые инструменты: ✅ (опциональны, можно отключить)

## Следующие шаги

Рекомендуется:

1. Протестировать работу инструментов в изолированной среде
2. Проверить логирование операций
3. Убедиться в корректности проверки путей
4. Добавить unit-тесты для инструментов
5. Обновить документацию пользователя

## Возможные улучшения в будущем

- Batch операции (множественное создание/удаление)
- Копирование файлов и папок
- Чтение содержимого файлов
- Поиск файлов по шаблону
- Получение списка файлов в директории
- Метаданные файлов (размер, дата изменения)
