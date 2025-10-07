#!/usr/bin/env python3
"""
Memory Agent Installation Script

This script:
1. Installs mem-agent dependencies
2. Downloads the model from HuggingFace
3. Sets up the MCP server configuration
4. Registers the mem-agent MCP server

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


def create_mcp_server_config(workspace_root: Path, memory_postfix: str) -> bool:
    """Create MCP server configuration for mem-agent"""
    print("\n=== Creating MCP Server Configuration ===\n")
    
    # MCP configs are global (per-user, not per-KB) and stored in data/mcp_servers/
    mcp_servers_dir = Path("data/mcp_servers")
    mcp_servers_dir.mkdir(parents=True, exist_ok=True)
    
    # Create mem-agent MCP server configuration
    # Note: Memory directory path will be determined at runtime based on user's KB
    config = {
        "name": "mem-agent",
        "description": "Local memory agent with intelligent memory management using LLM",
        "command": sys.executable,
        "args": [
            "-m",
            "src.mem_agent.server"
        ],
        "env": {
            "MEM_AGENT_MEMORY_POSTFIX": memory_postfix
        },
        "working_dir": str(workspace_root),
        "enabled": True
    }
    
    config_file = mcp_servers_dir / "mem-agent.json"
    
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[✓] MCP server configuration created: {config_file}")
        return True
    except Exception as e:
        print(f"[✗] Failed to create MCP server configuration: {e}")
        return False


def setup_memory_directory_note() -> None:
    """Print note about memory directory creation"""
    print("\n=== Memory Directory Setup ===\n")
    print("[i] Memory directory will be created automatically by the MCP server")
    print("    when it's first called. This ensures the correct path structure:")
    print("    knowledge_base/{user-specific-kb}/memory/")
    print("    ")
    print("    The memory directory is NOT created during installation because")
    print("    the specific user's knowledge base name is only known at runtime.")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Install and configure mem-agent for tg-note"
    )
    
    # Get defaults from config if available
    default_model = app_settings.MEM_AGENT_MODEL if CONFIG_AVAILABLE else "driaforall/mem-agent"
    default_precision = app_settings.MEM_AGENT_MODEL_PRECISION if CONFIG_AVAILABLE else "4bit"
    default_memory_postfix = app_settings.MEM_AGENT_MEMORY_POSTFIX if CONFIG_AVAILABLE else "memory"
    
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
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace root directory (default: current directory)"
    )
    parser.add_argument(
        "--memory-postfix",
        type=str,
        default=default_memory_postfix,
        help=f"Memory directory postfix within KB (default: {default_memory_postfix})"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Memory Agent Installation")
    print("=" * 60)
    print(f"\nModel: {args.model}")
    print(f"Precision: {args.precision}")
    print(f"Workspace: {args.workspace}")
    print(f"Memory postfix: {args.memory_postfix}")
    print(f"MCP config location: data/mcp_servers/mem-agent.json")
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
    
    # Step 3: Print note about memory directory (will be created at runtime)
    setup_memory_directory_note()
    
    # Step 4: Create MCP server configuration
    if not create_mcp_server_config(args.workspace, args.memory_postfix):
        print("\n[✗] Installation failed at MCP server configuration stage")
        return 1
    
    print("\n" + "=" * 60)
    print("Installation Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. The mem-agent MCP server has been registered in data/mcp_servers/")
    print("2. Enable it in your config.yaml or .env:")
    print("   AGENT_ENABLE_MCP: true")
    print("   AGENT_ENABLE_MCP_MEMORY: true")
    print("3. Memory will be stored per-user at runtime:")
    print("   knowledge_base/{user-kb-name}/memory/")
    print("   The MCP server creates this directory when first called.")
    print("4. You can change settings in config.yaml or .env:")
    print("   - MEM_AGENT_MODEL (default: driaforall/mem-agent)")
    print(f"   - MEM_AGENT_MEMORY_POSTFIX (default: {default_memory_postfix})")
    print("   - Each user's memory is isolated in their own KB")
    print("\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())