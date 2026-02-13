# 📥 Docling Models Download - Cheat Sheet

## 🚀 SUPER QUICK (одна команда)

```bash
bash INSTALL_AND_DOWNLOAD.sh
```

**Что делает:**
1. Создаёт `config.yaml` из примера (если нет)
2. Устанавливает минимальные зависимости
3. Тестирует установку
4. Загружает все модели согласно `config.yaml`

---

## ⚡ QUICK (три команды)

```bash
# 1. Установить минимальные зависимости
pip install -r requirements-model-download.txt

# 2. Создать config.yaml (если нет)
cp config.example.yaml config.yaml

# 3. Загрузить модели
python scripts/download_docling_models.py
```

---

## 📋 ПОШАГОВО

### 1️⃣ Установка

```bash
# Минимальная установка (100-200 MB)
pip install -r requirements-model-download.txt

# Проверить установку
python scripts/test_model_download_setup.py
```

### 2️⃣ Конфигурация

```bash
# Создать config.yaml
cp config.example.yaml config.yaml

# Отредактировать (опционально)
nano config.yaml
```

**Важные настройки:**
```yaml
MEDIA_PROCESSING_DOCLING:
  model_cache:
    base_dir: /opt/docling-mcp/models  # Куда скачивать
    builtin_models:
      layout: true              # ~500 MB
      tableformer: true         # ~700 MB  
      code_formula: true        # ~400 MB
      picture_classifier: true  # ~300 MB
      rapidocr:
        enabled: true           # ~400 MB
```

### 3️⃣ Загрузка

```bash
# Обычная загрузка
python scripts/download_docling_models.py

# Принудительная перезагрузка
python scripts/download_docling_models.py --force

# С подробным выводом
python scripts/download_docling_models.py --verbose

# С другим конфигом
python scripts/download_docling_models.py --config /path/to/config.yaml
```

---

## 🎯 АЛЬТЕРНАТИВА: huggingface-cli (без проекта)

```bash
# Установка
pip install huggingface-hub hf-transfer

# Включить ускорение
export HF_HUB_ENABLE_HF_TRANSFER=1

# Создать папку
mkdir -p /opt/docling-mcp/models
cd /opt/docling-mcp/models

# Загрузить (выберите нужные модели)
huggingface-cli download DS4SD/docling-models --include "layout/*" --local-dir . --local-dir-use-symlinks False
huggingface-cli download DS4SD/docling-models --include "tableformer/*" --local-dir . --local-dir-use-symlinks False
huggingface-cli download DS4SD/docling-models --include "code_formula_detection/*" --local-dir . --local-dir-use-symlinks False
huggingface-cli download DS4SD/docling-models --include "picture_classifier/*" --local-dir . --local-dir-use-symlinks False
huggingface-cli download RapidAI/RapidOCR --include "RapidOcr/onnx/PP-OCRv4/*" --local-dir . --local-dir-use-symlinks False
```

Или используйте скрипт:
```bash
bash download_docling_models.sh /opt/docling-mcp/models
```

---

## 📊 МОДЕЛИ

| Модель | Размер | Обязательна? | Назначение |
|--------|--------|-------------|-----------|
| **layout** | ~500 MB | ⚠️ Рекомендуется | Анализ структуры документа |
| **tableformer** | ~700 MB | ⚠️ Рекомендуется | Извлечение таблиц |
| **code_formula** | ~400 MB | ✅ Опционально | Детекция кода и формул |
| **picture_classifier** | ~300 MB | ✅ Опционально | Классификация изображений |
| **rapidocr** | ~400 MB | ⚠️ Рекомендуется | OCR (распознавание текста) |
| easyocr | ~1-2 GB | ❌ Опционально | Альтернативный OCR |
| VLM модели | ~2-5 GB | ❌ Опционально | Vision-Language модели |

**Минимум:** layout + tableformer + rapidocr = **~1.6 GB**  
**Рекомендуется:** все базовые = **~2.3 GB**

---

## ✅ ПРОВЕРКА

```bash
# Список файлов
ls -lh /opt/docling-mcp/models

# Структура
tree /opt/docling-mcp/models -L 2

# Размер
du -sh /opt/docling-mcp/models

# Ожидаемая структура:
# /opt/docling-mcp/models/
# ├── layout/
# ├── tableformer/
# ├── code_formula_detection/
# ├── picture_classifier/
# └── RapidOcr/
```

