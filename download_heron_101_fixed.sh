#!/bin/bash
# Fixed script to download docling-layout-heron-101 with timeout handling

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "Downloading docling-layout-heron-101 with timeout fix"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if hf-transfer is installed
if ! python3 -c "import hf_transfer" 2>/dev/null; then
    echo "📦 Installing hf-transfer (required for stable downloads)..."
    pip install hf-transfer -q
    echo "✅ hf-transfer installed"
    echo ""
fi

# Set environment variables
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DOWNLOAD_TIMEOUT=600
export HF_HUB_DISABLE_XET=1

echo "Environment:"
echo "  HF_HUB_ENABLE_HF_TRANSFER=1 (bypass XET bridge)"
echo "  HF_HUB_DOWNLOAD_TIMEOUT=600 (10 minutes)"
echo ""

# Create output directory
OUTPUT_DIR="./layout"
mkdir -p "$OUTPUT_DIR"

echo "═══════════════════════════════════════════════════════════════"
echo "Using Python script with automatic retry..."
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Download with Python (more reliable than CLI)
python3 << 'PYTHON_SCRIPT'
import os
import time
from pathlib import Path

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "600"
os.environ["HF_HUB_DISABLE_XET"] = "1"

from huggingface_hub import snapshot_download

MODEL = "docling-project/docling-layout-heron-101"
LOCAL_DIR = "./layout"
MAX_RETRIES = 10

print(f"Model: {MODEL}")
print(f"Output: {LOCAL_DIR}")
print()

for attempt in range(MAX_RETRIES):
    try:
        print(f"{'─'*60}")
        print(f"Attempt {attempt + 1}/{MAX_RETRIES}")
        print(f"{'─'*60}")
        
        snapshot_download(
            repo_id=MODEL,
            local_dir=LOCAL_DIR,
            local_dir_use_symlinks=False,
            resume_download=True,
            max_workers=4,
        )
        
        print()
        print("✅ Download completed!")
        break
        
    except Exception as e:
        error = str(e)
        print(f"❌ Error: {error[:100]}")
        
        if attempt < MAX_RETRIES - 1:
            delay = 10 * (1.5 ** attempt)  # Exponential backoff
            print(f"⏳ Retrying in {delay:.0f} seconds...")
            print()
            time.sleep(delay)
        else:
            print()
            print("❌ All retries failed!")
            raise

# Verify
files = list(Path(LOCAL_DIR).rglob("*"))
files = [f for f in files if f.is_file()]
total_size = sum(f.stat().st_size for f in files) / (1024*1024)

print()
print("="*60)
print(f"✅ Downloaded {len(files)} files ({total_size:.1f} MB)")
print("="*60)
for f in sorted(files)[:10]:
    size_mb = f.stat().st_size / (1024*1024)
    print(f"  {f.name:30s} {size_mb:6.1f} MB")
if len(files) > 10:
    print(f"  ... and {len(files)-10} more")
PYTHON_SCRIPT

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Done! Files are in: $OUTPUT_DIR"
echo "═══════════════════════════════════════════════════════════════"
