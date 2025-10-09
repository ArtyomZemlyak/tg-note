"""
Tests for Knowledge Base Reading Tools
"""

import tempfile
from pathlib import Path

import pytest

from src.agents.autonomous_agent import AutonomousAgent


@pytest.fixture
def temp_kb():
    """Create a temporary knowledge base for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_path = Path(tmpdir)

        # Create test directory structure
        (kb_path / "topics" / "ai").mkdir(parents=True)
        (kb_path / "topics" / "tech").mkdir(parents=True)

        # Create test files
        (kb_path / "topics" / "ai" / "neural-networks.md").write_text(
            "# Neural Networks\n\nThis is about neural networks and deep learning."
        )
        (kb_path / "topics" / "ai" / "machine-learning.md").write_text(
            "# Machine Learning\n\nBasics of machine learning algorithms."
        )
        (kb_path / "topics" / "tech" / "python.md").write_text(
            "# Python Programming\n\nPython is a versatile programming language."
        )

        yield kb_path


@pytest.mark.asyncio
async def test_kb_read_file(temp_kb):
    """Test reading files from knowledge base"""
    agent = AutonomousAgent(llm_connector=None, kb_root_path=temp_kb)

    # Test reading single file
    result = await agent._tool_kb_read_file({"paths": ["topics/ai/neural-networks.md"]})

    assert result["success"] is True
    assert result["files_read"] == 1
    assert len(result["results"]) == 1
    assert "neural networks" in result["results"][0]["content"].lower()

    # Test reading multiple files
    result = await agent._tool_kb_read_file(
        {"paths": ["topics/ai/neural-networks.md", "topics/tech/python.md"]}
    )

    assert result["success"] is True
    assert result["files_read"] == 2
    assert len(result["results"]) == 2

    # Test reading non-existent file
    result = await agent._tool_kb_read_file({"paths": ["topics/nonexistent.md"]})

    assert result["success"] is False
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_kb_list_directory(temp_kb):
    """Test listing directory contents"""
    agent = AutonomousAgent(llm_connector=None, kb_root_path=temp_kb)

    # Test non-recursive listing
    result = await agent._tool_kb_list_directory({"path": "topics/ai", "recursive": False})

    assert result["success"] is True
    assert result["file_count"] == 2
    assert any(f["name"] == "neural-networks.md" for f in result["files"])
    assert any(f["name"] == "machine-learning.md" for f in result["files"])

    # Test recursive listing
    result = await agent._tool_kb_list_directory({"path": "topics", "recursive": True})

    assert result["success"] is True
    assert result["file_count"] == 3  # All 3 test files

    # Test listing root
    result = await agent._tool_kb_list_directory({"path": "", "recursive": False})

    assert result["success"] is True
    assert result["directory_count"] >= 1  # Should have topics directory


@pytest.mark.asyncio
async def test_kb_search_files(temp_kb):
    """Test searching files by pattern"""
    agent = AutonomousAgent(llm_connector=None, kb_root_path=temp_kb)

    # Test searching for markdown files
    result = await agent._tool_kb_search_files({"pattern": "*.md"})

    assert result["success"] is True
    assert result["file_count"] >= 3

    # Test searching for specific file
    result = await agent._tool_kb_search_files({"pattern": "*neural*"})

    assert result["success"] is True
    assert any("neural" in f["name"].lower() for f in result["files"])

    # Test searching in specific directory
    result = await agent._tool_kb_search_files({"pattern": "topics/ai/*.md"})

    assert result["success"] is True
    assert result["file_count"] == 2


@pytest.mark.asyncio
async def test_kb_search_content(temp_kb):
    """Test searching by file contents"""
    agent = AutonomousAgent(llm_connector=None, kb_root_path=temp_kb)

    # Test searching for content
    result = await agent._tool_kb_search_content(
        {"query": "neural networks", "case_sensitive": False}
    )

    assert result["success"] is True
    assert result["files_found"] >= 1
    assert any("neural-networks.md" in m["name"] for m in result["matches"])

    # Test searching for Python
    result = await agent._tool_kb_search_content({"query": "Python", "case_sensitive": True})

    assert result["success"] is True
    assert result["files_found"] >= 1

    # Test searching with file pattern
    result = await agent._tool_kb_search_content(
        {"query": "machine learning", "file_pattern": "*.md"}
    )

    assert result["success"] is True

    # Test searching for non-existent content
    result = await agent._tool_kb_search_content({"query": "nonexistent content xyz123"})

    assert result["success"] is True
    assert result["files_found"] == 0


@pytest.mark.asyncio
async def test_kb_tools_security(temp_kb):
    """Test security validation for KB tools"""
    agent = AutonomousAgent(llm_connector=None, kb_root_path=temp_kb)

    # Test path traversal prevention
    result = await agent._tool_kb_read_file({"paths": ["../../../etc/passwd"]})

    assert result["success"] is False
    assert len(result["errors"]) > 0
    assert (
        "traversal" in result["errors"][0]["error"].lower() or ".." in result["errors"][0]["error"]
    )

    # Test directory listing path traversal
    result = await agent._tool_kb_list_directory({"path": "../../.."})

    assert result["success"] is False
    assert "traversal" in result["error"].lower() or ".." in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
