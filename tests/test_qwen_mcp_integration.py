"""
Tests for Qwen CLI MCP integration

Tests the standalone MCP server and configuration generator
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.mcp.memory.memory_server import MemoryMCPServer
from src.agents.mcp.memory.memory_storage import MemoryStorage
from src.agents.mcp.qwen_config_generator import QwenMCPConfigGenerator, setup_qwen_mcp_config


class TestMemoryStorage:
    """Test MemoryStorage class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create MemoryStorage instance"""
        return MemoryStorage(temp_dir)

    def test_initialization(self, temp_dir):
        """Test storage initialization"""
        storage = MemoryStorage(temp_dir)

        assert storage.data_dir == temp_dir
        assert storage.data_dir.exists()
        assert storage.memories == []

    def test_store_memory(self, storage):
        """Test storing memory"""
        result = storage.store(content="Test memory", category="test")

        assert result["success"] is True
        assert "memory_id" in result
        assert result["memory_id"] == 1
        assert len(storage.memories) == 1
        assert storage.memories[0]["content"] == "Test memory"
        assert storage.memories[0]["category"] == "test"

    def test_store_multiple_memories(self, storage):
        """Test storing multiple memories"""
        storage.store("Memory 1", "cat1")
        storage.store("Memory 2", "cat2")
        storage.store("Memory 3", "cat1")

        assert len(storage.memories) == 3
        assert storage.memories[0]["id"] == 1
        assert storage.memories[1]["id"] == 2
        assert storage.memories[2]["id"] == 3

    def test_retrieve_all(self, storage):
        """Test retrieving all memories"""
        storage.store("Memory 1", "test")
        storage.store("Memory 2", "test")

        result = storage.retrieve()

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["memories"]) == 2

    def test_retrieve_by_query(self, storage):
        """Test retrieving by query"""
        storage.store("Python programming", "tech")
        storage.store("Machine learning", "ai")
        storage.store("Python ML libraries", "ai")

        result = storage.retrieve(query="python")

        assert result["success"] is True
        assert result["count"] == 2
        # Should find "Python programming" and "Python ML libraries"

    def test_retrieve_by_category(self, storage):
        """Test retrieving by category"""
        storage.store("Memory 1", "cat1")
        storage.store("Memory 2", "cat2")
        storage.store("Memory 3", "cat1")

        result = storage.retrieve(category="cat1")

        assert result["success"] is True
        assert result["count"] == 2
        assert all(m["category"] == "cat1" for m in result["memories"])

    def test_retrieve_with_limit(self, storage):
        """Test retrieving with limit"""
        for i in range(20):
            storage.store(f"Memory {i}", "test")

        result = storage.retrieve(limit=5)

        assert result["count"] == 5
        # Should return last 5
        assert result["memories"][0]["id"] == 16
        assert result["memories"][-1]["id"] == 20

    def test_list_categories(self, storage):
        """Test listing categories"""
        storage.store("M1", "cat1")
        storage.store("M2", "cat1")
        storage.store("M3", "cat2")
        storage.store("M4", "cat1")

        result = storage.list_categories()

        assert result["success"] is True
        assert len(result["categories"]) == 2

        # Find categories in result
        categories_dict = {c["name"]: c["count"] for c in result["categories"]}
        assert categories_dict["cat1"] == 3
        assert categories_dict["cat2"] == 1

    def test_persistence(self, temp_dir):
        """Test that memories persist across instances"""
        # Store some memories
        storage1 = MemoryStorage(temp_dir)
        storage1.store("Persistent memory", "test")
        storage1.store("Another memory", "test")

        # Create new instance and check memories are loaded
        storage2 = MemoryStorage(temp_dir)
        assert len(storage2.memories) == 2
        assert storage2.memories[0]["content"] == "Persistent memory"


class TestMemoryMCPServer:
    """Test MemoryMCPServer class"""

    @pytest.fixture
    def server(self):
        """Create MCP server instance"""
        return MemoryMCPServer(user_id=123)

    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test listing available tools"""
        tools = await server.handle_list_tools()

        assert len(tools) == 3
        tool_names = [t["name"] for t in tools]
        assert "store_memory" in tool_names
        assert "retrieve_memory" in tool_names
        assert "list_categories" in tool_names

        # Check store_memory schema
        store_tool = next(t for t in tools if t["name"] == "store_memory")
        assert "content" in store_tool["inputSchema"]["properties"]
        assert "category" in store_tool["inputSchema"]["properties"]
        assert "content" in store_tool["inputSchema"]["required"]

    @pytest.mark.asyncio
    async def test_call_store_memory(self, server):
        """Test calling store_memory tool"""
        result = await server.handle_call_tool(
            "store_memory", {"content": "Test memory", "category": "test"}
        )

        assert len(result) == 1
        assert result[0]["type"] == "text"

        result_data = json.loads(result[0]["text"])
        assert result_data["success"] is True
        assert "memory_id" in result_data

    @pytest.mark.asyncio
    async def test_call_retrieve_memory(self, server):
        """Test calling retrieve_memory tool"""
        # Store some memories first
        await server.handle_call_tool(
            "store_memory", {"content": "Test memory 1", "category": "test"}
        )
        await server.handle_call_tool(
            "store_memory", {"content": "Test memory 2", "category": "test"}
        )

        # Retrieve
        result = await server.handle_call_tool("retrieve_memory", {"category": "test"})

        assert len(result) == 1
        result_data = json.loads(result[0]["text"])
        assert result_data["success"] is True
        assert result_data["count"] == 2

    @pytest.mark.asyncio
    async def test_call_list_categories(self, server):
        """Test calling list_categories tool"""
        # Store memories in different categories
        await server.handle_call_tool("store_memory", {"content": "M1", "category": "cat1"})
        await server.handle_call_tool("store_memory", {"content": "M2", "category": "cat2"})

        # List categories
        result = await server.handle_call_tool("list_categories", {})

        assert len(result) == 1
        result_data = json.loads(result[0]["text"])
        assert result_data["success"] is True
        assert len(result_data["categories"]) == 2

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, server):
        """Test calling unknown tool"""
        result = await server.handle_call_tool("unknown_tool", {})

        assert len(result) == 1
        result_data = json.loads(result[0]["text"])
        assert result_data["success"] is False
        assert "Unknown tool" in result_data["error"]

    @pytest.mark.asyncio
    async def test_handle_initialize_request(self, server):
        """Test handling initialize request"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        }

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "memory"

    @pytest.mark.asyncio
    async def test_handle_tools_list_request(self, server):
        """Test handling tools/list request"""
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 3

    @pytest.mark.asyncio
    async def test_handle_tools_call_request(self, server):
        """Test handling tools/call request"""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "store_memory",
                "arguments": {"content": "Test", "category": "test"},
            },
        }

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        assert "content" in response["result"]


class TestQwenMCPConfigGenerator:
    """Test QwenMCPConfigGenerator class"""

    @pytest.fixture
    def generator(self):
        """Create config generator"""
        return QwenMCPConfigGenerator(user_id=123)

    def test_initialization(self, generator):
        """Test generator initialization"""
        assert generator.user_id == 123
        assert generator.project_root.exists()

    def test_generate_config(self, generator):
        """Test config generation"""
        config = generator.generate_config()

        assert "mcpServers" in config
        assert "memory" in config["mcpServers"]
        assert "allowMCPServers" in config
        assert "memory" in config["allowMCPServers"]

    def test_memory_config(self, generator):
        """Test memory configuration (HTTP mode by default)"""
        config = generator._generate_memory_config()

        assert config is not None
        assert "url" in config
        assert "trust" in config
        assert config["trust"] is True
        assert config["url"] == "http://127.0.0.1:8765/sse"

        # HTTP mode doesn't use user-id in config (handled by server)
        assert "timeout" in config

    def test_memory_config_no_user_id(self):
        """Test memory config without user ID (HTTP mode)"""
        generator = QwenMCPConfigGenerator(user_id=None)
        config = generator._generate_memory_config()

        assert config is not None
        assert "url" in config
        assert config["url"] == "http://127.0.0.1:8765/sse"

    def test_memory_config_stdio_mode(self):
        """Test memory config in STDIO mode (backward compatibility)"""
        generator = QwenMCPConfigGenerator(user_id=123, use_http=False)
        config = generator._generate_memory_config()

        assert config is not None
        assert "command" in config
        assert "args" in config
        assert "cwd" in config
        assert config["command"] == "python3"

        # Should include user-id argument in STDIO mode
        assert "--user-id" in config["args"]
        assert "123" in config["args"]

    def test_memory_config_custom_port(self):
        """Test memory config with custom HTTP port"""
        generator = QwenMCPConfigGenerator(user_id=None, use_http=True, http_port=9000)
        config = generator._generate_memory_config()

        assert config is not None
        assert "url" in config
        assert config["url"] == "http://127.0.0.1:9000/sse"

    def test_save_to_qwen_dir(self, generator):
        """Test saving to qwen directory"""
        with tempfile.TemporaryDirectory() as tmp:
            qwen_dir = Path(tmp) / ".qwen"

            saved_path = generator.save_to_qwen_dir(qwen_dir)

            assert saved_path.exists()
            assert saved_path.name == "settings.json"

            # Load and verify
            with open(saved_path) as f:
                config = json.load(f)

            assert "mcpServers" in config
            assert "memory" in config["mcpServers"]

    def test_save_to_kb_dir(self, generator):
        """Test saving to KB directory"""
        with tempfile.TemporaryDirectory() as tmp:
            kb_path = Path(tmp)

            saved_path = generator.save_to_kb_dir(kb_path)

            assert saved_path.exists()
            assert saved_path.parent.name == ".qwen"
            assert saved_path.parent.parent == kb_path

    def test_merge_with_existing_config(self, generator):
        """Test merging with existing configuration"""
        with tempfile.TemporaryDirectory() as tmp:
            qwen_dir = Path(tmp) / ".qwen"
            qwen_dir.mkdir()
            settings_file = qwen_dir / "settings.json"

            # Create existing config
            existing = {
                "mcpServers": {"other-server": {"command": "other", "args": []}},
                "allowMCPServers": ["other-server"],
                "otherSetting": "value",
            }
            with open(settings_file, "w") as f:
                json.dump(existing, f)

            # Save our config
            generator.save_to_qwen_dir(qwen_dir)

            # Load and verify merged
            with open(settings_file) as f:
                config = json.load(f)

            assert "memory" in config["mcpServers"]
            assert "other-server" in config["mcpServers"]
            assert "memory" in config["allowMCPServers"]
            assert "other-server" in config["allowMCPServers"]
            assert config["otherSetting"] == "value"

    def test_get_config_json(self, generator):
        """Test getting config as JSON string"""
        json_str = generator.get_config_json()

        config = json.loads(json_str)
        assert "mcpServers" in config
        assert "mem-agent" in config["mcpServers"]


class TestSetupQwenMCPConfig:
    """Test setup_qwen_mcp_config function"""

    def test_global_config_only(self):
        """Test setup with global config only"""
        with tempfile.TemporaryDirectory() as tmp:
            # Mock home directory
            with patch("pathlib.Path.home", return_value=Path(tmp)):
                paths = setup_qwen_mcp_config(user_id=123, global_config=True)

                assert len(paths) == 1
                assert paths[0].exists()
                assert ".qwen" in str(paths[0])

    def test_kb_config_only(self):
        """Test setup with KB config only"""
        with tempfile.TemporaryDirectory() as tmp:
            kb_path = Path(tmp)

            paths = setup_qwen_mcp_config(user_id=123, kb_path=kb_path, global_config=False)

            assert len(paths) == 1
            assert paths[0].exists()
            assert paths[0].parent.parent == kb_path

    def test_both_configs(self):
        """Test setup with both global and KB configs"""
        with tempfile.TemporaryDirectory() as tmp:
            kb_path = Path(tmp) / "kb"
            kb_path.mkdir()

            with patch("pathlib.Path.home", return_value=Path(tmp)):
                paths = setup_qwen_mcp_config(user_id=123, kb_path=kb_path, global_config=True)

                assert len(paths) == 2
                assert all(p.exists() for p in paths)
