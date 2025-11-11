# Docling Model Path Fix - Объяснение проблемы и решения

## Проблема

Docling не мог найти модели, выдавая ошибку:
```
Missing Docling model artefact '/opt/docling-mcp/models/model.safetensors'
```

Хотя модели были скачаны в правильные подпапки:
```
/opt/docling-mcp/models/docling-project--docling-layout-heron-101/model.safetensors
```

## Причина

### Как Docling на самом деле работает

После изучения исходного кода Docling (файл `docling/models/layout_model.py`), выяснилось, что Docling строит пути к моделям следующим образом:

```python
# Из docling/models/layout_model.py, строки 68-79
if (artifacts_path / model_repo_folder).exists():
    artifacts_path = artifacts_path / model_repo_folder / model_path
elif (artifacts_path / model_path).exists():
    artifacts_path = artifacts_path / model_path
```

Docling ожидает:
- `artifacts_path` = базовая директория моделей (например, `/opt/docling-mcp/models`)
- `model_repo_folder` = **относительный** путь к папке модели (например, `docling-project--docling-layout-heron-101`)
- `model_path` = **пустая строка** или относительный путь внутри `model_repo_folder`

### Что делал старый код (НЕПРАВИЛЬНО)

Функция `_fix_model_path()` пыталась "исправить" пути, устанавливая `model_path` в **абсолютный** путь:

```python
# СТАРЫЙ НЕПРАВИЛЬНЫЙ КОД
model_dir_str = str((models_base / folder_path).resolve())
setattr(model_spec_or_options, "model_path", model_dir_str)
# model_path = "/opt/docling-mcp/models/docling-project--docling-layout-heron-101"
```

Это **ломало** логику Docling, потому что:
1. Docling пытался построить путь как `artifacts_path / model_repo_folder / model_path`
2. Получалось что-то вроде `/opt/docling-mcp/models/docling-project--docling-layout-heron-101//opt/docling-mcp/models/docling-project--docling-layout-heron-101`
3. Или Docling игнорировал `model_path` и искал модель прямо в `artifacts_path`

### Правильные значения из исходного Docling

Из файла `docling/datamodel/layout_model_specs.py`:

```python
DOCLING_LAYOUT_HERON_101 = LayoutModelConfig(
    name="docling_layout_heron_101",
    repo_id="docling-project/docling-layout-heron-101",
    revision="main",
    model_path="",  # <--- ПУСТАЯ СТРОКА!
)
```

## Решение

### Новый код (ПРАВИЛЬНО)

Переписал функцию `_fix_model_path()` так, чтобы она:

1. **Проверяет**, что `model_repo_folder` и `repo_cache_folder` остаются **относительными**
2. **Проверяет**, что `model_path` остается **пустым** или относительным (НЕ абсолютным)
3. **Исправляет** только в случае, если кто-то случайно установил абсолютные пути

```python
# НОВЫЙ ПРАВИЛЬНЫЙ КОД
def _fix_model_path(...):
    # Убедиться, что folder_path относительный
    if Path(folder_path).is_absolute():
        folder_path = Path(folder_path).name
        setattr(model_spec_or_options, folder_attr, folder_path)
    
    # Убедиться, что model_path пустой или относительный
    if hasattr(model_spec_or_options, "model_path"):
        current_model_path = getattr(model_spec_or_options, "model_path")
        if current_model_path and Path(current_model_path).is_absolute():
            setattr(model_spec_or_options, "model_path", "")
```

### Как теперь работает

1. `artifacts_path` = `/opt/docling-mcp/models` (из настроек)
2. `model_repo_folder` = `docling-project--docling-layout-heron-101` (относительный)
3. `model_path` = `""` (пустая строка)
4. Docling строит путь: `/opt/docling-mcp/models/docling-project--docling-layout-heron-101/`
5. Находит `model.safetensors` в этой директории ✅

## Как проверить

После применения исправления:

1. Перезапустите контейнер docling-mcp
2. Попробуйте конвертировать документ
3. В логах должны быть сообщения:
   ```
   Model paths verified for LayoutModelConfig: 
     model_repo_folder=docling-project--docling-layout-heron-101, 
     model_path=
   ```
4. Конвертация должна пройти успешно без ошибок о missing model artefact

## Вывод

Ключевое правило при работе с Docling:

> **НЕ** устанавливайте `model_path` в абсолютный путь!
> 
> Docling ожидает `model_path` пустым или относительным внутри `model_repo_folder`.
> 
> Используйте `artifacts_path` для указания базовой директории моделей.
