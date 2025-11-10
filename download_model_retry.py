#!/usr/bin/env python3
"""
Download HuggingFace model with automatic retry on timeout.
Handles XET bridge timeouts gracefully.

Usage:
    python download_model_retry.py [MODEL_ID] [LOCAL_DIR]
    
Examples:
    python download_model_retry.py docling-project/docling-layout-heron-101 ./layout
    python download_model_retry.py docling-project/docling-layout-v2 ./layout
"""

import os
import sys
import time
from pathlib import Path

# Enable hf-transfer for faster downloads (bypasses XET)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "600"
os.environ["HF_HUB_DISABLE_XET"] = "1"

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("❌ Error: huggingface-hub not installed")
    print("Install it with: pip install huggingface-hub hf-transfer")
    sys.exit(1)

# Check if hf-transfer is available
try:
    import hf_transfer
    print(f"✅ hf-transfer available (version {hf_transfer.__version__})")
except ImportError:
    print("⚠️  Warning: hf-transfer not installed, downloads will be slower")
    print("Install it with: pip install hf-transfer")

# Configuration
MODEL = sys.argv[1] if len(sys.argv) > 1 else "docling-project/docling-layout-heron-101"
LOCAL_DIR = sys.argv[2] if len(sys.argv) > 2 else "./layout"

MAX_RETRIES = 10
RETRY_DELAY = 10  # seconds
BACKOFF_MULTIPLIER = 1.5  # Exponential backoff


def download_with_retry():
    """Download model with retry logic."""
    
    print("=" * 80)
    print(f"Model: {MODEL}")
    print(f"Output directory: {LOCAL_DIR}")
    print(f"Max retries: {MAX_RETRIES}")
    print("=" * 80)
    print()
    
    delay = RETRY_DELAY
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"{'='*80}")
            print(f"Attempt {attempt + 1}/{MAX_RETRIES}: Downloading {MODEL}")
            print(f"{'='*80}")
            print()
            
            # Create directory
            Path(LOCAL_DIR).mkdir(parents=True, exist_ok=True)
            
            # Download with resume support
            local_path = snapshot_download(
                repo_id=MODEL,
                local_dir=LOCAL_DIR,
                local_dir_use_symlinks=False,
                resume_download=True,  # Resume if interrupted
                max_workers=4,  # Parallel downloads
            )
            
            print()
            print("=" * 80)
            print("✅ Download completed successfully!")
            print("=" * 80)
            print()
            
            # Verify download
            verify_download(local_path)
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Download interrupted by user")
            sys.exit(130)
            
        except Exception as e:
            error_msg = str(e)
            print()
            print("=" * 80)
            print(f"❌ Attempt {attempt + 1} failed!")
            print("=" * 80)
            print(f"Error: {error_msg}")
            print()
            
            # Check if it's a timeout error
            is_timeout = any(keyword in error_msg.lower() for keyword in [
                'timeout', 'timed out', 'read timeout', 'connection reset'
            ])
            
            if is_timeout:
                print("🔍 Detected timeout error - will retry")
            
            if attempt < MAX_RETRIES - 1:
                print(f"⏳ Retrying in {delay:.1f} seconds...")
                print()
                time.sleep(delay)
                
                # Exponential backoff
                delay *= BACKOFF_MULTIPLIER
                
            else:
                print("=" * 80)
                print("❌ All attempts failed!")
                print("=" * 80)
                print()
                print("Suggestions:")
                print("1. Check your internet connection")
                print("2. Try again later (HuggingFace servers may be overloaded)")
                print("3. Install hf-transfer: pip install hf-transfer")
                print("4. Try downloading individual files instead")
                print()
                raise
    
    return False


def verify_download(path):
    """Verify that files were downloaded."""
    files = list(Path(path).rglob("*"))
    files = [f for f in files if f.is_file()]
    
    print(f"Downloaded {len(files)} files:")
    print()
    
    # Show first 15 files
    for f in sorted(files)[:15]:
        size = f.stat().st_size
        size_mb = size / (1024 * 1024)
        print(f"  {f.name:40s} {size_mb:8.2f} MB")
    
    if len(files) > 15:
        print(f"  ... and {len(files) - 15} more files")
    
    print()
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in files)
    total_mb = total_size / (1024 * 1024)
    print(f"Total size: {total_mb:.2f} MB")
    print()


if __name__ == "__main__":
    try:
        success = download_with_retry()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
