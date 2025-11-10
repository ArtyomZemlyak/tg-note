#!/bin/bash
# Download Docling models using huggingface-cli with hf_transfer for faster downloads
# Usage: bash download_docling_models.sh [output_dir]

set -e

# Default output directory
OUTPUT_DIR="${1:-/opt/docling-mcp/models}"

echo "═══════════════════════════════════════════════════════════════"
echo "Downloading Docling models to: $OUTPUT_DIR"
echo "═══════════════════════════════════════════════════════════════"

# Install hf_transfer if not already installed
if ! python3 -c "import hf_transfer" 2>/dev/null; then
    echo "Installing hf_transfer for faster downloads..."
    pip install hf-transfer -q
fi

# Enable hf_transfer for faster downloads
export HF_HUB_ENABLE_HF_TRANSFER=1

# Create output directory
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "1/5 Downloading Layout Model (DS4SD/docling-models)..."
echo "───────────────────────────────────────────────────────────────"
huggingface-cli download \
    DS4SD/docling-models \
    --include "layout/*" \
    --local-dir . \
    --local-dir-use-symlinks False

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "2/5 Downloading TableFormer Model (DS4SD/docling-models)..."
echo "───────────────────────────────────────────────────────────────"
huggingface-cli download \
    DS4SD/docling-models \
    --include "tableformer/*" \
    --local-dir . \
    --local-dir-use-symlinks False

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "3/5 Downloading Code & Formula Model (DS4SD/docling-models)..."
echo "───────────────────────────────────────────────────────────────"
huggingface-cli download \
    DS4SD/docling-models \
    --include "code_formula_detection/*" \
    --local-dir . \
    --local-dir-use-symlinks False

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "4/5 Downloading Picture Classifier (DS4SD/docling-models)..."
echo "───────────────────────────────────────────────────────────────"
huggingface-cli download \
    DS4SD/docling-models \
    --include "picture_classifier/*" \
    --local-dir . \
    --local-dir-use-symlinks False

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "5/5 Downloading RapidOCR Models (RapidAI/RapidOCR)..."
echo "───────────────────────────────────────────────────────────────"
huggingface-cli download \
    RapidAI/RapidOCR \
    --include "RapidOcr/onnx/PP-OCRv4/*" \
    --local-dir . \
    --local-dir-use-symlinks False

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ All models downloaded successfully to: $OUTPUT_DIR"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Directory structure:"
ls -lh "$OUTPUT_DIR"
