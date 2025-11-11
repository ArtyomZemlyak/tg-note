#!/usr/bin/env python3
"""
Test script to verify that minimal docling installation is working correctly.

Usage:
    python scripts/test_model_download_setup.py
"""

import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "docker" / "docling-mcp" / "app"))

PASSED = 0
FAILED = 0


def test_import(module_name, package=None):
    """Test if a module can be imported."""
    global PASSED, FAILED
    try:
        if package:
            __import__(package, fromlist=[module_name])
        else:
            __import__(module_name)
        print(f"✅ {module_name}")
        PASSED += 1
        return True
    except ImportError as e:
        print(f"❌ {module_name}: {e}")
        FAILED += 1
        return False


def main():
    global PASSED, FAILED
    print("=" * 80)
    print("Testing Minimal Docling Installation for Model Download")
    print("=" * 80)
    print()

    # Test required packages
    print("1. Testing required packages:")
    print("-" * 80)
    test_import("pydantic")
    test_import("yaml", "yaml")
    test_import("huggingface_hub")
    test_import("requests")
    test_import("tqdm")
    print()

    # Test optional packages
    print("2. Testing optional packages:")
    print("-" * 80)
    hf_transfer_available = test_import("hf_transfer")
    modelscope_available = test_import("modelscope")
    print()

    # Test docling core
    print("3. Testing docling core:")
    print("-" * 80)
    docling_ok = test_import("docling")
    if docling_ok:
        test_import("docling.datamodel.pipeline_options")
        test_import("docling.models.layout_model")
        test_import("docling.models.table_structure_model")
        test_import("docling.utils.model_downloader")
    print()

    # Test project modules
    print("4. Testing project modules:")
    print("-" * 80)
    config_ok = test_import("config.settings")
    tg_docling_ok = test_import("tg_docling.config")
    model_sync_ok = test_import("tg_docling.model_sync")
    print()

    # Test config file
    print("5. Testing configuration:")
    print("-" * 80)
    config_yaml = project_root / "config.yaml"
    if config_yaml.exists():
        print(f"✅ config.yaml exists at {config_yaml}")
        PASSED += 1
    else:
        print(f"❌ config.yaml not found at {config_yaml}")
        print("   Create it from config.example.yaml:")
        print(f"   cp {project_root / 'config.example.yaml'} {config_yaml}")
        FAILED += 1
    print()

    # Summary
    print("=" * 80)
    print("Summary:")
    print("=" * 80)
    print(f"Passed: {PASSED}")
    print(f"Failed: {FAILED}")
    print()

    if FAILED == 0:
        print("🎉 All tests passed! You can now download models:")
        print("   python scripts/download_docling_models.py")
        print()
        if not hf_transfer_available:
            print("💡 Tip: Install hf-transfer for faster downloads:")
            print("   pip install hf-transfer")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print()
        if FAILED > 3 and not docling_ok:
            print("💡 Most likely you need to install requirements:")
            print("   pip install -r requirements-model-download.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
