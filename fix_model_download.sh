#!/bin/bash
# Script to check repository structure and download correctly

REPO="$1"
if [ -z "$REPO" ]; then
    echo "Usage: bash fix_model_download.sh <repo_id>"
    echo "Example: bash fix_model_download.sh docling-project/docling-layout-heron-101"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "Checking repository: $REPO"
echo "═══════════════════════════════════════════════════════════════"

# List files in the repository
echo ""
echo "Files in repository:"
echo "───────────────────────────────────────────────────────────────"
huggingface-cli scan-cache "$REPO" 2>/dev/null || {
    echo "Repository not in cache, fetching file list from HuggingFace..."
    python3 -c "
from huggingface_hub import list_repo_files
try:
    files = list_repo_files('$REPO')
    for f in sorted(files)[:20]:
        print(f'  {f}')
    if len(files) > 20:
        print(f'  ... and {len(files) - 20} more files')
except Exception as e:
    print(f'Error: {e}')
    print('Try: pip install huggingface-hub')
"
}

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Recommended download command:"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "# Download ALL files (recommended):"
echo "huggingface-cli download $REPO --local-dir . --local-dir-use-symlinks False"
echo ""
echo "# Or download only specific files (faster):"
echo "huggingface-cli download $REPO --include '*.onnx' --include '*.json' --local-dir . --local-dir-use-symlinks False"
echo ""
