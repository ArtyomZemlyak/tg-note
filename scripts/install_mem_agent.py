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
    """Install mem-agent dependencies"""
    print("\n=== Installing Dependencies ===\n")
    
    # Determine which dependencies to install based on platform
    if sys.platform == "darwin":
        # macOS - install MLX support
        deps = ["mlx", "mlx-lm", "transformers", "huggingface-hub", "fastmcp", "aiofiles"]
    else:
        # Linux/Windows - install vLLM support
        deps = ["vllm", "transformers", "huggingface-hub", "fastmcp", "aiofiles"]
    
    # Always install these
    deps.extend(["pydantic>=2.0.0", "python-dotenv", "jinja2", "pygments"])
    
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


def create_mcp_server_config(workspace_root: Path, kb_path: Path, memory_postfix: str) -> bool:
    """Create MCP server configuration for mem-agent"""
    print("\n=== Creating MCP Server Configuration ===\n")
    
    # Get MCP servers directory from config if available
    if CONFIG_AVAILABLE:
        mcp_servers_dir = app_settings.get_mcp_servers_dir(kb_path)
    else:
        mcp_servers_dir = kb_path / ".mcp_servers"
    
    mcp_servers_dir.mkdir(parents=True, exist_ok=True)
    
    # Create mem-agent MCP server configuration
    config = {
        "name": "mem-agent",
        "description": "Local memory agent with intelligent memory management using LLM",
        "command": sys.executable,
        "args": [
            "-m",
            "src.mem_agent.server"
        ],
        "env": {
            "MEM_AGENT_MEMORY_POSTFIX": memory_postfix,
            "KB_PATH": str(kb_path)
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


def setup_memory_directory(kb_path: Path, memory_postfix: str) -> bool:
    """Setup memory directory structure"""
    print("\n=== Setting Up Memory Directory ===\n")
    
    memory_dir = kb_path / memory_postfix
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    # Create initial user.md if it doesn't exist
    user_md = memory_dir / "user.md"
    if not user_md.exists():
        initial_content = """# User Information

This is your personal memory file. The memory agent will store information about you and your relationships here.

## User Relationships

Links to entities will appear here as you interact with the memory agent.
"""
        try:
            with open(user_md, "w", encoding="utf-8") as f:
                f.write(initial_content)
            print(f"[✓] Created initial user.md at {user_md}")
        except Exception as e:
            print(f"[✗] Failed to create user.md: {e}")
            return False
    else:
        print(f"[✓] user.md already exists at {user_md}")
    
    # Create entities directory
    entities_dir = memory_dir / "entities"
    entities_dir.mkdir(exist_ok=True)
    print(f"[✓] Memory directory structure created at {memory_dir}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Install and configure mem-agent for tg-note"
    )
    
    # Get defaults from config if available
    default_model = app_settings.MEM_AGENT_MODEL if CONFIG_AVAILABLE else "driaforall/mem-agent"
    default_precision = app_settings.MEM_AGENT_MODEL_PRECISION if CONFIG_AVAILABLE else "4bit"
    default_memory_postfix = app_settings.MEM_AGENT_MEMORY_POSTFIX if CONFIG_AVAILABLE else "memory"
    default_kb_path = app_settings.KB_PATH if CONFIG_AVAILABLE else Path("./knowledge_bases/default")
    
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
        "--kb-path",
        type=Path,
        default=default_kb_path,
        help=f"Knowledge base path (default: {default_kb_path})"
    )
    parser.add_argument(
        "--memory-postfix",
        type=str,
        default=default_memory_postfix,
        help=f"Memory directory postfix within KB (default: {default_memory_postfix})"
    )
    
    args = parser.parse_args()
    
    # Construct full memory path for display
    full_memory_path = args.kb_path / args.memory_postfix
    
    print("=" * 60)
    print("Memory Agent Installation")
    print("=" * 60)
    print(f"\nModel: {args.model}")
    print(f"Precision: {args.precision}")
    print(f"Workspace: {args.workspace}")
    print(f"Knowledge Base: {args.kb_path}")
    print(f"Memory postfix: {args.memory_postfix}")
    print(f"Full memory path: {full_memory_path}")
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
    
    # Step 3: Setup memory directory
    if not setup_memory_directory(args.kb_path, args.memory_postfix):
        print("\n[✗] Installation failed at memory directory setup stage")
        return 1
    
    # Step 4: Create MCP server configuration
    if not create_mcp_server_config(args.workspace, args.kb_path, args.memory_postfix):
        print("\n[✗] Installation failed at MCP server configuration stage")
        return 1
    
    print("\n" + "=" * 60)
    print("Installation Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. The mem-agent MCP server has been registered")
    print("2. Enable it in your config.yaml or .env:")
    print("   AGENT_ENABLE_MCP: true")
    print("   AGENT_ENABLE_MCP_MEMORY: true")
    print(f"3. Memory will be stored in: {full_memory_path}")
    print(f"   (KB: {args.kb_path} + postfix: {args.memory_postfix})")
    print("4. You can change settings in config.yaml or .env:")
    print("   - MEM_AGENT_MODEL (default: driaforall/mem-agent)")
    print(f"   - MEM_AGENT_MEMORY_POSTFIX (default: {default_memory_postfix})")
    print("   - Each user's memory is stored in their KB: kb_path/{postfix}")
    print("\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())