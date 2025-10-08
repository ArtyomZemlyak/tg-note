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


def get_dependencies_from_pyproject() -> list[str]:
    """Read dependencies from pyproject.toml"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    try:
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
        
        # Get core mem-agent dependencies
        deps = []
        optional_deps = pyproject.get("project", {}).get("optional-dependencies", {})
        
        # Add core mem-agent dependencies
        core_deps = optional_deps.get("mem-agent", [])
        deps.extend(core_deps)
        
        # Add platform-specific dependencies
        if sys.platform == "darwin":
            # macOS - MLX support
            platform_deps = optional_deps.get("mem-agent-macos", [])
            deps.extend(platform_deps)
        else:
            # Linux/Windows - vLLM support
            platform_deps = optional_deps.get("mem-agent-linux", [])
            deps.extend(platform_deps)
        
        return deps
    except Exception as e:
        print(f"[!] Warning: Could not read dependencies from pyproject.toml: {e}")
        print("[!] Falling back to minimal dependencies")
        # Fallback to minimal dependencies
        return [
            "transformers",
            "huggingface-hub",
            "fastmcp",
            "aiofiles",
            "pydantic>=2.0.0",
            "python-dotenv",
            "jinja2",
            "pygments"
        ]


def check_huggingface_cli() -> bool:
    """Check if huggingface-cli is available"""
    try:
        subprocess.run(
            ["huggingface-cli", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_dependencies() -> bool:
    """Install mem-agent dependencies from pyproject.toml"""
    print("\n=== Installing Dependencies ===\n")
    
    # Get dependencies from pyproject.toml
    deps = get_dependencies_from_pyproject()
    
    platform_name = "macOS (MLX)" if sys.platform == "darwin" else "Linux/Windows (vLLM)"
    print(f"[*] Platform: {platform_name}")
    print(f"[*] Installing {len(deps)} dependencies from pyproject.toml\n")
    
    for dep in deps:
        if not run_command(
            [sys.executable, "-m", "pip", "install", dep],
            f"Installing {dep}"
        ):
            print(f"\n[!] Warning: Failed to install {dep}, continuing anyway...")
    
    return True


def download_model(model_id: str, precision: str = "4bit") -> bool:
    """Download model from HuggingFace"""
    print("\n=== Downloading Model ===\n")
    
    if not check_huggingface_cli():
        print("[!] huggingface-cli not found, installing...")
        if not run_command(
            [sys.executable, "-m", "pip", "install", "huggingface-hub[cli]"],
            "Installing huggingface-hub CLI"
        ):
            return False
    
    # Download the model
    print(f"[*] Downloading {model_id}...")
    print(f"    This may take a while depending on your internet connection...")
    
    try:
        subprocess.run(
            ["huggingface-cli", "download", model_id],
            check=True,
            text=True
        )
        print(f"[✓] Model {model_id} downloaded successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[✗] Failed to download model: {e}")
        return False




def main():
    parser = argparse.ArgumentParser(
        description="Install and configure mem-agent for tg-note"
    )
    
    # Get defaults from config if available
    # Note: Using driaforall/mem-agent as the default model (not BAAI/bge-m3 which is for embeddings)
    default_model = "driaforall/mem-agent"
    default_precision = app_settings.MEM_AGENT_MODEL_PRECISION if CONFIG_AVAILABLE else "4bit"
    
    parser.add_argument(
        "--model",
        default=default_model,
        help=f"HuggingFace model ID (default: {default_model})"
    )
    parser.add_argument(
        "--precision",
        default=default_precision,
        choices=["4bit", "8bit", "fp16"],
        help=f"Model precision (default: {default_precision})"
    )
    parser.add_argument(
        "--skip-model-download",
        action="store_true",
        help="Skip model download (if already downloaded)"
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
    
    # Step 1: Install dependencies
    if not install_dependencies():
        print("\n[✗] Installation failed at dependency installation stage")
        return 1
    
    # Step 2: Download model (unless skipped)
    if not args.skip_model_download:
        if not download_model(args.model, args.precision):
            print("\n[!] Warning: Model download failed, but continuing anyway...")
            print("    You can download the model manually later using:")
            print(f"    huggingface-cli download {args.model}")
    else:
        print("\n[*] Skipping model download (as requested)")
    
    print("\n" + "=" * 60)
    print("Installation Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Enable mem-agent in your config.yaml or .env:")
    print("   AGENT_ENABLE_MCP: true")
    print("   AGENT_ENABLE_MCP_MEMORY: true")
    print("2. Start the bot - MCP server will be auto-configured and started")
    print("3. Agent's notes will be stored per-user at:")
    print("   knowledge_base/{user-kb-name}/memory/")
    print("   (directories are created automatically on first use)")
    print("4. How the agent uses it:")
    print("   - During tasks: Agent records notes about findings, context, etc.")
    print("   - When needed: Agent searches notes to recall previously recorded info")
    print("   - Within session: Maintains working memory across multiple LLM calls")
    print("5. You can change settings in config.yaml or .env:")
    print("   - Model: driaforall/mem-agent (LLM-based memory agent)")
    print("   - MEM_AGENT_MEMORY_POSTFIX (default: memory)")
    print("   - Each user's notes are isolated in their own KB")
    print("6. To start the MCP server:")
    print("   python -m src.agents.mcp.memory.mem_agent_impl.mcp_server --host 127.0.0.1 --port 8766")
    print("\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())