#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to clean up duplicate images in knowledge base.

This script:
1. Scans the images directory for duplicate images based on file hash
2. Keeps the oldest file (by timestamp in filename)
3. Removes newer duplicates
4. Reports what was removed

Usage:
    python scripts/cleanup_duplicate_images.py [--dry-run] <images_dir>

Example:
    python scripts/cleanup_duplicate_images.py --dry-run knowledge_base/tg-note-kb/images
    python scripts/cleanup_duplicate_images.py knowledge_base/tg-note-kb/images
"""

import argparse
import hashlib
import sys
from collections import defaultdict
from pathlib import Path


def compute_file_hash(file_path):
    """Compute SHA256 hash of file."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def extract_timestamp_from_filename(filename):
    """Extract timestamp from image filename like img_1762860964_AgACAgIA.jpg"""
    try:
        # Format: img_<timestamp>_<file_id>.ext
        parts = filename.split("_")
        if len(parts) >= 2 and parts[0] == "img":
            return int(parts[1])
    except (ValueError, IndexError):
        pass
    return 0


def find_duplicates(images_dir):
    """
    Find duplicate images grouped by hash.

    Returns:
        dict: Hash -> list of file paths with that hash
    """
    hash_to_files = defaultdict(list)

    print(f"Scanning directory: {images_dir}")

    # Scan all image files
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp", ".webp"]:
        for image_file in images_dir.glob(f"img_*{ext}"):
            if image_file.is_file():
                try:
                    file_hash = compute_file_hash(image_file)
                    hash_to_files[file_hash].append(image_file)
                except Exception as e:
                    print(f"Warning: Error processing {image_file}: {e}", file=sys.stderr)

    # Filter to only keep hashes with duplicates
    duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}

    return duplicates


def cleanup_duplicates(duplicates, dry_run=False):
    """
    Remove duplicate files, keeping the oldest one.

    Args:
        duplicates: Hash -> list of duplicate files
        dry_run: If True, don't actually delete files

    Returns:
        tuple: (total_files_removed, total_bytes_saved)
    """
    files_removed = 0
    bytes_saved = 0

    for file_hash, files in duplicates.items():
        # Sort by timestamp (oldest first)
        sorted_files = sorted(files, key=lambda f: extract_timestamp_from_filename(f.name))

        # Keep the first (oldest) file
        keep_file = sorted_files[0]
        remove_files = sorted_files[1:]

        print(f"\n🔍 Hash: {file_hash[:8]}...")
        print(f"   ✅ KEEP: {keep_file.name}")

        for remove_file in remove_files:
            file_size = remove_file.stat().st_size
            bytes_saved += file_size

            if dry_run:
                print(f"   🗑️  WOULD REMOVE: {remove_file.name} ({file_size} bytes)")
            else:
                try:
                    remove_file.unlink()
                    print(f"   ❌ REMOVED: {remove_file.name} ({file_size} bytes)")
                    files_removed += 1
                except Exception as e:
                    print(f"   ⚠️  ERROR removing {remove_file.name}: {e}", file=sys.stderr)

    return files_removed, bytes_saved


def format_bytes(bytes_count):
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} TB"


def main():
    parser = argparse.ArgumentParser(
        description="Clean up duplicate images in knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("images_dir", type=Path, help="Path to images directory")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without actually removing files",
    )

    args = parser.parse_args()

    # Validate directory
    if not args.images_dir.exists():
        print(f"❌ Error: Directory does not exist: {args.images_dir}", file=sys.stderr)
        sys.exit(1)

    if not args.images_dir.is_dir():
        print(f"❌ Error: Not a directory: {args.images_dir}", file=sys.stderr)
        sys.exit(1)

    # Find duplicates
    print("=" * 60)
    print("🔍 Scanning for duplicate images...")
    print("=" * 60)

    duplicates = find_duplicates(args.images_dir)

    if not duplicates:
        print("\n✅ No duplicates found!")
        return

    # Report findings
    total_duplicate_files = sum(len(files) - 1 for files in duplicates.values())
    print(f"\n📊 Found {len(duplicates)} sets of duplicates")
    print(f"📊 Total duplicate files to remove: {total_duplicate_files}")

    # Cleanup
    print("\n" + "=" * 60)
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be deleted")
    else:
        print("🗑️  CLEANUP MODE - Removing duplicates...")
    print("=" * 60)

    files_removed, bytes_saved = cleanup_duplicates(duplicates, dry_run=args.dry_run)

    # Final summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    if args.dry_run:
        print(f"Would remove: {total_duplicate_files} files")
        print(f"Would save: {format_bytes(bytes_saved)}")
        print("\nRun without --dry-run to actually remove duplicates")
    else:
        print(f"✅ Removed: {files_removed} files")
        print(f"💾 Saved: {format_bytes(bytes_saved)}")


if __name__ == "__main__":
    main()
