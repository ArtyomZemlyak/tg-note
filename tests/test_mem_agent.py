"""
Unit tests for mem-agent implementation
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_mem_agent_imports():
    """Test that mem-agent modules can be imported"""
    try:
        from src.mcp.memory.mem_agent_impl import Agent, AgentResponse, ChatMessage, Role

        assert Agent is not None
        assert AgentResponse is not None
        assert ChatMessage is not None
        assert Role is not None
    except ImportError as e:
        pytest.fail(f"Failed to import mem-agent modules: {e}")


def test_mem_agent_settings():
    """Test that mem-agent settings can be loaded"""
    try:
        from config.settings import (
            FILE_SIZE_LIMIT,
            MAX_TOOL_TURNS,
            SANDBOX_TIMEOUT,
            get_memory_path,
        )

        assert isinstance(MAX_TOOL_TURNS, int)
        assert MAX_TOOL_TURNS > 0
        assert isinstance(FILE_SIZE_LIMIT, int)
        assert isinstance(SANDBOX_TIMEOUT, int)

        # Test get_memory_path function
        path = get_memory_path()
        assert isinstance(path, Path)

        kb_path = Path("/tmp/test_kb")
        memory_path = get_memory_path(kb_path)
        assert isinstance(memory_path, Path)
        assert "memory" in str(memory_path)

    except Exception as e:
        pytest.fail(f"Failed to load mem-agent settings: {e}")


def test_mem_agent_schemas():
    """Test that mem-agent schemas work correctly"""
    from src.mcp.memory.mem_agent_impl.schemas import AgentResponse, ChatMessage, Role

    # Test ChatMessage
    msg = ChatMessage(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"

    # Test AgentResponse
    response = AgentResponse(
        thoughts="Thinking...", reply="Hello back", python_block="print('test')"
    )
    assert response.thoughts == "Thinking..."
    assert response.reply == "Hello back"
    assert response.python_block == "print('test')"


def test_mem_agent_utils():
    """Test mem-agent utility functions"""
    from src.mcp.memory.mem_agent_impl.utils import (
        extract_python_code,
        extract_reply,
        extract_thoughts,
        format_results,
    )

    # Test extraction functions
    response = """
    <think>I need to check the file</think>
    <python>
    content = read_file("user.md")
    </python>
    """

    thoughts = extract_thoughts(response)
    assert "check the file" in thoughts

    python_code = extract_python_code(response)
    assert "read_file" in python_code

    # Test reply extraction
    response_with_reply = """
    <think>No code needed</think>
    <python></python>
    <reply>Here is your answer</reply>
    """

    reply = extract_reply(response_with_reply)
    assert "answer" in reply

    # Test format_results
    results = {"var": "value"}
    formatted = format_results(results)
    assert "<result>" in formatted
    assert "var" in formatted


def test_mem_agent_tools():
    """Test mem-agent tool functions"""
    from src.mcp.memory.mem_agent_impl.tools import (
        check_if_file_exists,
        create_file,
        list_files,
        read_file,
    )

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # Test file creation
        result = create_file("test.md", "Test content")
        assert result is True

        # Test file existence check
        exists = check_if_file_exists("test.md")
        assert exists is True

        # Test file reading
        content = read_file("test.md")
        assert content == "Test content"

        # Test list_files
        file_list = list_files()
        assert "test.md" in file_list


def test_mcp_server_import():
    """Test that MCP server can be imported"""
    try:
        from src.mcp.memory.mem_agent_impl.mcp_server import get_agent, mcp

        assert mcp is not None
        assert callable(get_agent)
    except ImportError as e:
        # fastmcp is an optional dependency - skip test if not installed
        if "fastmcp" in str(e):
            pytest.skip(f"Skipping MCP server test - fastmcp not installed: {e}")
        else:
            pytest.fail(f"Failed to import MCP server: {e}")


def test_agent_response_format():
    """Test AgentResponse string formatting"""
    from src.mcp.memory.mem_agent_impl.schemas import AgentResponse

    response = AgentResponse(
        thoughts="Testing thoughts", reply="Testing reply", python_block="x = 1"
    )

    response_str = str(response)
    assert "Thoughts:" in response_str
    assert "Reply:" in response_str
    assert "Testing" in response_str


def test_static_memory_schema():
    """Test StaticMemory schema"""
    from src.mcp.memory.mem_agent_impl.schemas import EntityFile, StaticMemory

    entity = EntityFile(
        entity_name="test_entity",
        entity_file_path="entities/test.md",
        entity_file_content="# Test Entity\n",
    )

    memory = StaticMemory(
        memory_id="test_memory", user_md="# User\n- name: Test", entities=[entity]
    )

    assert memory.memory_id == "test_memory"
    assert len(memory.entities) == 1
    assert memory.entities[0].entity_name == "test_entity"


def test_sandbox_safety():
    """Test that sandbox environment is configured for safety"""
    from config.settings import FILE_SIZE_LIMIT, SANDBOX_TIMEOUT

    # Verify safety limits are reasonable
    assert SANDBOX_TIMEOUT > 0 and SANDBOX_TIMEOUT <= 60, "Timeout should be reasonable"
    assert FILE_SIZE_LIMIT > 0, "File size limit should be positive"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
