"""
Tests for error handling across agents and KB manager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent
from src.agents.base_agent import KBStructure
from src.knowledge_base.manager import KnowledgeBaseManager
import tempfile
from pathlib import Path


class TestKBStructureErrorHandling:
    """Test error handling in KBStructure"""
    
    def test_get_relative_path_with_none_category(self):
        """Test get_relative_path handles None category"""
        kb_structure = KBStructure(category=None)
        path = kb_structure.get_relative_path()
        
        # Should use default 'general' category
        assert path == "topics/general"
    
    def test_get_relative_path_with_none_subcategory(self):
        """Test get_relative_path handles None subcategory"""
        kb_structure = KBStructure(category="ai", subcategory=None)
        path = kb_structure.get_relative_path()
        
        assert path == "topics/ai"
        assert "None" not in path
    
    def test_get_relative_path_with_all_none(self):
        """Test get_relative_path when everything is None"""
        kb_structure = KBStructure(category=None, subcategory=None)
        path = kb_structure.get_relative_path()
        
        # Should still work with default category
        assert path == "topics/general"
        assert "None" not in path


class TestQwenCodeCLIAgentErrorHandling:
    """Test error handling in QwenCodeCLIAgent"""
    
    @pytest.fixture
    def mock_cli_check(self):
        """Mock CLI availability check"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="qwen version 1.0.0",
                stderr=""
            )
            yield mock_run
    
    @pytest.fixture
    def agent(self, mock_cli_check):
        """Create test agent with mocked CLI"""
        return QwenCodeCLIAgent()
    
    def test_parse_result_with_empty_metadata(self, agent):
        """Test parsing result with empty metadata values"""
        result_text = """# Test
```metadata
category: 
subcategory: 
tags: 
```
Content here.
"""
        
        parsed = agent._parse_qwen_result(result_text)
        
        # Should have defaults
        assert parsed["title"] == "Test"
        assert parsed["category"] == "general"
        assert parsed["tags"] == ["untagged"]
    
    def test_parse_result_with_invalid_metadata(self, agent):
        """Test parsing result with malformed metadata"""
        result_text = """# Test
```metadata
category ai
subcategory
tags ml neural
```
Content here.
"""
        
        parsed = agent._parse_qwen_result(result_text)
        
        # Should handle gracefully with defaults
        assert parsed["title"] == "Test"
        assert parsed["category"] == "general"
        assert parsed["tags"] == ["untagged"]
    
    def test_parse_result_no_title(self, agent):
        """Test parsing result without title"""
        result_text = "Some content without a title heading"
        
        parsed = agent._parse_qwen_result(result_text)
        
        # Should have default title
        assert parsed["title"] == "Untitled Note"
    
    def test_fallback_processing_empty_content(self, agent):
        """Test fallback processing with empty content"""
        prompt = """
## Text Content

## URLs
# Task
"""
        
        result = agent._fallback_processing(prompt)
        
        # Should still produce valid markdown
        assert "# " in result
        assert "No content available" in result or "Untitled Note" in result
    
    @pytest.mark.asyncio
    async def test_process_invalid_input(self, agent):
        """Test process with invalid input"""
        invalid_content = {"no_text_key": "value"}
        
        with pytest.raises(ValueError) as exc_info:
            await agent.process(invalid_content)
        
        assert "must be a dict with 'text' key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_cli_non_zero_exit(self, agent):
        """Test CLI execution with non-zero exit code"""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: authentication required")
        )
        mock_process.returncode = 1
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(RuntimeError) as exc_info:
                await agent._execute_qwen_cli("test prompt")
            
            assert "Qwen CLI execution failed" in str(exc_info.value)
            assert "authentication required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_cli_empty_result_fallback(self, agent):
        """Test that empty CLI result triggers fallback"""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await agent._execute_qwen_cli("test prompt\n\n## Text Content\nTest content")
            
            # Should use fallback and return valid markdown
            assert len(result) > 0
            assert "# " in result
    
    @pytest.mark.asyncio
    async def test_process_with_fallback_error(self, agent):
        """Test process when both CLI and fallback fail"""
        sample_content = {"text": "test"}
        
        # Mock CLI to return empty
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Mock fallback to raise error
            with patch.object(agent, "_fallback_processing", side_effect=Exception("Fallback failed")):
                with pytest.raises(RuntimeError) as exc_info:
                    await agent._execute_qwen_cli("prompt")
                
                assert "fallback processing failed" in str(exc_info.value).lower()
    
    def test_cli_check_non_zero_exit(self):
        """Test CLI availability check with non-zero exit"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Command not found"
            )
            
            with pytest.raises(RuntimeError) as exc_info:
                QwenCodeCLIAgent()
            
            assert "Qwen CLI check failed" in str(exc_info.value)
    
    def test_cli_check_timeout(self):
        """Test CLI availability check timeout"""
        import subprocess
        
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("qwen", 10)):
            with pytest.raises(RuntimeError) as exc_info:
                QwenCodeCLIAgent()
            
            assert "timed out" in str(exc_info.value).lower()


class TestKnowledgeBaseManagerErrorHandling:
    """Test error handling in KnowledgeBaseManager"""
    
    @pytest.fixture
    def temp_kb_path(self):
        """Create temporary KB path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def kb_manager(self, temp_kb_path):
        """Create KB manager with temp path"""
        return KnowledgeBaseManager(str(temp_kb_path))
    
    def test_create_article_none_content(self, kb_manager):
        """Test create_article with None content"""
        kb_structure = KBStructure(category="test")
        
        with pytest.raises(ValueError) as exc_info:
            kb_manager.create_article(
                content=None,
                title="Test",
                kb_structure=kb_structure
            )
        
        assert "content cannot be empty" in str(exc_info.value).lower()
    
    def test_create_article_empty_content(self, kb_manager):
        """Test create_article with empty content"""
        kb_structure = KBStructure(category="test")
        
        with pytest.raises(ValueError) as exc_info:
            kb_manager.create_article(
                content="",
                title="Test",
                kb_structure=kb_structure
            )
        
        assert "content cannot be empty" in str(exc_info.value).lower()
    
    def test_create_article_none_title(self, kb_manager):
        """Test create_article with None title"""
        kb_structure = KBStructure(category="test")
        
        with pytest.raises(ValueError) as exc_info:
            kb_manager.create_article(
                content="Test content",
                title=None,
                kb_structure=kb_structure
            )
        
        assert "title cannot be empty" in str(exc_info.value).lower()
    
    def test_create_article_none_kb_structure(self, kb_manager):
        """Test create_article with None KB structure"""
        with pytest.raises(ValueError) as exc_info:
            kb_manager.create_article(
                content="Test content",
                title="Test",
                kb_structure=None
            )
        
        assert "KB structure cannot be None" in str(exc_info.value)
    
    def test_create_article_invalid_kb_structure_type(self, kb_manager):
        """Test create_article with invalid KB structure type"""
        with pytest.raises(TypeError) as exc_info:
            kb_manager.create_article(
                content="Test content",
                title="Test",
                kb_structure={"category": "test"}  # Wrong type
            )
        
        assert "must be KBStructure instance" in str(exc_info.value)
    
    def test_create_article_none_category(self, kb_manager):
        """Test create_article with None category in KB structure"""
        kb_structure = KBStructure(category=None)
        
        with pytest.raises(ValueError) as exc_info:
            kb_manager.create_article(
                content="Test content",
                title="Test",
                kb_structure=kb_structure
            )
        
        assert "valid category" in str(exc_info.value).lower()
    
    def test_create_article_valid(self, kb_manager):
        """Test create_article with valid inputs"""
        kb_structure = KBStructure(category="ai", tags=["ml", "test"])
        
        result = kb_manager.create_article(
            content="Test content",
            title="Test Article",
            kb_structure=kb_structure
        )
        
        assert result.exists()
        assert result.suffix == ".md"
        assert "test-article" in result.name


