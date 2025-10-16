#!/usr/bin/env python3
"""
Memory Agent Installation Script

This script installs mem-agent - a personal note-taking and search system
specifically designed for the main agent.

The agent uses mem-agent to:
- Record notes and findings during task execution
- Search through notes to "remember" previously recorded information
- Maintain working memory within a single agent session

Installation steps:
1. Installs mem-agent dependencies
2. Downloads the model from HuggingFace

MCP server configuration and folder creation are handled automatically
when the bot starts (see src/agents/mcp/server_manager.py).

Note: Uses settings from config.settings to avoid conflicts
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config.settings import settings as app_settings

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    print("[!] Warning: Could not import config.settings, using default values")


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status"""
    print(f"[*] {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"[✓] {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[✗] {description} - Failed")
        print(f"    Error: {e.stderr}")
        return False


def is_apple_silicon() -> bool:
    """Return True if running on macOS with Apple Silicon (arm64)."""
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def normalize_dep_name(dep: str) -> str:
    """Extract the base package name from a dependency spec string."""
    # Split on common version/extras delimiters
    for sep in ["[", " ", "<", ">", "=", "~", "!", ";"]:
        dep = dep.split(sep, 1)[0]
    return dep.strip()


def get_dependencies_from_pyproject() -> list[str]:
    """Read minimal dependencies from pyproject.toml, filtering heavy ML deps."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    try:
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)

        # On Apple Silicon, we rely on LM Studio; no Python ML deps needed
        if is_apple_silicon():
            return []

        # Otherwise, install only lightweight, platform-independent deps
        optional_deps = pyproject.get("project", {}).get("optional-dependencies", {})
        core_deps: list[str] = list(optional_deps.get("mem-agent", []))

        # Filter out heavy ML/runtime packages since models run in containers/LM Studio
        heavy_names = {
            "transformers",
            "torch",
            "tensorflow",
            "jax",
            "vllm",
            "mlx",
            "mlx-lm",
            "sentence-transformers",
            "faiss-cpu",
            "faiss-gpu",
        }
        filtered_deps = [d for d in core_deps if normalize_dep_name(d) not in heavy_names]
        return filtered_deps
    except Exception as e:
        print(f"[!] Warning: Could not read dependencies from pyproject.toml: {e}")
        print("[!] Falling back to minimal dependencies")
        # Fallback to minimal dependencies
        base = [
            # intentionally omit heavy ML libs like transformers/torch
            "huggingface-hub",
            "fastmcp",
            "aiofiles",
            "pydantic>=2.0.0",
            "python-dotenv",
            "jinja2",
            "pygments",
        ]
        return [] if is_apple_silicon() else base


def check_huggingface_cli() -> bool:
    """Check if huggingface-cli is available"""
    try:
        subprocess.run(["huggingface-cli", "--version"], check=True, capture_output=True, text=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_dependencies() -> bool:
    """Install minimal mem-agent dependencies (skip heavy ML backends)."""
    print("\n=== Installing Dependencies ===\n")

    # Get dependencies from pyproject.toml
    deps = get_dependencies_from_pyproject()

    if is_apple_silicon():
        print("[*] Platform: macOS (Apple Silicon)")
        print("[*] Skipping Python ML dependencies (LM Studio will be used)")
        return True

    print("[*] Platform: Linux/Windows (models served via containers)")
    print(f"[*] Installing {len(deps)} lightweight dependencies from pyproject.toml\n")

    for dep in deps:
        if not run_command([sys.executable, "-m", "pip", "install", dep], f"Installing {dep}"):
            print(f"\n[!] Warning: Failed to install {dep}, continuing anyway...")

    return True


def install_lm_studio() -> bool:
    """Install LM Studio on macOS via Homebrew if available, or print instructions."""
    print("\n=== Installing LM Studio (macOS) ===\n")
    # Prefer Homebrew if present
    brew_path = shutil.which("brew")

    if brew_path:
        print("[*] Homebrew detected. Installing LM Studio via Homebrew cask...")
        if run_command([brew_path, "install", "--cask", "lm-studio"], "Installing LM Studio"):
            print("[✓] LM Studio installed via Homebrew")
            return True
        else:
            print("[!] Homebrew install failed. You can install manually from the website.")
    else:
        print("[!] Homebrew not found.")

    print("\nManual installation required:")
    print("  1) Download LM Studio: https://lmstudio.ai")
    print("  2) Drag 'LM Studio.app' to /Applications")
    print("  3) Run 'scripts/run_lmstudio_model.sh' to set environment and validate server")
    return False


def download_model(model_id: str, precision: str = "4bit") -> bool:
    """Download model from HuggingFace"""
    print("\n=== Downloading Model ===\n")

    if not check_huggingface_cli():
        print("[!] huggingface-cli not found, installing...")
        if not run_command(
            [sys.executable, "-m", "pip", "install", "huggingface-hub[cli]"],
            "Installing huggingface-hub CLI",
        ):
            return False

    # Download the model
    print(f"[*] Downloading {model_id}...")
    print(f"    This may take a while depending on your internet connection...")

    try:
        subprocess.run(["huggingface-cli", "download", model_id], check=True, text=True)
        print(f"[✓] Model {model_id} downloaded successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[✗] Failed to download model: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Install and configure mem-agent for tg-note")

    # Get defaults from config if available
    # Note: Using driaforall/mem-agent as the default model (not BAAI/bge-m3 which is for embeddings)
    default_model = "driaforall/mem-agent"
    default_precision = app_settings.MEM_AGENT_MODEL_PRECISION if CONFIG_AVAILABLE else "4bit"

    parser.add_argument(
        "--model", default=default_model, help=f"HuggingFace model ID (default: {default_model})"
    )
    parser.add_argument(
        "--precision",
        default=default_precision,
        choices=["4bit", "8bit", "fp16"],
        help=f"Model precision (default: {default_precision})",
    )
    parser.add_argument(
        "--skip-model-download",
        action="store_true",
        help="Skip model download (if already downloaded)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Memory Agent Installation")
    print("=" * 60)
    print(f"\nModel: {args.model}")
    print(f"Precision: {args.precision}")
    if CONFIG_AVAILABLE:
        print("[✓] Using settings from config.settings")
    else:
        print("[!] Using default settings (config.settings not available)")
    print()

    # Step 1: Platform-specific setup
    if is_apple_silicon():
        # Apple Silicon: use LM Studio; skip Python ML deps and model download
        if not install_dependencies():
            print("\n[✗] Failed to perform base setup")
            return 1
        install_lm_studio()
        print("\n[*] Skipping model download (LM Studio will handle model management)")
    else:
        # Non-macOS: models run in containers; install only lightweight deps and skip downloads
        if not install_dependencies():
            print("\n[✗] Installation failed at dependency installation stage")
            return 1
        print("\n[*] Skipping local model download (containerized backend will handle models)")

    print("\n" + "=" * 60)
    print("Installation Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Enable mem-agent in your config.yaml or .env:")
    print("   AGENT_ENABLE_MCP: true")
    print("   AGENT_ENABLE_MCP_MEMORY: true")
    if is_apple_silicon():
        print("2. Start LM Studio and enable the local OpenAI-compatible server:")
        print("   - Quick setup and model load via CLI:")
        print("     ./scripts/lms_load_mem_agent.sh")
        print("   - Or manually:")
        print("     ./scripts/run_lmstudio_model.sh")
        print(
            "   - This sets MEM_AGENT_BASE_URL=http://127.0.0.1:1234/v1 and MEM_AGENT_OPENAI_API_KEY=lm-studio"
        )
    else:
        print("2. Start the containerized backend (vLLM) as per docker-compose setup")
        print(
            "   - Configure MEM_AGENT_BASE_URL to point to your OpenAI-compatible endpoint"
        )
        print(
            "   - Example: MEM_AGENT_BASE_URL=http://vllm-server:8001/v1"
        )
    print("3. Start the bot - MCP server will be auto-configured and started")
    print("4. Agent's notes are stored per-user inside your KB path (memory/)")
    print("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
