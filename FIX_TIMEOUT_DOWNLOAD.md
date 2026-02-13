# 🔧 Решение проблемы таймаута при загрузке моделей

## ❌ Проблема

```
Error while downloading from https://cas-bridge.xethub.hf.co/...
HTTPSConnectionPool(host='cas-bridge.xethub.hf.co', port=443): Read timed out.
```

**Причина:** 
- HuggingFace использует XET bridge для больших файлов
- XET bridge медленный/нестабильный
- `HF_HUB_DISABLE_XET=1` не всегда работает

---

## ✅ РЕШЕНИЕ 1: Использовать hf-transfer (ЛУЧШЕЕ)

```bash
# Установить hf-transfer (если нет)
pip install hf-transfer

# Включить hf-transfer (обходит XET)
export HF_HUB_ENABLE_HF_TRANSFER=1

# Увеличить timeout
export HF_HUB_DOWNLOAD_TIMEOUT=300

# Загрузить
huggingface-cli download docling-project/docling-layout-heron-101 \
    --local-dir ./layout \
    --local-dir-use-symlinks False
```

**Почему работает:**
- `hf-transfer` использует многопоточную загрузку
- Обходит XET bridge
- Быстрее в 5-10 раз
- Лучше обрабатывает таймауты

---

## ✅ РЕШЕНИЕ 2: Python API с retry (НАДЁЖНОЕ)

```bash
cat > download_model_retry.py << 'EOF'
#!/usr/bin/env python3
"""Download model with automatic retry on timeout"""

import time
from huggingface_hub import snapshot_download
from pathlib import Path

MODEL = "docling-project/docling-layout-heron-101"
LOCAL_DIR = "./layout"

# Enable hf-transfer
import os
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "300"

MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

for attempt in range(MAX_RETRIES):
    try:
        print(f"\n{'='*70}")
        print(f"Attempt {attempt + 1}/{MAX_RETRIES}: Downloading {MODEL}")
        print(f"{'='*70}\n")
        
        snapshot_download(
            repo_id=MODEL,
            local_dir=LOCAL_DIR,
            local_dir_use_symlinks=False,
            resume_download=True,  # Resume if interrupted
        )
        
        print(f"\n{'='*70}")
        print("✅ Download completed successfully!")
        print(f"{'='*70}\n")
        break
        
    except Exception as e:
        print(f"\n❌ Attempt {attempt + 1} failed: {e}")
        
        if attempt < MAX_RETRIES - 1:
            print(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
        else:
            print("\n❌ All attempts failed!")
            raise

# Verify download
files = list(Path(LOCAL_DIR).rglob("*"))
print(f"\nDownloaded {len(files)} files:")
for f in sorted(files)[:10]:
    print(f"  {f}")
if len(files) > 10:
    print(f"  ... and {len(files) - 10} more")
EOF

# Запустить
python3 download_model_retry.py
```

**Почему работает:**
- Автоматический retry при ошибке
- `resume_download=True` продолжает с места обрыва
- Более гибкий контроль

---

## ✅ РЕШЕНИЕ 3: Загружать файлы по одному (МЕДЛЕННОЕ, но РАБОТАЕТ)

```bash
# Получить список файлов
python3 << 'EOF'
from huggingface_hub import list_repo_files
files = list_repo_files("docling-project/docling-layout-heron-101")
for f in files:
    print(f)
EOF
```

Затем загрузить каждый файл отдельно:

```bash
# Создать директорию
mkdir -p layout

# Загрузить каждый файл
export HF_HUB_ENABLE_HF_TRANSFER=1

huggingface-cli download docling-project/docling-layout-heron-101 \
    --include "config.json" \
    --local-dir ./layout \
    --local-dir-use-symlinks False

huggingface-cli download docling-project/docling-layout-heron-101 \
    --include "preprocessor_config.json" \
    --local-dir ./layout \
    --local-dir-use-symlinks False

huggingface-cli download docling-project/docling-layout-heron-101 \
    --include "model.safetensors" \
    --local-dir ./layout \
    --local-dir-use-symlinks False

# И так далее для каждого файла
```

---

## ✅ РЕШЕНИЕ 4: Увеличить timeout + отключить XET

```bash
# Увеличить все таймауты
export HF_HUB_DOWNLOAD_TIMEOUT=600
export REQUESTS_TIMEOUT=600
export HTTP_TIMEOUT=600

# Отключить XET (может не работать)
export HF_HUB_DISABLE_XET=1
export HF_HUB_DISABLE_EXPERIMENTAL_FEATURES=1

# Включить hf-transfer как альтернативу
export HF_HUB_ENABLE_HF_TRANSFER=1

# Загрузить с resume
huggingface-cli download docling-project/docling-layout-heron-101 \
    --local-dir ./layout \
    --local-dir-use-symlinks False \
    --resume-download
```

---

## ✅ РЕШЕНИЕ 5: Использовать wget/curl напрямую

