# Быстрая загрузка моделей Docling

## Проблема
Модели Docling не загружаются или зависают при загрузке через стандартный механизм.

## Решение
Загрузить модели вручную через `huggingface-cli` с использованием `hf-transfer` для ускорения.

---

## 🚀 Быстрый старт

### Вариант 1: Автоматический скрипт (рекомендуется)

```bash
# 1. Установить зависимости
pip install huggingface-hub hf-transfer

# 2. Запустить скрипт
bash download_docling_models.sh /opt/docling-mcp/models
```

### Вариант 2: Одна команда (копировать и выполнить)

```bash
pip install huggingface-hub hf-transfer && \
export HF_HUB_ENABLE_HF_TRANSFER=1 && \
mkdir -p /opt/docling-mcp/models && \
cd /opt/docling-mcp/models && \
huggingface-cli download DS4SD/docling-models --include "layout/*" --local-dir . --local-dir-use-symlinks False && \
huggingface-cli download DS4SD/docling-models --include "tableformer/*" --local-dir . --local-dir-use-symlinks False && \
huggingface-cli download DS4SD/docling-models --include "code_formula_detection/*" --local-dir . --local-dir-use-symlinks False && \
huggingface-cli download DS4SD/docling-models --include "picture_classifier/*" --local-dir . --local-dir-use-symlinks False && \
huggingface-cli download RapidAI/RapidOCR --include "RapidOcr/onnx/PP-OCRv4/*" --local-dir . --local-dir-use-symlinks False
```

---

## 📋 Подробная инструкция

### Шаг 1: Установка зависимостей

Нужны только `huggingface-hub` и `hf-transfer`:

```bash
pip install huggingface-hub hf-transfer
```

**Примечание**: Это минимальные зависимости. Не нужно устанавливать сам `docling` и его тяжёлые зависимости.

### Шаг 2: Включить hf-transfer

```bash
export HF_HUB_ENABLE_HF_TRANSFER=1
```

Это включит многопоточную загрузку для ускорения процесса.

### Шаг 3: Создать директорию для моделей

```bash
mkdir -p /opt/docling-mcp/models
cd /opt/docling-mcp/models
```

**Для Docker**: Убедитесь, что эта директория смонтирована как volume.

### Шаг 4: Загрузить модели

#### Layout Model (анализ структуры документа)
```bash
huggingface-cli download DS4SD/docling-models \
    --include "layout/*" \
    --local-dir . \
    --local-dir-use-symlinks False
```

#### TableFormer (распознавание таблиц)
```bash
huggingface-cli download DS4SD/docling-models \
    --include "tableformer/*" \
    --local-dir . \
    --local-dir-use-symlinks False
```

#### Code & Formula Detection (код и формулы)
```bash
huggingface-cli download DS4SD/docling-models \
    --include "code_formula_detection/*" \
    --local-dir . \
    --local-dir-use-symlinks False
```

#### Picture Classifier (классификация изображений)
```bash
huggingface-cli download DS4SD/docling-models \
    --include "picture_classifier/*" \
    --local-dir . \
    --local-dir-use-symlinks False
```

#### RapidOCR Models (OCR для текста)
```bash
huggingface-cli download RapidAI/RapidOCR \
    --include "RapidOcr/onnx/PP-OCRv4/*" \
    --local-dir . \
    --local-dir-use-symlinks False
```

---

## ✅ Проверка результата

После загрузки проверьте содержимое:

```bash
ls -lh /opt/docling-mcp/models
```

Должны появиться следующие директории:
```
layout/
tableformer/
code_formula_detection/
picture_classifier/
RapidOcr/
```

Общий размер: **около 2-3 GB**

---

## 🔧 Дополнительные опции

### Загрузка в другую директорию

Замените `/opt/docling-mcp/models` на нужный путь:

```bash
bash download_docling_models.sh /путь/к/вашей/папке
```

или в командах вручную:

```bash
mkdir -p /путь/к/вашей/папке
cd /путь/к/вашей/папке
# ... далее команды загрузки
```

### Использование с Docker

Если запускаете внутри Docker контейнера:

```bash
# Войти в контейнер
docker exec -it docling-mcp bash

# Внутри контейнера выполнить команды
pip install huggingface-hub hf-transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
cd /opt/docling-mcp/models
# ... команды загрузки
```

Или смонтировать volume и загрузить снаружи:

```bash
# На хосте
mkdir -p ./docling-models
cd ./docling-models

# Загрузить модели
pip install huggingface-hub hf-transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
# ... команды загрузки

# Затем в docker-compose.yml:
# volumes:
#   - ./docling-models:/opt/docling-mcp/models
```

---

## 🐛 Troubleshooting

### Загрузка зависает

**Решение 1**: Отключить hf-transfer
```bash
export HF_HUB_ENABLE_HF_TRANSFER=0
```

**Решение 2**: Загружать модели по одной
```bash
# Загружать каждую модель отдельно, дожидаясь завершения
```

**Решение 3**: Проверить интернет соединение
```bash
ping huggingface.co
```

### Ошибка доступа

Некоторые модели могут требовать авторизации:

```bash
huggingface-cli login
```

Затем введите токен от HuggingFace (получить можно на https://huggingface.co/settings/tokens)

### Не хватает места

Проверьте свободное место:

```bash
df -h /opt/docling-mcp/models
```

Нужно минимум **5 GB** свободного места.

### Permission denied

Если нет прав на запись:

```bash
sudo mkdir -p /opt/docling-mcp/models
sudo chown -R $USER:$USER /opt/docling-mcp/models
```

---

## 📝 Что делают эти модели

| Модель | Назначение | Размер |
|--------|-----------|--------|
| Layout | Анализ структуры документа (заголовки, абзацы, списки) | ~500 MB |
| TableFormer | Распознавание и извлечение таблиц | ~700 MB |
| Code & Formula | Детекция кода и математических формул | ~400 MB |
| Picture Classifier | Классификация типов изображений | ~300 MB |
| RapidOCR | OCR (распознавание текста на изображениях) | ~400 MB |

---

## 🔗 Ссылки

- [Docling GitHub](https://github.com/DS4SD/docling)
- [HuggingFace CLI](https://huggingface.co/docs/huggingface_hub/guides/cli)
- [hf-transfer](https://github.com/huggingface/hf_transfer)
- [Модели Docling на HuggingFace](https://huggingface.co/DS4SD/docling-models)
- [RapidOCR](https://huggingface.co/RapidAI/RapidOCR)

---

## 💡 Советы

1. **Используйте hf-transfer** - это значительно ускоряет загрузку (в 5-10 раз)
2. **Загружайте ночью** - если интернет медленный
3. **Проверяйте MD5** - если боитесь повреждения файлов при передаче
4. **Используйте кеш** - huggingface-cli кеширует модели в `~/.cache/huggingface/`

---

## ⚙️ Интеграция с проектом

После загрузки моделей убедитесь, что в `config.yaml` указан правильный путь:

```yaml
MEDIA_PROCESSING_DOCLING:
  model_cache:
    base_dir: /opt/docling-mcp/models
    builtin_models:
      layout: true
      tableformer: true
      code_formula: true
      picture_classifier: true
      rapidocr:
        enabled: true
        backends:
          - onnxruntime
```

Если модели уже загружены, можно отключить автозагрузку при старте:

```yaml
MEDIA_PROCESSING_DOCLING:
  startup_sync: false  # Не загружать при старте
```

---

Готово! Модели должны загрузиться быстро и без зависаний. 🎉