---

## 🐛 TROUBLESHOOTING

| Проблема | Решение |
|----------|---------|
| `No module named 'docling'` | `pip install -r requirements-model-download.txt` |
| `Config file not found` | `cp config.example.yaml config.yaml` |
| `Permission denied` | `sudo chown -R $USER:$USER /opt/docling-mcp/models` |
| Загрузка зависает | `export HF_HUB_ENABLE_HF_TRANSFER=0` |
| Нужна авторизация | `huggingface-cli login` |

---

## 🔧 НАСТРОЙКА ПОСЛЕ ЗАГРУЗКИ

### Docker

```yaml
# docker-compose.yml
volumes:
  - ./models:/opt/docling-mcp/models:ro
```

### Config

```yaml
# config.yaml
MEDIA_PROCESSING_DOCLING:
  startup_sync: false  # Не перезагружать при старте (модели уже есть)
```

---

## 📁 ФАЙЛЫ

| Файл | Назначение |
|------|-----------|
| `INSTALL_AND_DOWNLOAD.sh` | **Всё в одном: установка + загрузка** |
| `scripts/download_docling_models.py` | **Основной скрипт загрузки** |
| `scripts/test_model_download_setup.py` | Тест установки |
| `download_docling_models.sh` | Bash скрипт (huggingface-cli) |
| `requirements-model-download.txt` | Минимальные зависимости |
| `MINIMAL_DOCLING_INSTALL.md` | 📖 Подробная инструкция |
| `DOWNLOAD_MODELS_README_RU.md` | 📖 Инструкция huggingface-cli |
| `MODEL_DOWNLOAD_CHEATSHEET.md` | 📄 Эта шпаргалка |
| `QUICK_MODEL_DOWNLOAD.txt` | Быстрая памятка |

---

## 💡 СОВЕТЫ

1. **Используйте минимальную установку** - установить docling для загрузки = 100-200 MB
2. **Включайте hf-transfer** - загрузка быстрее в 5-10 раз
3. **Отключайте VLM модели** - если не нужны, они очень большие (2-5 GB каждая)
4. **Проверяйте config.yaml** - убедитесь что пути правильные
5. **Используйте --force** - если нужно перезагрузить модели
6. **Отключайте startup_sync** - после первой загрузки

---

## 🎓 ПРИМЕРЫ

### Загрузить только базовые модели

```yaml
# config.yaml
builtin_models:
  layout: true
  tableformer: true
  code_formula: true
  picture_classifier: true
  rapidocr:
    enabled: true
  # Остальное false
```

```bash
python scripts/download_docling_models.py
```

### Загрузить в локальную папку

```yaml
# config.yaml
model_cache:
  base_dir: ./models  # Локально
```

```bash
python scripts/download_docling_models.py
```

### Загрузить с custom HuggingFace repo

```yaml
# config.yaml
model_cache:
  downloads:
    - name: my_model
      type: huggingface
      repo_id: myorg/mymodel
      local_dir: custom
```

```bash
python scripts/download_docling_models.py
```

---

## 🆚 СРАВНЕНИЕ

| Метод | Код проекта | Размер установки | Config | Скорость |
|-------|------------|-----------------|--------|----------|
| **Минимальный docling** | ✅ | 100-200 MB | ✅ | ⚡⚡⚡ |
| huggingface-cli | ❌ | 50 MB | ❌ | ⚡⚡⚡ |
| Полный docling | ✅ | 5-10 GB | ✅ | ⚡⚡ |

**Рекомендация:** Минимальный docling - best of both worlds!

---

## 🔗 ССЫЛКИ

- [Docling GitHub](https://github.com/DS4SD/docling)
- [Модели на HuggingFace](https://huggingface.co/DS4SD/docling-models)
- [RapidOCR](https://huggingface.co/RapidAI/RapidOCR)
- [HuggingFace Hub Docs](https://huggingface.co/docs/huggingface_hub)

---

## 🎉 ГОТОВО!

```bash
# Один способ чтобы править всеми!
bash INSTALL_AND_DOWNLOAD.sh
```

Enjoy! 🚀
