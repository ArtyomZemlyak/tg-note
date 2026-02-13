# 🆕 Docling New Repositories Guide (docling-project)

## ⚠️ ВАЖНО: Изменение структуры репозиториев!

Docling **версии 2.61.2+** использует **новые репозитории** на HuggingFace:

- ❌ **СТАРЫЕ:** `DS4SD/docling-models` (всё в одном репозитории)
- ✅ **НОВЫЕ:** `docling-project/*` (отдельный репозиторий для каждой модели)

---

## 🔍 Проблема: "Fetching 0 files"

**Ваша команда:**
```bash
huggingface-cli download docling-project/docling-layout-heron-101 \
    --include "layout/*" \
    --local-dir . --local-dir-use-symlinks False
```

**Проблема:** 
- В репозитории `docling-project/docling-layout-heron-101` **НЕТ папки** `layout/`
- Файлы лежат **в корне** репозитория
- Паттерн `layout/*` не находит файлы → 0 файлов

---

## ✅ РЕШЕНИЕ

### Вариант 1: Загрузить ВСЁ (рекомендуется)

```bash
huggingface-cli download docling-project/docling-layout-heron-101 \
    --local-dir . \
    --local-dir-use-symlinks False
```

**Без** `--include` - загрузит все файлы модели.

### Вариант 2: Загрузить только нужные типы файлов

```bash
huggingface-cli download docling-project/docling-layout-heron-101 \
    --include "*.onnx" \
    --include "*.json" \
    --include "*.txt" \
    --local-dir . \
    --local-dir-use-symlinks False
```

### Вариант 3: Проверить структуру ПЕРЕД загрузкой

```bash
# Посмотреть какие файлы есть в репозитории
python3 -c "
from huggingface_hub import list_repo_files
files = list_repo_files('docling-project/docling-layout-heron-101')
for f in files:
    print(f)
"
```

Или используйте скрипт:
```bash
bash fix_model_download.sh docling-project/docling-layout-heron-101
```

---

## 📋 Новая структура репозиториев Docling

### Layout Models
- `docling-project/docling-layout-v2` (default)
- `docling-project/docling-layout-heron`
- `docling-project/docling-layout-heron-101` ← Вы пытались загрузить это
- `docling-project/docling-layout-egret-medium`
- `docling-project/docling-layout-egret-large`
- `docling-project/docling-layout-egret-xlarge`

### TableFormer Models
- `docling-project/docling-tableformer`

### Other Models
- `docling-project/docling-code-formula-detection`
- `docling-project/docling-document-picture-classifier`

### OCR Models
- `RapidAI/RapidOCR` (отдельный проект, не изменился)

---

## 🔧 Правильная загрузка новых моделей

### Layout Heron 101 (ваш случай)

```bash
cd /home/artem/projects/tg-note/data/docling/models

# Создать папку для модели
mkdir -p layout_heron_101
cd layout_heron_101

# Загрузить модель
export HF_HUB_ENABLE_HF_TRANSFER=1
huggingface-cli download docling-project/docling-layout-heron-101 \
    --local-dir . \
    --local-dir-use-symlinks False
```

### Layout V2 (default)

```bash
mkdir -p layout_v2
cd layout_v2

huggingface-cli download docling-project/docling-layout-v2 \
    --local-dir . \
    --local-dir-use-symlinks False
```

### TableFormer

```bash
mkdir -p tableformer
cd tableformer

huggingface-cli download docling-project/docling-tableformer \
    --local-dir . \
    --local-dir-use-symlinks False
```

### Code & Formula

```bash
mkdir -p code_formula
cd code_formula

huggingface-cli download docling-project/docling-code-formula-detection \
    --local-dir . \
    --local-dir-use-symlinks False
```

### Picture Classifier

```bash
mkdir -p picture_classifier
cd picture_classifier

huggingface-cli download docling-project/docling-document-picture-classifier \
    --local-dir . \
    --local-dir-use-symlinks False
```

---

## 🆚 Сравнение старой и новой структуры

### СТАРАЯ структура (DS4SD/docling-models)

```
DS4SD/docling-models/
├── layout/
│   ├── model.onnx
│   └── config.json
├── tableformer/
│   ├── model.onnx
│   └── config.json
└── code_formula_detection/
    └── ...
```

**Загрузка:**
```bash
huggingface-cli download DS4SD/docling-models \
    --include "layout/*" \    # ✅ Работает!
    --local-dir .
```

### НОВАЯ структура (docling-project/*)

```
docling-project/docling-layout-heron-101/   (отдельный репозиторий)
├── model.onnx
├── config.json
└── preprocessor_config.json

docling-project/docling-tableformer/        (отдельный репозиторий)
├── model.onnx
└── config.json
```

**Загрузка:**
```bash
huggingface-cli download docling-project/docling-layout-heron-101 \
    --local-dir .              # ✅ Без --include!
```

---

## 🔄 Обновление скриптов загрузки

Наши скрипты уже поддерживают новые репозитории! Используйте:

```bash
python scripts/download_docling_models.py
```

Скрипт автоматически определяет правильные репозитории на основе версии docling.

---

## 💡 Советы

1. **НЕ используйте** `--include "layout/*"` для новых репозиториев
2. **Проверяйте структуру** репозитория перед загрузкой
3. **Используйте** `--local-dir-use-symlinks False` для реальных копий
4. **Включайте** `HF_HUB_ENABLE_HF_TRANSFER=1` для скорости
5. **Создавайте** отдельные папки для каждой модели

---

## 🐛 Troubleshooting

### "Fetching 0 files"

**Причина:** Неправильный паттерн `--include`

**Решение:** Уберите `--include` или используйте правильный паттерн:
```bash
# Без фильтра (лучше)
huggingface-cli download REPO --local-dir .

# Или с правильным паттерном
huggingface-cli download REPO --include "*.onnx" --include "*.json" --local-dir .
```

### "Repository not found"

**Причина:** Используете старое имя репозитория

**Решение:** Обновите на новое:
- `DS4SD/docling-models` → `docling-project/docling-layout-v2`

### "Model not working after download"

**Причина:** Неправильная структура папок

**Решение:** Убедитесь что папки соответствуют ожиданиям docling:
```
models/
├── layout/                    # Для layout моделей
├── tableformer/              # Для tableformer
└── code_formula_detection/   # Для code & formula
```

---

## ✅ Правильная команда для вашего случая

```bash
cd /home/artem/projects/tg-note/data/docling/models

# Создать папку (docling ожидает именно "layout")
mkdir -p layout
cd layout

# Загрузить модель БЕЗ --include
export HF_HUB_ENABLE_HF_TRANSFER=1
huggingface-cli download docling-project/docling-layout-heron-101 \
    --local-dir . \
    --local-dir-use-symlinks False

# Проверить
ls -lh
# Должны быть: model.onnx, config.json, etc.
```

---

## 📖 Документация

- [Docling Migration Guide](https://github.com/DS4SD/docling/releases)
- [HuggingFace Hub CLI](https://huggingface.co/docs/huggingface_hub/guides/cli)
- [hf-transfer](https://github.com/huggingface/hf_transfer)

---

**Итого:** Уберите `--include "layout/*"` и всё заработает! 🎉
