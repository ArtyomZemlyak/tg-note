# Минимальная установка Docling для загрузки моделей

Этот способ позволяет использовать весь существующий код загрузки моделей из `docker/docling-mcp/app/tg_docling/model_sync.py` без установки тяжелых зависимостей.

---

## 🎯 Что устанавливается

**Устанавливается:**
- ✅ `docling` (базовая версия)
- ✅ `huggingface-hub` (для загрузки)
- ✅ `hf-transfer` (для ускорения)
- ✅ Базовые утилиты (pydantic, pyyaml, requests, tqdm)

**НЕ устанавливается:**
- ❌ OCR движки (easyocr, rapidocr, tesserocr, onnxtr)
- ❌ Deep learning фреймворки (transformers, accelerate)
- ❌ GPU рантаймы (onnxruntime-gpu)
- ❌ VLM модели
- ❌ Обработка изображений (opencv-python)

**Размер установки:** ~100-200 MB вместо ~5-10 GB

---

## 🚀 Быстрый старт

### Шаг 1: Установка минимальных зависимостей

```bash
pip install -r requirements-model-download.txt
```

### Шаг 2: Загрузка моделей

```bash
python scripts/download_docling_models.py
```

Готово! Скрипт использует ваш `config.yaml` и загружает только те модели, которые там указаны.

---

## 📋 Подробная инструкция

### Вариант 1: Используя скрипт (рекомендуется)

```bash
# 1. Установить минимальные зависимости
pip install -r requirements-model-download.txt

# 2. Убедиться что config.yaml существует
# Если нет, создать из примера:
cp config.example.yaml config.yaml

# 3. Запустить загрузку
python scripts/download_docling_models.py

# 4. Принудительная перезагрузка (если нужно)
python scripts/download_docling_models.py --force

# 5. Использовать другой конфиг
python scripts/download_docling_models.py --config /path/to/config.yaml

# 6. Подробный вывод
python scripts/download_docling_models.py --verbose
```

### Вариант 2: Прямой вызов model_sync.py

```bash
# 1. Установить зависимости
pip install -r requirements-model-download.txt

# 2. Добавить пути в PYTHONPATH
export PYTHONPATH="$PWD:$PWD/docker/docling-mcp/app:$PYTHONPATH"

# 3. Запустить model_sync напрямую
cd docker/docling-mcp/app
python -m tg_docling.model_sync

# Или с force:
python -m tg_docling.model_sync --force
```

---

## ⚙️ Настройка в config.yaml

Скрипт читает настройки из `config.yaml` (секция `MEDIA_PROCESSING_DOCLING`):

```yaml
MEDIA_PROCESSING_DOCLING:
  model_cache:
    base_dir: /opt/docling-mcp/models  # Куда скачивать модели
    
    builtin_models:
      # Включить/выключить модели
      layout: true                # Layout analysis (~500 MB)
      tableformer: true           # Table extraction (~700 MB)
      code_formula: true          # Code & formula detection (~400 MB)
      picture_classifier: true    # Picture classification (~300 MB)
      
      rapidocr:
        enabled: true             # RapidOCR models (~400 MB)
        backends:
          - onnxruntime           # Выбрать бэкенды
      
      easyocr: false              # EasyOCR (не включать без установки easyocr)
      smolvlm: false              # VLM модели (не включать без transformers)
      granitedocling: false       # VLM модели
      smoldocling: false          # VLM модели
      granite_vision: false       # VLM модели
    
    downloads: []                 # Дополнительные загрузки (HuggingFace/ModelScope)
```

**Важно:** Отключите VLM модели если не планируете их использовать - они очень большие!

---

## 🔧 Примеры использования

### Загрузить только базовые модели

```yaml
# config.yaml
MEDIA_PROCESSING_DOCLING:
  model_cache:
    base_dir: ./models
    builtin_models:
      layout: true
      tableformer: true
      code_formula: true
      picture_classifier: true
      rapidocr:
        enabled: true
        backends:
          - onnxruntime
      # Всё остальное отключено
      easyocr: false
      smolvlm: false
      granitedocling: false
      smoldocling: false
      granite_vision: false
```

```bash
python scripts/download_docling_models.py
```

### Загрузить только RapidOCR

```yaml
# config.yaml
MEDIA_PROCESSING_DOCLING:
  model_cache:
    base_dir: ./models
    builtin_models:
      layout: false
      tableformer: false
      code_formula: false
      picture_classifier: false
      rapidocr:
        enabled: true
        backends:
          - onnxruntime
          - torch
```

```bash
python scripts/download_docling_models.py
```

### Загрузить с custom HuggingFace repo

```yaml
# config.yaml
MEDIA_PROCESSING_DOCLING:
  model_cache:
    base_dir: ./models
    builtin_models:
      # ... базовые модели ...
    downloads:
      - name: my_custom_model
        type: huggingface
        repo_id: myorg/mymodel
        revision: main
        local_dir: custom_models
        allow_patterns:
          - "*.bin"
          - "*.json"
```