class TestIntegratedErrorHandling:
    """Test error handling across the full processing chain"""
    
    @pytest.fixture
    def mock_cli_check(self):
        """Mock CLI availability check"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="qwen version 1.0.0",
                stderr=""
            )
            yield mock_run
    
    @pytest.fixture
    def agent(self, mock_cli_check):
        """Create test agent"""
        return QwenCodeCLIAgent()
    
    @pytest.fixture
    def temp_kb_path(self):
        """Create temporary KB path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def kb_manager(self, temp_kb_path):
        """Create KB manager"""
        return KnowledgeBaseManager(str(temp_kb_path))
    
    @pytest.mark.asyncio
    async def test_end_to_end_with_minimal_cli_output(self, agent, kb_manager):
        """Test full workflow when CLI returns minimal output"""
        content = {"text": "Test about machine learning"}
        
        # Mock CLI to return minimal result (just title, no metadata)
        minimal_result = "# ML Article\n\nSome content about ML"
        
        with patch.object(agent, "_execute_qwen_cli", return_value=minimal_result):
            # Process content
            result = await agent.process(content)
            
            # Should have defaults filled in
            assert result["title"] is not None
            assert result["kb_structure"] is not None
            assert result["kb_structure"].category is not None
            
            # Should be able to create article
            kb_file = kb_manager.create_article(
                content=result["markdown"],
                title=result["title"],
                kb_structure=result["kb_structure"],
                metadata=result["metadata"]
            )
            
            assert kb_file.exists()
    
    @pytest.mark.asyncio
    async def test_end_to_end_with_empty_cli_output(self, agent, kb_manager):
        """Test full workflow when CLI returns empty"""
        content = {"text": "Test about AI and neural networks"}
        
        # Mock CLI to return empty (triggers fallback)
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Process content
            result = await agent.process(content)
            
            # Should have valid defaults from fallback
            assert result["title"] is not None
            assert result["markdown"] is not None
            assert result["kb_structure"] is not None
            assert result["kb_structure"].category is not None
            
            # Should be able to create article
            kb_file = kb_manager.create_article(
                content=result["markdown"],
                title=result["title"],
                kb_structure=result["kb_structure"],
                metadata=result["metadata"]
            )
            
            assert kb_file.exists()
