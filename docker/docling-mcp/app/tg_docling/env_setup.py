"""
Early environment setup for Docling paths.

This module MUST be imported before any Docling components to ensure
environment variables are set correctly before Docling initialization.
"""

import os
from pathlib import Path


def setup_docling_environment() -> None:
    """
    Initialize Docling environment variables early in the startup process.

    This should be called before any Docling imports to ensure paths
    are configured correctly.
    """
    # Default models directory
    models_dir = Path(os.getenv("DOCLING_MODELS_DIR", "/opt/docling-mcp/models"))
    models_dir.mkdir(parents=True, exist_ok=True)

    # Default cache directory
    cache_dir = Path(os.getenv("DOCLING_CACHE_DIR", "/opt/docling-mcp/cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Set environment variables (use assignment to override any incorrect values)
    os.environ["DOCLING_MODELS_DIR"] = str(models_dir)
    os.environ["DOCLING_ARTIFACTS_PATH"] = str(models_dir)
    os.environ["DOCLING_CACHE_DIR"] = str(cache_dir)

    # Set HuggingFace cache if not already configured
    if "HF_HOME" not in os.environ:
        hf_home = models_dir.parent / "hf_cache"
        hf_home.mkdir(parents=True, exist_ok=True)
        os.environ["HF_HOME"] = str(hf_home)


# AICODE-NOTE: Initialize environment as soon as this module is imported
setup_docling_environment()