```bash
python scripts/download_docling_models.py
```

---

## 📊 Размеры моделей

| Модель | Размер | Назначение |
|--------|--------|-----------|
| layout | ~500 MB | Анализ структуры документа |
| tableformer | ~700 MB | Извлечение таблиц |
| code_formula | ~400 MB | Детекция кода и формул |
| picture_classifier | ~300 MB | Классификация изображений |
| rapidocr | ~400 MB | OCR (распознавание текста) |
| easyocr | ~1-2 GB | Альтернативный OCR |
| smolvlm | ~2-3 GB | Vision-Language модель |
| granitedocling | ~3-5 GB | VLM для документов |

**Минимальная установка:** layout + tableformer + code_formula + picture_classifier + rapidocr = **~2.3 GB**

---

## ✅ Проверка результата

После загрузки проверьте:

```bash
# Список загруженных файлов
ls -lh /opt/docling-mcp/models

# Структура директории
tree /opt/docling-mcp/models -L 2

# Размер
du -sh /opt/docling-mcp/models
```

Должны появиться папки для каждой включенной модели:
```
/opt/docling-mcp/models/
├── layout/
├── tableformer/
├── code_formula_detection/
├── picture_classifier/
└── RapidOcr/
```

---

## 🐛 Troubleshooting

### ImportError: No module named 'docling'

**Решение:** Установите зависимости:
```bash
pip install -r requirements-model-download.txt
```

### ModuleNotFoundError: No module named 'tg_docling'

**Решение:** Запускайте из корня проекта:
```bash
cd /workspace
python scripts/download_docling_models.py
```

### Config file not found

**Решение:** Создайте config.yaml:
```bash
cp config.example.yaml config.yaml
# Затем отредактируйте под себя
```

### Permission denied для /opt/docling-mcp/models

**Решение 1:** Создайте директорию с правами:
```bash
sudo mkdir -p /opt/docling-mcp/models
sudo chown -R $USER:$USER /opt/docling-mcp/models
```

**Решение 2:** Используйте локальную директорию:
```yaml
# config.yaml
MEDIA_PROCESSING_DOCLING:
  model_cache:
    base_dir: ./models  # Локальная папка
```

### Загрузка зависает

**Решение:** Отключите hf-transfer:
```bash
export HF_HUB_ENABLE_HF_TRANSFER=0
python scripts/download_docling_models.py
```

### Ошибка "Cannot download model"

**Решение:** Проверьте интернет и авторизацию:
```bash
# Если модель требует авторизации
huggingface-cli login

# Проверить доступ
ping huggingface.co
```

---

## 🆚 Сравнение методов

| Метод | Размер установки | Использует наш код | Гибкость | Скорость |
|-------|-----------------|-------------------|----------|----------|
| **Минимальный docling** | ~100-200 MB | ✅ Да | ⭐⭐⭐ | ⭐⭐⭐ |
| huggingface-cli | ~50 MB | ❌ Нет | ⭐⭐ | ⭐⭐⭐ |
| Полный docling | ~5-10 GB | ✅ Да | ⭐⭐⭐ | ⭐⭐ |

**Рекомендация:** Используйте минимальный docling - лучший баланс!

---

## 💡 Преимущества этого метода

1. ✅ **Использует весь существующий код** - `model_sync.py`, `converter.py`, вся логика проекта
2. ✅ **Минимальные зависимости** - только то что нужно для загрузки
3. ✅ **Читает config.yaml** - одна конфигурация для всего проекта
4. ✅ **Поддерживает все настройки** - builtin models, custom downloads, ModelScope
5. ✅ **Подробный лог** - видно что происходит на каждом этапе
6. ✅ **Быстро** - использует hf-transfer автоматически

---

## 🔗 Связанные файлы

- `requirements-model-download.txt` - минимальные зависимости
- `scripts/download_docling_models.py` - скрипт загрузки
- `docker/docling-mcp/app/tg_docling/model_sync.py` - основная логика
- `config.yaml` - конфигурация (создать из `config.example.yaml`)

---

## 📝 Что делать после загрузки

После загрузки моделей:

1. **Для локального использования:** Модели готовы, можно запускать docling-mcp контейнер
2. **Для Docker:** Убедитесь что volume смонтирован правильно в `docker-compose.yml`:
   ```yaml
   volumes:
     - ./models:/opt/docling-mcp/models:ro
   ```
3. **Отключите startup_sync:** Если модели уже загружены:
   ```yaml
   MEDIA_PROCESSING_DOCLING:
     startup_sync: false  # Не перезагружать при старте
   ```

---

## 🎉 Готово!

Теперь у вас есть минимальная установка docling, которая использует весь ваш код для загрузки моделей!

```bash
# Установить
pip install -r requirements-model-download.txt

# Загрузить модели
python scripts/download_docling_models.py

# Наслаждаться! 🚀
```
