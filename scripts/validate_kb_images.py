#!/usr/bin/env python3
"""
CLI tool for validating media references in knowledge base markdown files.

Usage:
    python scripts/validate_kb_images.py /path/to/kb --verbose
    python scripts/validate_kb_images.py --kb /path/to/kb
    python scripts/validate_kb_images.py --help
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor.markdown_media_validator import validate_kb_media


def main():
    parser = argparse.ArgumentParser(
        description="Validate media references in knowledge base markdown files"
    )
    parser.add_argument(
        "kb_path",
        nargs="?",
        help="Path to knowledge base directory (default: ./knowledge_base)",
        default="./knowledge_base",
    )
    parser.add_argument(
        "--kb",
        dest="kb_path_alt",
        help="Alternative way to specify KB path",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Include info-level issues in report (e.g., alt text quality)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code if any validation issues found (including warnings)",
    )

    args = parser.parse_args()

    # Use alternate KB path if provided
    kb_path = Path(args.kb_path_alt or args.kb_path)

    # Validate KB path exists
    if not kb_path.exists():
        print(f"❌ Error: Knowledge base path does not exist: {kb_path}", file=sys.stderr)
        return 1

    if not kb_path.is_dir():
        print(f"❌ Error: Knowledge base path is not a directory: {kb_path}", file=sys.stderr)
        return 1

    print(f"🔍 Validating knowledge base: {kb_path.resolve()}")
    print()

    # Run validation
    error_count = validate_kb_media(kb_path, verbose=args.verbose)

    # Determine exit code
    if error_count > 0:
        print(f"\n❌ Validation failed with {error_count} error(s)")
        return 1
    elif args.strict:
        print("\n⚠️  Validation passed with warnings (strict mode)")
        return 0  # Could return 1 here if you want strict mode to fail on warnings
    else:
        print("\n✅ Validation passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
