#!/bin/bash
# All-in-one script: install minimal docling and download models
# Usage: bash INSTALL_AND_DOWNLOAD.sh [--force]

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "Docling Model Download - Complete Setup"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if config.yaml exists
if [ ! -f "config.yaml" ]; then
    echo "⚠️  config.yaml not found"
    if [ -f "config.example.yaml" ]; then
        echo "Creating config.yaml from config.example.yaml..."
        cp config.example.yaml config.yaml
        echo "✅ config.yaml created"
        echo ""
        echo "⚠️  IMPORTANT: Review and adjust config.yaml for your needs!"
        echo "   Especially check MEDIA_PROCESSING_DOCLING.model_cache.base_dir"
        echo ""
    else
        echo "❌ config.example.yaml not found!"
        echo "   Please create config.yaml manually"
        exit 1
    fi
fi

# Install minimal requirements
echo "───────────────────────────────────────────────────────────────"
echo "Step 1/3: Installing minimal requirements..."
echo "───────────────────────────────────────────────────────────────"
pip install -r requirements-model-download.txt
echo "✅ Requirements installed"
echo ""

# Test setup
echo "───────────────────────────────────────────────────────────────"
echo "Step 2/3: Testing installation..."
echo "───────────────────────────────────────────────────────────────"
python scripts/test_model_download_setup.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Setup test failed!"
    echo "   Please fix the issues above before continuing"
    exit 1
fi
echo ""

# Download models
echo "───────────────────────────────────────────────────────────────"
echo "Step 3/3: Downloading models..."
echo "───────────────────────────────────────────────────────────────"

# Check for --force flag
FORCE_FLAG=""
if [ "$1" == "--force" ]; then
    FORCE_FLAG="--force"
    echo "Force re-download enabled"
fi

python scripts/download_docling_models.py $FORCE_FLAG

if [ $? -eq 0 ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "✅ Complete! All models downloaded successfully"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Next steps:"
    echo "  1. Verify models in the configured directory"
    echo "  2. Start your docling-mcp container"
    echo "  3. Optionally set startup_sync: false in config.yaml"
    echo ""
else
    echo ""
    echo "❌ Model download failed!"
    echo "   Check the logs above for details"
    exit 1
fi
