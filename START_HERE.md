# 🎯 START HERE - Загрузка моделей Docling

## Проблема
Модели Docling не загружаются или зависают? Нужно загрузить модели быстро и надёжно?

## ⚡ Решение (выберите один способ)

---

### 🥇 СПОСОБ 1: Минимальный Docling (РЕКОМЕНДУЕТСЯ)

**Преимущества:**
- ✅ Использует весь код проекта (`model_sync.py`)
- ✅ Читает `config.yaml` (одна конфигурация)
- ✅ Минимальные зависимости (~100-200 MB)
- ✅ Быстро (hf-transfer)

**Одна команда:**
```bash
bash INSTALL_AND_DOWNLOAD.sh
```

**Или три команды:**
```bash
pip install -r requirements-model-download.txt
cp config.example.yaml config.yaml  # если нет
python scripts/download_docling_models.py
```

**📖 Подробнее:** [`MINIMAL_DOCLING_INSTALL.md`](MINIMAL_DOCLING_INSTALL.md)

---

### 🥈 СПОСОБ 2: huggingface-cli (БЕЗ проекта)

**Преимущества:**
- ✅ Не нужен docling
- ✅ Минимальные зависимости (~50 MB)
- ✅ Быстро (hf-transfer)

**Одна команда:**
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

**Или скрипт:**
```bash
bash download_docling_models.sh /opt/docling-mcp/models
```

**📖 Подробнее:** [`DOWNLOAD_MODELS_README_RU.md`](DOWNLOAD_MODELS_README_RU.md)

---

## 📚 Документация

| Файл | Описание |
|------|----------|
| **[MODEL_DOWNLOAD_CHEATSHEET.md](MODEL_DOWNLOAD_CHEATSHEET.md)** | 📄 **Шпаргалка** - все команды в одном месте |
| **[QUICK_MODEL_DOWNLOAD.txt](QUICK_MODEL_DOWNLOAD.txt)** | ⚡ **Быстрая памятка** - копируй и выполняй |
| [MINIMAL_DOCLING_INSTALL.md](MINIMAL_DOCLING_INSTALL.md) | 📖 Полная инструкция: минимальный docling |
| [DOWNLOAD_MODELS_README_RU.md](DOWNLOAD_MODELS_README_RU.md) | 📖 Полная инструкция: huggingface-cli |
| [DOWNLOAD_MODELS_COMMAND.txt](DOWNLOAD_MODELS_COMMAND.txt) | 📋 Все команды huggingface-cli |

---

## 🛠️ Скрипты

| Скрипт | Назначение |
|--------|-----------|
| **`INSTALL_AND_DOWNLOAD.sh`** | **🎯 Всё в одном: установка + загрузка** |
| `scripts/download_docling_models.py` | Python скрипт (использует config.yaml) |
| `scripts/test_model_download_setup.py` | Проверка установки |
| `download_docling_models.sh` | Bash скрипт (huggingface-cli) |

---

## 📦 Файлы зависимостей

| Файл | Назначение |
|------|-----------|
| `requirements-model-download.txt` | Минимальные зависимости для загрузки моделей |

---

## ⚡ TL;DR

**Самый простой способ:**
```bash
bash INSTALL_AND_DOWNLOAD.sh
```

**Самый быстрый способ (если есть huggingface-cli):**
```bash
bash download_docling_models.sh /opt/docling-mcp/models
```

**Для разработчиков (с config.yaml):**
```bash
pip install -r requirements-model-download.txt
python scripts/download_docling_models.py
```

---

## 📊 Что будет загружено

| Модель | Размер | Описание |
|--------|--------|----------|
| layout | ~500 MB | Анализ структуры документа |
| tableformer | ~700 MB | Извлечение таблиц |
| code_formula | ~400 MB | Детекция кода и формул |
| picture_classifier | ~300 MB | Классификация изображений |
| rapidocr | ~400 MB | OCR (распознавание текста) |

**Итого:** ~2.3 GB (базовые модели)

---

## 🎓 Дальше

1. ✅ Загрузите модели (выберите способ выше)
2. ✅ Проверьте результат: `ls -lh /opt/docling-mcp/models`
3. ✅ Запустите docling-mcp контейнер
4. ✅ (Опционально) Отключите `startup_sync` в `config.yaml`

---

## ❓ Помощь

- **Ошибка:** Смотрите раздел "Troubleshooting" в документации
- **Вопросы:** Читайте [`MODEL_DOWNLOAD_CHEATSHEET.md`](MODEL_DOWNLOAD_CHEATSHEET.md)
- **Подробности:** Выберите нужный `.md` файл из списка выше

---

**Выберите способ и начинайте!** 🚀

Рекомендуем: [`INSTALL_AND_DOWNLOAD.sh`](./INSTALL_AND_DOWNLOAD.sh) - работает из коробки!
