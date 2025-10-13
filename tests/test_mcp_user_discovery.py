"""
Tests for per-user MCP server discovery
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.mcp.registry import MCPServerRegistry, MCPServersManager


@pytest.fixture
def temp_mcp_dir():
    """Create temporary directory for MCP server configs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_shared_server_discovery(temp_mcp_dir):
    """Test discovery of shared MCP servers"""
    # Create a shared server config
    shared_config = {
        "name": "shared-server",
        "description": "Shared MCP server",
        "command": "python",
        "args": ["-m", "server"],
        "enabled": True,
    }

    shared_file = temp_mcp_dir / "shared-server.json"
    with open(shared_file, "w") as f:
        json.dump(shared_config, f)

    # Discover servers without user_id (should find shared only)
    registry = MCPServerRegistry(temp_mcp_dir)
    registry.discover_servers()

    servers = registry.get_all_servers()
    assert len(servers) == 1
    assert servers[0].name == "shared-server"


def test_per_user_server_discovery(temp_mcp_dir):
    """Test discovery of per-user MCP servers"""
    # Create a shared server
    shared_config = {
        "name": "shared-server",
        "description": "Shared MCP server",
        "command": "python",
        "args": ["-m", "server"],
        "enabled": True,
    }
    shared_file = temp_mcp_dir / "shared-server.json"
    with open(shared_file, "w") as f:
        json.dump(shared_config, f)

    # Create user-specific directory and server
    user_dir = temp_mcp_dir / "user_123"
    user_dir.mkdir()

    user_config = {
        "name": "user-server",
        "description": "User-specific MCP server",
        "command": "python",
        "args": ["-m", "user_server"],
        "enabled": True,
    }
    user_file = user_dir / "user-server.json"
    with open(user_file, "w") as f:
        json.dump(user_config, f)

    # Discover servers with user_id
    registry = MCPServerRegistry(temp_mcp_dir, user_id=123)
    registry.discover_servers()

    servers = registry.get_all_servers()
    assert len(servers) == 2

    server_names = {s.name for s in servers}
    assert "shared-server" in server_names
    assert "user-server" in server_names


def test_user_override_shared_server(temp_mcp_dir):
    """Test that user-specific servers override shared ones"""
    # Create a shared server
    shared_config = {
        "name": "test-server",
        "description": "Shared version",
        "command": "python",
        "args": ["-m", "shared_server"],
        "enabled": True,
    }
    shared_file = temp_mcp_dir / "test-server.json"
    with open(shared_file, "w") as f:
        json.dump(shared_config, f)

    # Create user-specific override
    user_dir = temp_mcp_dir / "user_456"
    user_dir.mkdir()

    user_config = {
        "name": "test-server",
        "description": "User override",
        "command": "python",
        "args": ["-m", "user_server"],
        "enabled": True,
    }
    user_file = user_dir / "test-server.json"
    with open(user_file, "w") as f:
        json.dump(user_config, f)

    # Discover servers with user_id
    registry = MCPServerRegistry(temp_mcp_dir, user_id=456)
    registry.discover_servers()

    servers = registry.get_all_servers()
    assert len(servers) == 1

    server = servers[0]
    assert server.name == "test-server"
    assert server.description == "User override"
    assert server.args == ["-m", "user_server"]


def test_manager_with_user_id(temp_mcp_dir):
    """Test MCPServersManager with user_id"""
    # Create shared and user-specific servers
    shared_config = {
        "name": "shared",
        "description": "Shared server",
        "command": "python",
        "args": ["-m", "shared"],
        "enabled": True,
    }
    with open(temp_mcp_dir / "shared.json", "w") as f:
        json.dump(shared_config, f)

    user_dir = temp_mcp_dir / "user_789"
    user_dir.mkdir()

    user_config = {
        "name": "private",
        "description": "Private server",
        "command": "python",
        "args": ["-m", "private"],
        "enabled": True,
    }
    with open(user_dir / "private.json", "w") as f:
        json.dump(user_config, f)

    # Create manager with user_id
    manager = MCPServersManager(servers_dir=temp_mcp_dir, user_id=789)
    manager.initialize()

    all_servers = manager.get_all_servers()
    assert len(all_servers) == 2

    server_names = {s.name for s in all_servers}
    assert "shared" in server_names
    assert "private" in server_names


def test_multiple_users_isolation(temp_mcp_dir):
    """Test that different users get different servers"""
    # Create shared server
    shared_config = {
        "name": "shared",
        "description": "Shared server",
        "command": "python",
        "args": ["-m", "shared"],
        "enabled": True,
    }
    with open(temp_mcp_dir / "shared.json", "w") as f:
        json.dump(shared_config, f)

    # Create user 111's server
    user_111_dir = temp_mcp_dir / "user_111"
    user_111_dir.mkdir()
    user_111_config = {
        "name": "user-111-server",
        "description": "User 111 server",
        "command": "python",
        "args": ["-m", "user111"],
        "enabled": True,
    }
    with open(user_111_dir / "user-111-server.json", "w") as f:
        json.dump(user_111_config, f)

    # Create user 222's server
    user_222_dir = temp_mcp_dir / "user_222"
    user_222_dir.mkdir()
    user_222_config = {
        "name": "user-222-server",
        "description": "User 222 server",
        "command": "python",
        "args": ["-m", "user222"],
        "enabled": True,
    }
    with open(user_222_dir / "user-222-server.json", "w") as f:
        json.dump(user_222_config, f)

    # User 111's registry
    registry_111 = MCPServerRegistry(temp_mcp_dir, user_id=111)
    registry_111.discover_servers()
    servers_111 = registry_111.get_all_servers()

    # User 222's registry
    registry_222 = MCPServerRegistry(temp_mcp_dir, user_id=222)
    registry_222.discover_servers()
    servers_222 = registry_222.get_all_servers()

    # Both should see shared server
    names_111 = {s.name for s in servers_111}
    names_222 = {s.name for s in servers_222}

    assert "shared" in names_111
    assert "shared" in names_222

    # Each should see only their own user-specific server
    assert "user-111-server" in names_111
    assert "user-111-server" not in names_222

    assert "user-222-server" in names_222
    assert "user-222-server" not in names_111


def test_disabled_user_server(temp_mcp_dir):
    """Test that disabled user servers are not returned by get_enabled_servers"""
    # Create user directory
    user_dir = temp_mcp_dir / "user_999"
    user_dir.mkdir()

    # Create enabled server
    enabled_config = {
        "name": "enabled-server",
        "description": "Enabled server",
        "command": "python",
        "args": ["-m", "enabled"],
        "enabled": True,
    }
    with open(user_dir / "enabled.json", "w") as f:
        json.dump(enabled_config, f)

    # Create disabled server
    disabled_config = {
        "name": "disabled-server",
        "description": "Disabled server",
        "command": "python",
        "args": ["-m", "disabled"],
        "enabled": False,
    }
    with open(user_dir / "disabled.json", "w") as f:
        json.dump(disabled_config, f)

    # Discover with user_id
    manager = MCPServersManager(servers_dir=temp_mcp_dir, user_id=999)
    manager.initialize()

    all_servers = manager.get_all_servers()
    enabled_servers = manager.get_enabled_servers()

    assert len(all_servers) == 2
    assert len(enabled_servers) == 1
    assert enabled_servers[0].name == "enabled-server"
