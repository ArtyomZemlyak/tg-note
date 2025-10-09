"""
Tests for StubAgent
"""

import pytest
from src.agents.stub_agent import StubAgent


@pytest.mark.asyncio
async def test_stub_agent_process():
    """Test stub agent processing"""
    agent = StubAgent()
    
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
async def test_stub_agent_invalid_input():
    """Test stub agent with invalid input"""
    agent = StubAgent()
    
    with pytest.raises(ValueError):
        await agent.process({})  # Missing 'text' field


def test_stub_agent_validate_input():
    """Test input validation"""
    agent = StubAgent()
    
    assert agent.validate_input({"text": "valid"})
    assert not agent.validate_input({})
    assert not agent.validate_input({"invalid": "data"})


@pytest.mark.asyncio
async def test_stub_agent_title_generation():
    """Test title generation"""
    agent = StubAgent()
    
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
    assert len(result["title"]) <= 63  # 60 chars + "..." (MAX_TITLE_LENGTH=60)