```bash
# Получить прямую ссылку
python3 << 'EOF'
from huggingface_hub import hf_hub_url, HfApi

api = HfApi()
repo = "docling-project/docling-layout-heron-101"

files = api.list_repo_files(repo)
for file in files:
    url = hf_hub_url(repo, file)
    print(f"# {file}")
    print(f"wget '{url}' -O {file}")
    print()
EOF
```

Затем использовать `wget` с retry:

```bash
wget --tries=10 --retry-connrefused --continue \
    '<DIRECT_URL>' -O model.safetensors
```

---

## 🎯 РЕКОМЕНДУЕМЫЙ ПОРЯДОК ДЕЙСТВИЙ

### 1️⃣ Попробуйте hf-transfer (БЫСТРО)

```bash
pip install hf-transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DOWNLOAD_TIMEOUT=300

huggingface-cli download docling-project/docling-layout-heron-101 \
    --local-dir ./layout \
    --local-dir-use-symlinks False
```

### 2️⃣ Если не помогло - Python с retry (НАДЁЖНО)

```bash
python3 download_model_retry.py
```

### 3️⃣ Если всё равно падает - по файлам (МЕДЛЕННО)

Загружайте файлы по одному (см. РЕШЕНИЕ 3)

---

## 🔍 Диагностика

### Проверить что hf-transfer установлен и работает:

```bash
python3 -c "
import hf_transfer
print('✅ hf_transfer installed:', hf_transfer.__version__)
"
```

### Проверить переменные окружения:

```bash
echo "HF_HUB_ENABLE_HF_TRANSFER=$HF_HUB_ENABLE_HF_TRANSFER"
echo "HF_HUB_DOWNLOAD_TIMEOUT=$HF_HUB_DOWNLOAD_TIMEOUT"
echo "HF_HUB_DISABLE_XET=$HF_HUB_DISABLE_XET"
```

### Проверить скорость интернета к HuggingFace:

```bash
curl -w "%{speed_download}\n" -o /dev/null -s \
    https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/transformers/model_doc/bert_architecture.png
```

---

## 💡 Дополнительные советы

1. **Загружайте ночью** - меньше нагрузка на серверы HuggingFace
2. **Используйте VPN** - если проблемы с доступом к cas-bridge.xethub.hf.co
3. **Проверьте файрволл** - может блокировать XET bridge
4. **Очистите кеш** - `rm -rf ~/.cache/huggingface/downloads/*`
5. **Обновите huggingface-hub** - `pip install --upgrade huggingface-hub`

---

## 🐛 Если ничего не помогает

### Вариант A: Скачать из зеркала (если доступно)

Некоторые модели есть на ModelScope:

```bash
pip install modelscope
python3 << 'EOF'
from modelscope.hub.snapshot_download import snapshot_download

snapshot_download(
    'your-model-id',  # Если есть на ModelScope
    cache_dir='./layout'
)
EOF
```

### Вариант B: Запросить помощь сообщества

Создайте issue на GitHub:
- https://github.com/DS4SD/docling/issues
- https://github.com/huggingface/huggingface_hub/issues

### Вариант C: Использовать наш Python скрипт

```bash
python scripts/download_docling_models.py --verbose
```

Наш скрипт уже включает retry и hf-transfer!

---

## 📦 Готовый скрипт для вашего случая

```bash
#!/bin/bash
# download_heron_101.sh

set -e

echo "Installing hf-transfer..."
pip install hf-transfer -q

echo "Setting environment..."
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DOWNLOAD_TIMEOUT=600

echo "Downloading model..."
mkdir -p layout

python3 << 'EOF'
import os
import time
from huggingface_hub import snapshot_download

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "600"

MAX_RETRIES = 5

for attempt in range(MAX_RETRIES):
    try:
        print(f"\nAttempt {attempt + 1}/{MAX_RETRIES}")
        snapshot_download(
            repo_id="docling-project/docling-layout-heron-101",
            local_dir="./layout",
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        print("\n✅ Success!")
        break
    except Exception as e:
        print(f"❌ Failed: {e}")
        if attempt < MAX_RETRIES - 1:
            time.sleep(10)
        else:
            raise
EOF

echo "Verifying download..."
ls -lh layout/

echo "Done!"
```

Сохраните как `download_heron_101.sh` и запустите:

```bash
bash download_heron_101.sh
```

---

## ✅ Для вашего конкретного случая

```bash
# 1. Установить hf-transfer
pip install hf-transfer

# 2. Запустить с правильными настройками
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DOWNLOAD_TIMEOUT=600

cd /home/artem/projects/tg-note/data/docling/models
mkdir -p layout

huggingface-cli download docling-project/docling-layout-heron-101 \
    --local-dir ./layout \
    --local-dir-use-symlinks False
```

Если всё равно таймаутит - используйте Python скрипт выше! 🚀
