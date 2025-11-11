# Исправление для Вашей Конфигурации (layout_heron_101)

## 🎯 Что было найдено

Ваш конфиг:
```yaml
pipeline:
  layout:
    preset: layout_heron_101
```

**Проблема**: `download_model_bundles()` скачивал не ту модель!

### Ваши логи показывали:
```
Returning existing local_dir `/opt/docling-mcp/models/docling-project--docling-layout-heron`
```

### Что должно было быть:
```
/opt/docling-mcp/models/docling-models--layout__heron_101
```

**Разница**:
- ❌ `docling-project--docling-layout-heron` (старый repo_id)
- ✅ `docling-models--layout__heron_101` (правильный repo_id из вашего preset)

## ✅ Что исправлено

1. **Прямая загрузка с HuggingFace** используя repo_id из вашего preset
2. **Правильная папка**: `docling-models--layout__heron_101`
3. **Graceful fallback** на кэшированные модели при сетевых ошибках
4. **Ранняя настройка environment** переменных

## 🚀 Что делать

### 1. Удалить старые модели (опционально)

```bash
# Удалить неправильные папки
docker-compose exec docling-mcp rm -rf /opt/docling-mcp/models/docling-project--*
```

### 2. Пересобрать контейнер

```bash
docker-compose down
docker-compose build docling-mcp
docker-compose up -d docling-mcp
```

### 3. Проверить логи

```bash
docker-compose logs -f docling-mcp
```

**Ожидайте увидеть**:
```
✅ Docling environment configured: DOCLING_MODELS_DIR=/opt/docling-mcp/models
✅ Downloading Docling layout bundle: preset='layout_heron_101', 
   repo_id='docling-models/layout__heron_101', 
   folder='docling-models--layout__heron_101'
✅ Downloading layout model from docling-models/layout__heron_101
✅ Model sync completed successfully
```

### 4. Проверить что модель скачалась правильно

```bash
# Проверить имя папки
docker-compose exec docling-mcp ls /opt/docling-mcp/models/
```

**Должно быть**:
```
docling-models--layout__heron_101/    ← ✅ ПРАВИЛЬНО!
```

**НЕ должно быть**:
```
docling-project--docling-layout-heron/  ← ❌ Старая неправильная папка
```

```bash
# Проверить файлы модели
docker-compose exec docling-mcp ls /opt/docling-mcp/models/docling-models--layout__heron_101/
```

**Ожидаемый результат**:
```
model.safetensors
config.json
preprocessor_config.json
```

### 5. Протестировать конвертацию

Отправьте PDF в ваш Telegram бот - должно заработать! 🎉

## 📊 Техническая информация

### Почему была ошибка

```python
# Старый код (НЕПРАВИЛЬНО)
download_model_bundles(output_dir=base_dir, with_layout=True)
# ↓
# Скачивал: docling-project/docling-layout-heron (встроенный repo_id)
# Папка: docling-project--docling-layout-heron

# LayoutModel искал:
model_repo_folder = "docling-models--layout__heron_101"  # Из вашего preset
# Путь: /opt/docling-mcp/models/docling-models--layout__heron_101

# Проверка:
if (artifacts_path / model_repo_folder).exists():  # False!
    # Папка не найдена
else:
    artifacts_path = artifacts_path / model_path  # = /opt/docling-mcp/models/
    # LayoutPredictor ищет: /opt/docling-mcp/models/model.safetensors
    # ERROR: FileNotFoundError!
```

### Как исправлено

```python
# Новый код (ПРАВИЛЬНО)
layout_spec = _LAYOUT_PRESET_MAP["layout_heron_101"]
repo_id = layout_spec.repo_id  # "docling-models/layout__heron_101"
model_repo_folder = layout_spec.model_repo_folder  # "docling-models--layout__heron_101"

# Прямая загрузка с HuggingFace
target_dir = base_dir / model_repo_folder
_snapshot_download_with_hf_transfer_fallback(
    repo_id=repo_id,  # ← Правильный repo_id из preset!
    target_dir=target_dir,
)
# ↓
# Скачивает: docling-models/layout__heron_101
# Папка: docling-models--layout__heron_101

# LayoutModel ищет:
model_repo_folder = "docling-models--layout__heron_101"
# Проверка:
if (artifacts_path / model_repo_folder).exists():  # True! ✅
    artifacts_path = artifacts_path / model_repo_folder
    # = /opt/docling-mcp/models/docling-models--layout__heron_101
    # LayoutPredictor ищет: .../docling-models--layout__heron_101/model.safetensors
    # SUCCESS! ✅
```

## 🔍 Диагностика

### Если всё ещё не работает

1. **Проверьте environment переменные**:
   ```bash
   docker-compose exec docling-mcp env | grep DOCLING
   ```
   
   Должно быть:
   ```
   DOCLING_MODELS_DIR=/opt/docling-mcp/models
   DOCLING_ARTIFACTS_PATH=/opt/docling-mcp/models
   DOCLING_CACHE_DIR=/opt/docling-mcp/cache
   ```

2. **Принудительная перезагрузка моделей**:
   ```bash
   docker-compose exec docling-mcp python -m tg_docling.model_sync --force
   ```

3. **Проверьте что файлы действительно скачались**:
   ```bash
   docker-compose exec docling-mcp find /opt/docling-mcp/models -name "*.safetensors"
   ```
   
   Должно показать:
   ```
   /opt/docling-mcp/models/docling-models--layout__heron_101/model.safetensors
   ```

### Если есть сетевые ошибки

Наш fix **обрабатывает сетевые ошибки**:
- Если модели уже скачаны, использует кэш
- Если нет - сообщит понятную ошибку

## 📁 Измененные файлы

```
docker/docling-mcp/app/tg_docling/
├── env_setup.py         (NEW) - Ранняя настройка environment
├── model_sync.py        (MOD) - Прямая загрузка с HuggingFace
├── server.py            (MOD) - Импорт env_setup
├── tools.py             (MOD) - Импорт env_setup
├── config.py            (MOD) - Импорт env_setup
└── converter.py         (MOD) - Импорт env_setup
```

## ✨ Что изменится

- ✅ Модели скачаются в **правильную папку**
- ✅ LayoutModel **найдет модели**
- ✅ Конвертация **заработает**
- ✅ Сетевые ошибки **обрабатываются gracefully**
- ✅ Логи покажут **правильную информацию**

## 🎉 Результат

**До**: `FileNotFoundError: /opt/docling-mcp/models/model.safetensors`  
**После**: Успешная конвертация документов! 🚀

---

**Вопросы?** Смотрите детальную документацию:
- `CRITICAL_FIX.md` - Техническй анализ
- `VERIFICATION_FOR_HERON_101.md` - Верификация для вашего preset
- `FINAL_SOLUTION.md` - Общее резюме
