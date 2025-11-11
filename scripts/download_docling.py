#!/usr/bin/env python3
"""
Standalone script to download Docling models using the project's model_sync code.

This script can be run with minimal dependencies (no OCR engines, no transformers, etc.)
It uses the existing model_sync.py logic from docker/docling-mcp/app/tg_docling/

Usage:
    python scripts/download_docling_models.py [--force] [--config CONFIG_PATH]

Requirements:
    pip install docling docling-mcp huggingface-hub hf-transfer

HF_HUB_DISABLE_XET=1 HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download docling-project/docling-layout-heron-101 --local-dir ./docling-project--docling-layout-heron --local-dir-use-symlinks False
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "docker" / "docling-mcp" / "app"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Download Docling models based on project configuration"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if models already exist",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Import after path is set
    try:
        from tg_docling.config import load_docling_settings
        from tg_docling.model_sync import sync_models
    except ImportError as e:
        logger.error("Failed to import model_sync modules: %s", e)
        logger.error("Make sure you have installed: pip install -r requirements-model-download.txt")
        return 1

    # Load settings
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        logger.error("Please create config.yaml from config.example.yaml")
        return 1

    logger.info("Loading configuration from: %s", config_path)
    try:
        docling_settings, _ = load_docling_settings(config_path)
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        return 1

    # Display configuration summary
    logger.info("=" * 80)
    logger.info("Docling Model Download Configuration")
    logger.info("=" * 80)
    logger.info("Model cache directory: %s", docling_settings.model_cache.base_dir)
    logger.info("Force re-download: %s", args.force)

    builtin = docling_settings.model_cache.builtin_models
    enabled_models = []
    if builtin.layout:
        enabled_models.append("layout")
    if builtin.tableformer:
        enabled_models.append("tableformer")
    if builtin.code_formula:
        enabled_models.append("code_formula")
    if builtin.picture_classifier:
        enabled_models.append("picture_classifier")
    if builtin.rapidocr.enabled:
        backends = builtin.rapidocr.backends or ["onnxruntime", "torch"]
        enabled_models.append(f"rapidocr ({', '.join(backends)})")
    if builtin.easyocr:
        enabled_models.append("easyocr")
    if builtin.smolvlm:
        enabled_models.append("smolvlm")
    if builtin.granitedocling:
        enabled_models.append("granitedocling")
    if builtin.granitedocling_mlx:
        enabled_models.append("granitedocling_mlx")
    if builtin.smoldocling:
        enabled_models.append("smoldocling")
    if builtin.smoldocling_mlx:
        enabled_models.append("smoldocling_mlx")
    if builtin.granite_vision:
        enabled_models.append("granite_vision")

    logger.info("Enabled builtin models: %s", ", ".join(enabled_models) or "none")
    logger.info("Extra downloads: %d", len(docling_settings.model_cache.downloads))
    logger.info("=" * 80)

    # Create output directory
    output_dir = Path(docling_settings.model_cache.base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Created model cache directory: %s", output_dir)

    # Run model sync
    logger.info("Starting model synchronization...")
    logger.info("=" * 80)
    try:
        result = sync_models(docling_settings, force=args.force)
    except Exception as e:
        logger.error("Model synchronization failed: %s", e)
        logger.exception("Full traceback:")
        return 1

    # Display results
    logger.info("=" * 80)
    logger.info("Model Synchronization Complete")
    logger.info("=" * 80)
    summary = result.get("summary", {})
    logger.info("Total items: %d", summary.get("total", 0))
    logger.info("Successful: %d", summary.get("successful", 0))
    logger.info("Failed: %d", summary.get("failed", 0))

    # Show details
    if result.get("items"):
        logger.info("\nDetails:")
        for item in result["items"]:
            name = item.get("name", "unknown")
            status = item.get("status", "unknown")
            kind = item.get("kind", "unknown")
            path = item.get("path", "N/A")

            if status == "downloaded":
                logger.info("  ✅ %s [%s]: %s", name, kind, path)
            elif status == "skipped":
                reason = item.get("reason", "already cached")
                logger.info("  ⏭️  %s [%s]: skipped (%s)", name, kind, reason)
            elif status == "error":
                error = item.get("error", "unknown error")
                logger.error("  ❌ %s [%s]: %s", name, kind, error)

    logger.info("=" * 80)

    if summary.get("failed", 0) > 0:
        logger.warning("Some models failed to download. Check logs above for details.")
        return 1

    logger.info("✅ All models downloaded successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())