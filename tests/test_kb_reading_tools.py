"""
Tests for Knowledge Base Reading Tools

AICODE-NOTE: Multi-Stage Search Strategy
These tools are designed to work together in a 3-stage search approach:

Stage 1: File Search (kb_search_files)
  - Search files by name patterns based on keywords
  - Quick discovery of relevant files by filename

Stage 2: Vector Search (kb_vector_search)
  - Semantic search across entire knowledge base
  - Finds semantically similar content

Stage 3: Refined Search (kb_search_content + kb_read_file)
  - Search specific terms in promising files
  - Read most relevant files
  - Optional: Another targeted vector search with refined query

This strategy ensures optimal information retrieval by combining:
- Fast file-based search (Stage 1)
- AI-powered semantic search (Stage 2)
- Detailed content analysis (Stage 3)
"""

import tempfile
from pathlib import Path

import pytest

from src.agents.tools.base_tool import ToolContext
from src.agents.tools.kb_reading_tools import (
    KBListDirectoryTool,
    KBReadFileTool,
    KBSearchContentTool,
    KBSearchFilesTool,
)


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


@pytest.fixture
def tool_context(temp_kb):
    """Create a tool context for testing"""
    from src.agents.base_agent import BaseAgent

    return ToolContext(kb_root_path=temp_kb, base_agent_class=BaseAgent)


@pytest.mark.asyncio
async def test_kb_read_file(tool_context):
    """Test reading files from knowledge base (Stage 3 of multi-stage search)"""
    tool = KBReadFileTool()

    # Test reading single file
    result = await tool.execute({"paths": ["topics/ai/neural-networks.md"]}, tool_context)

    assert result["success"] is True
    assert result["files_read"] == 1
    assert len(result["results"]) == 1
    assert "neural networks" in result["results"][0]["content"].lower()

    # Test reading multiple files
    result = await tool.execute(
        {"paths": ["topics/ai/neural-networks.md", "topics/tech/python.md"]}, tool_context
    )

    assert result["success"] is True
    assert result["files_read"] == 2
    assert len(result["results"]) == 2

    # Test reading non-existent file
    result = await tool.execute({"paths": ["topics/nonexistent.md"]}, tool_context)

    assert result["success"] is False
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_kb_list_directory(tool_context):
    """Test listing directory contents"""
    tool = KBListDirectoryTool()

    # Test non-recursive listing
    result = await tool.execute({"path": "topics/ai", "recursive": False}, tool_context)

    assert result["success"] is True
    assert result["file_count"] == 2
    assert any(f["name"] == "neural-networks.md" for f in result["files"])
    assert any(f["name"] == "machine-learning.md" for f in result["files"])

    # Test recursive listing
    result = await tool.execute({"path": "topics", "recursive": True}, tool_context)

    assert result["success"] is True
    assert result["file_count"] == 3  # All 3 test files

    # Test listing root
    result = await tool.execute({"path": "", "recursive": False}, tool_context)

    assert result["success"] is True
    assert result["directory_count"] >= 1  # Should have topics directory


@pytest.mark.asyncio
async def test_kb_search_files(tool_context):
    """Test searching files by pattern (Stage 1 of multi-stage search)"""
    tool = KBSearchFilesTool()

    # Test searching for markdown files
    result = await tool.execute({"pattern": "*.md"}, tool_context)

    assert result["success"] is True
    assert result["file_count"] >= 3

    # Test searching for specific file
    result = await tool.execute({"pattern": "*neural*"}, tool_context)

    assert result["success"] is True
    assert any("neural" in f["name"].lower() for f in result["files"])

    # Test searching in specific directory
    result = await tool.execute({"pattern": "topics/ai/*.md"}, tool_context)

    assert result["success"] is True
    assert result["file_count"] == 2


@pytest.mark.asyncio
async def test_kb_search_content(tool_context):
    """Test searching by file contents (Stage 3 of multi-stage search)"""
    tool = KBSearchContentTool()

    # Test searching for content
    result = await tool.execute({"query": "neural networks", "case_sensitive": False}, tool_context)

    assert result["success"] is True
    assert result["files_found"] >= 1
    assert any("neural-networks.md" in m["name"] for m in result["matches"])

    # Test searching for Python
    result = await tool.execute({"query": "Python", "case_sensitive": True}, tool_context)

    assert result["success"] is True
    assert result["files_found"] >= 1

    # Test searching with file pattern
    result = await tool.execute({"query": "machine learning", "file_pattern": "*.md"}, tool_context)

    assert result["success"] is True

    # Test searching for non-existent content
    result = await tool.execute({"query": "nonexistent content xyz123"}, tool_context)

    assert result["success"] is True
    assert result["files_found"] == 0


@pytest.mark.asyncio
async def test_multi_stage_search_workflow(tool_context):
    """
    Test multi-stage search workflow integration

    AICODE-NOTE: This test demonstrates the complete 3-stage search strategy:
    Stage 1: File search by pattern
    Stage 2: Vector search (mocked, as it requires embeddings)
    Stage 3: Content search + read files
    """
    # Stage 1: File search - find files by name pattern
    search_files_tool = KBSearchFilesTool()
    stage1_result = await search_files_tool.execute({"pattern": "*neural*"}, tool_context)

    assert stage1_result["success"] is True
    assert stage1_result["file_count"] >= 1
    stage1_files = [f["path"] for f in stage1_result["files"]]

    # Stage 2 would normally use vector search (kb_vector_search)
    # Skipped in this test as it requires vector embeddings setup
    # In real usage: kb_vector_search(query="neural networks deep learning", top_k=5)

    # Stage 3a: Content search in promising files
    search_content_tool = KBSearchContentTool()
    stage3a_result = await search_content_tool.execute(
        {"query": "deep learning", "file_pattern": "*.md"}, tool_context
    )

    assert stage3a_result["success"] is True

    # Stage 3b: Read most relevant files
    read_tool = KBReadFileTool()
    if stage1_files:
        stage3b_result = await read_tool.execute({"paths": stage1_files[:2]}, tool_context)

        assert stage3b_result["success"] is True
        assert stage3b_result["files_read"] >= 1

        # Verify we got actual content
        assert len(stage3b_result["results"]) >= 1
        assert len(stage3b_result["results"][0]["content"]) > 0


@pytest.mark.asyncio
async def test_kb_tools_security(tool_context):
    """Test security validation for KB tools"""
    read_tool = KBReadFileTool()
    list_tool = KBListDirectoryTool()

    # Test path traversal prevention
    result = await read_tool.execute({"paths": ["../../../etc/passwd"]}, tool_context)

    assert result["success"] is False
    assert len(result["errors"]) > 0
    assert (
        "traversal" in result["errors"][0]["error"].lower() or ".." in result["errors"][0]["error"]
    )

    # Test directory listing path traversal
    result = await list_tool.execute({"path": "../../.."}, tool_context)

    assert result["success"] is False
    assert "traversal" in result["error"].lower() or ".." in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
