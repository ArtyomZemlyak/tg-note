#!/usr/bin/env python3
"""
Download Docling models via ModelScope mirror (works in China and regions with HF restrictions)

ModelScope is a Chinese mirror of HuggingFace models, often faster and more accessible
in Asia and regions where HuggingFace is slow/blocked.

Usage:
    python download_via_modelscope.py [output_dir]
"""

import sys
from pathlib import Path

try:
    from modelscope.hub.snapshot_download import snapshot_download
except ImportError:
    print("❌ ModelScope not installed!")
    print()
    print("Install it with:")
    print("  pip install modelscope")
    print()
    sys.exit(1)


OUTPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "./models"

# ModelScope model IDs (if available)
# Note: Not all HuggingFace models are mirrored on ModelScope
# You may need to search for equivalent models on modelscope.cn

MODELSCOPE_MODELS = {
    "layout": {
        "model_id": "iic/nlp_layout-lm_document-layout-analysis",  # Example, may not be exact
        "local_dir": "layout",
        "description": "Layout analysis model",
    },
    # Add more models as they become available on ModelScope
}


def download_from_modelscope(model_info, base_dir):
    """Download a model from ModelScope."""
    model_id = model_info["model_id"]
    local_dir = Path(base_dir) / model_info["local_dir"]
    description = model_info["description"]
    
    print("=" * 80)
    print(f"Downloading: {description}")
    print(f"Model ID: {model_id}")
    print(f"Output: {local_dir}")
    print("=" * 80)
    print()
    
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        
        cache_dir = snapshot_download(
            model_id,
            cache_dir=str(local_dir),
        )
        
        print()
        print(f"✅ Downloaded to: {cache_dir}")
        print()
        return True
        
    except Exception as e:
        print()
        print(f"❌ Failed: {e}")
        print()
        return False


def main():
    print("═══════════════════════════════════════════════════════════════")
    print("Downloading Docling Models via ModelScope Mirror")
    print("═══════════════════════════════════════════════════════════════")
    print()
    print("⚠️  NOTE: Not all HuggingFace models are available on ModelScope")
    print("You may need to find equivalent models or use alternative methods")
    print()
    
    base_dir = Path(OUTPUT_DIR)
    base_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    total_count = len(MODELSCOPE_MODELS)
    
    for model_name, model_info in MODELSCOPE_MODELS.items():
        if download_from_modelscope(model_info, base_dir):
            success_count += 1
    
    print("═══════════════════════════════════════════════════════════════")
    print(f"Summary: {success_count}/{total_count} models downloaded")
    print("═══════════════════════════════════════════════════════════════")
    print()
    
    if success_count == 0:
        print("❌ No models downloaded!")
        print()
        print("⚠️  Docling models may not be available on ModelScope yet.")
        print()
        print("Alternative solutions:")
        print("  1. Use VPN to access HuggingFace")
        print("  2. Download from alternative source (see below)")
        print("  3. Ask for direct download link from someone with access")
        print()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
