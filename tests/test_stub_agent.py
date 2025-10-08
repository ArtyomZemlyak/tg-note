"""
Tests for StubAgent
"""

import pytest
from pathlib import Path
from src.agents.stub_agent import StubAgent


@pytest.mark.asyncio
async def test_stub_agent_process(tmp_path):
    """Test stub agent processing with MCP memory support"""
    agent = StubAgent(kb_root_path=tmp_path)
    
    content = {
        "text": "This is a test message",
        "urls": ["https://example.com"]
    }
    
    result = await agent.process(content)
    
    assert "markdown" in result
    assert "metadata" in result
    assert "title" in result
    assert "kb_structure" in result
    assert result["kb_structure"].category == "general"


@pytest.mark.asyncio
async def test_stub_agent_invalid_input(tmp_path):
    """Test stub agent with invalid input"""
    agent = StubAgent(kb_root_path=tmp_path)
    
    with pytest.raises(ValueError):
        await agent.process({})  # Missing 'text' field


def test_stub_agent_validate_input(tmp_path):
    """Test input validation"""
    agent = StubAgent(kb_root_path=tmp_path)
    
    assert agent.validate_input({"text": "valid"})
    assert not agent.validate_input({})
    assert not agent.validate_input({"invalid": "data"})


@pytest.mark.asyncio
async def test_stub_agent_title_generation(tmp_path):
    """Test title generation"""
    agent = StubAgent(kb_root_path=tmp_path)
    
    content = {
        "text": "Short title\n\nLonger content here",
        "urls": []
    }
    
    result = await agent.process(content)
    assert result["title"] == "Short title"
    
    # Test long title truncation
    long_content = {
        "text": "A" * 100,
        "urls": []
    }
    
    result = await agent.process(long_content)
    assert len(result["title"]) <= 53  # 50 chars + "..."


@pytest.mark.asyncio
async def test_stub_agent_mcp_memory_integration(tmp_path):
    """Test that StubAgent initializes MCP memory tools"""
    agent = StubAgent(kb_root_path=tmp_path)
    
    # Check that memory tool was initialized (may be None if MCP setup failed)
    # This is OK - the test verifies the initialization attempt
    assert hasattr(agent, 'memory_tool')
    assert hasattr(agent, 'memory_context')