#!/bin/bash
# Download Docling models from NEW repositories (docling-project/*)
# Works with Docling 2.61.2+

set -e

OUTPUT_DIR="${1:-./models}"

echo "═══════════════════════════════════════════════════════════════"
echo "Downloading Docling models (NEW repos) to: $OUTPUT_DIR"
echo "═══════════════════════════════════════════════════════════════"

# Install hf_transfer if not present
if ! python3 -c "import hf_transfer" 2>/dev/null; then
    echo "Installing hf_transfer for faster downloads..."
    pip install hf-transfer -q
fi

# Enable hf_transfer
export HF_HUB_ENABLE_HF_TRANSFER=1

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "1/5 Downloading Layout Model (docling-layout-v2)..."
echo "───────────────────────────────────────────────────────────────"
mkdir -p "$OUTPUT_DIR/layout"
huggingface-cli download docling-project/docling-layout-v2 \
    --local-dir "$OUTPUT_DIR/layout" \
    --local-dir-use-symlinks False

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "2/5 Downloading TableFormer Model..."
echo "───────────────────────────────────────────────────────────────"
mkdir -p "$OUTPUT_DIR/tableformer"
huggingface-cli download docling-project/docling-tableformer \
    --local-dir "$OUTPUT_DIR/tableformer" \
    --local-dir-use-symlinks False

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "3/5 Downloading Code & Formula Model..."
echo "───────────────────────────────────────────────────────────────"
mkdir -p "$OUTPUT_DIR/code_formula_detection"
huggingface-cli download docling-project/docling-code-formula-detection \
    --local-dir "$OUTPUT_DIR/code_formula_detection" \
    --local-dir-use-symlinks False

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "4/5 Downloading Picture Classifier..."
echo "───────────────────────────────────────────────────────────────"
mkdir -p "$OUTPUT_DIR/picture_classifier"
huggingface-cli download docling-project/docling-document-picture-classifier \
    --local-dir "$OUTPUT_DIR/picture_classifier" \
    --local-dir-use-symlinks False

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "5/5 Downloading RapidOCR Models..."
echo "───────────────────────────────────────────────────────────────"
mkdir -p "$OUTPUT_DIR/RapidOcr"
huggingface-cli download RapidAI/RapidOCR \
    --include "RapidOcr/onnx/PP-OCRv4/*" \
    --local-dir "$OUTPUT_DIR" \
    --local-dir-use-symlinks False

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ All models downloaded successfully!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Models location: $OUTPUT_DIR"
echo ""
echo "Directory structure:"
tree "$OUTPUT_DIR" -L 2 2>/dev/null || ls -lh "$OUTPUT_DIR"
