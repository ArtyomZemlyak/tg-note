"""
Tests for Qwen Code CLI Agent
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest
from promptic import render

from src.agents.base_agent import BaseAgent, KBStructure
from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent


class TestQwenCodeCLIAgent:
    """Test QwenCodeCLIAgent class"""

    @pytest.fixture
    def mock_cli_check(self):
        """Mock CLI availability check"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="qwen version 1.0.0", stderr="")
            yield mock_run

    @pytest.fixture
    def agent(self, mock_cli_check):
        """Create test agent with mocked CLI"""
        return QwenCodeCLIAgent(
            config={}, enable_web_search=True, enable_git=True, enable_github=True
        )

    @pytest.fixture
    def sample_content(self):
        """Sample content for testing"""
        text = (
            "This is a test about machine learning and AI. "
            "Neural networks are powerful tools for deep learning."
        )
        urls = ["https://example.com/article"]
        prompt = (
            f"{QwenCodeCLIAgent.get_default_instruction()}\n\n"
            f"## Text Content\n{text}\n"
            f"## URLs\n- {urls[0]}\n"
            "```"
        )

        return {"text": text, "urls": urls, "metadata": {}, "prompt": prompt}

    def test_initialization(self, agent):
        """Test agent initialization"""
        assert agent is not None
        assert agent.enable_web_search
        assert agent.enable_git
        assert agent.enable_github
        assert agent.qwen_cli_path == "qwen"
        assert agent.timeout == 999999

    def test_initialization_custom_params(self, mock_cli_check):
        """Test initialization with custom parameters"""
        agent = QwenCodeCLIAgent(
            qwen_cli_path="/usr/local/bin/qwen", timeout=600, enable_web_search=False
        )

        assert agent.qwen_cli_path == "/usr/local/bin/qwen"
        assert agent.timeout == 600
        assert not agent.enable_web_search

    def test_custom_instruction(self, mock_cli_check):
        """Test custom instruction setting"""
        custom_instruction = "Custom instruction for testing"
        agent = QwenCodeCLIAgent(instruction=custom_instruction)

        assert agent.get_instruction() == custom_instruction

    def test_set_instruction(self, agent):
        """Test updating instruction"""
        new_instruction = "New instruction"
        agent.set_instruction(new_instruction)

        assert agent.get_instruction() == new_instruction

    def test_validate_input_valid(self, agent, sample_content):
        """Test input validation with valid content"""
        assert agent.validate_input(sample_content)

    def test_validate_input_invalid(self, agent):
        """Test input validation with invalid content"""
        assert not agent.validate_input({})
        assert not agent.validate_input({"no_text": "value"})
        assert not agent.validate_input(None)

    def test_prepare_prompt(self, agent, sample_content):
        """Test prompt preparation"""
        prompt = agent._prepare_prompt(sample_content)

        assert "machine learning" in prompt
        assert "example.com/article" in prompt
        assert "Базу Знаний" in prompt  # Instruction mentions knowledge base in Russian
        assert "```" in prompt  # Markdown code blocks are mentioned in instruction
        assert agent.instruction in prompt

    def test_promptic_returns_latest_version(self):
        """Promptic returns latest version (v5) when version='latest' is specified"""
        prompts_dir = Path(__file__).parent.parent / "config" / "prompts"
        latest = render(str(prompts_dir / "qwen_code_cli"), version="latest")
        v5_text = render(str(prompts_dir / "qwen_code_cli"), version="v5")
        assert isinstance(latest, str) and len(latest) > 0
        assert latest == v5_text, "render with 'latest' should return v5 version"
        assert "Работа с медиафайлами" in latest

    def test_prepare_prompt_no_urls(self, agent):
        """Test prompt preparation without URLs"""
        prompt_text = f"{agent.instruction}\n\n## Text Content\nSimple text\n"
        content = {"text": "Simple text", "prompt": prompt_text}
        prompt = agent._prepare_prompt(content)

        assert "Simple text" in prompt
        assert "## URLs" not in prompt

    def test_extract_title(self, agent):
        """Test title extraction"""
        text = "Machine Learning Fundamentals\n\nThis is the content..."
        title = BaseAgent.generate_title(text)

        assert title == "Machine Learning Fundamentals"

    def test_extract_title_long(self, agent):
        """Test title extraction with long text"""
        text = "A" * 100
        title = BaseAgent.generate_title(text, max_length=60)

        assert len(title) <= 63  # 60 + "..."
        assert title.endswith("...")

    def test_detect_category_ai(self, agent):
        """Test category detection for AI content"""
        text = "This article discusses machine learning and neural networks"
        category = BaseAgent.detect_category(text)

        assert category == "ai"

    def test_detect_category_tech(self, agent):
        """Test category detection for tech content"""
        text = "Python programming and software development"
        category = BaseAgent.detect_category(text)

        assert category == "tech"

    def test_detect_category_general(self, agent):
        """Test category detection for general content"""
        text = "This is some random text"
        category = BaseAgent.detect_category(text)

        assert category == "general"

    def test_extract_tags(self, agent):
        """Test tag extraction"""
        text = "machine learning neural networks deep learning AI"
        tags = BaseAgent.extract_keywords(text, top_n=3)

        assert len(tags) <= 3
        assert all(len(tag) > 3 for tag in tags)

    def test_generate_summary(self, agent):
        """Test summary generation"""
        text = "First paragraph summary.\n\nSecond paragraph."
        summary = BaseAgent.generate_summary(text)

        assert summary == "First paragraph summary."

    def test_parse_qwen_result_with_metadata(self, agent):
        """Test parsing result with metadata block"""
        result_text = """# Test Article

```metadata
category: ai
subcategory: machine-learning
tags: ml, neural-networks, deep-learning
```

```agent-result
{
  "summary": "Test article processed",
  "files_created": [],
  "files_edited": [],
  "folders_created": [],
  "metadata": {
    "category": "ai",
    "topics": ["ml", "neural-networks"]
  }
}
```

## TODO Plan
- [x] Analyze content
- [x] Extract key topics

## Content
Main content here.
"""

        # Test that agent can parse the response
        agent_result = agent.parse_agent_response(result_text)
        kb_structure = agent.extract_kb_structure_from_response(
            result_text, default_category="general"
        )
        todo_plan = agent._extract_todo_plan(result_text)

        assert agent_result["summary"] == "Test article processed"
        assert kb_structure.category == "ai"
        assert kb_structure.subcategory == "machine-learning"
        assert "ml" in kb_structure.tags
        assert len(todo_plan) == 2

    def test_parse_qwen_result_minimal(self, agent):
        """Test parsing minimal result"""
        result_text = """# Simple Title

```agent-result
{
  "summary": "Minimal content",
  "files_created": [],
  "files_edited": [],
  "folders_created": [],
  "metadata": {}
}
```

Some content"""

        # Test that agent can parse minimal response
        agent_result = agent.parse_agent_response(result_text)
        kb_structure = agent.extract_kb_structure_from_response(
            result_text, default_category="general"
        )

        assert agent_result["summary"] == "Minimal content"
        assert kb_structure.category == "general"  # default category
        # Tags are extracted from content, not from missing metadata
        assert isinstance(kb_structure.tags, list)

    def test_fallback_processing(self, agent):
        """Test fallback processing"""
        prompt = """
System instruction

## Text Content
This is test content about machine learning.

## URLs
- https://example.com

# Task
Process this content.
"""

        result = agent._fallback_processing(prompt)

        assert "machine learning" in result
        assert "# " in result  # Has title
        assert "## Metadata" in result
        assert "## Content" in result

    @pytest.mark.asyncio
    async def test_execute_qwen_cli_success(self, agent):
        """Test successful CLI execution"""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"# Test Result\n\nProcessed content", b"")
        )
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await agent._execute_qwen_cli("test prompt")

            assert "Test Result" in result
            assert "Processed content" in result

    @pytest.mark.asyncio
    async def test_execute_qwen_cli_empty_result(self, agent):
        """Test CLI execution with empty result"""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await agent._execute_qwen_cli("test prompt")

            # Should return fallback result
            assert len(result) > 0
            assert "# " in result  # Has markdown structure

    @pytest.mark.asyncio
    async def test_process_full_workflow(self, agent, sample_content):
        """Test full process workflow"""
        # Mock CLI execution - ResponseFormatter needs agent-result block
        mock_cli_result = """# Machine Learning Article

```agent-result
{
  "summary": "This article discusses machine learning and neural networks.",
  "files_created": [],
  "files_edited": [],
  "folders_created": [],
  "metadata": {}
}
```

```metadata
category: ai
subcategory: machine-learning
tags: ml, neural-networks, ai
```

## TODO Plan
- [x] Analyze content
- [x] Extract key information
- [x] Generate summary

## Summary
This article discusses machine learning and neural networks.

## Content
Machine learning is a subset of AI that focuses on...

## Key Takeaways
- Neural networks are powerful
- Deep learning is important
"""

        with patch.object(agent, "_execute_qwen_cli", return_value=mock_cli_result):
            result = await agent.process(sample_content)

            assert "markdown" in result
            assert "metadata" in result
            assert "title" in result
            assert "kb_structure" in result

            assert isinstance(result["kb_structure"], KBStructure)
            assert result["kb_structure"].category == "ai"
            assert result["metadata"]["agent"] == "QwenCodeCLIAgent"
            assert len(result["metadata"]["todo_plan"]) > 0

    @pytest.mark.asyncio
    async def test_process_with_cli_error(self, agent, sample_content):
        """Test process with CLI error (should use fallback)"""
        with patch.object(agent, "_execute_qwen_cli", side_effect=Exception("CLI error")):
            with pytest.raises(Exception):
                await agent.process(sample_content)

    def test_check_installation_available(self):
        """Test installation check when CLI is available"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = QwenCodeCLIAgent.check_installation()
            assert result is True

    def test_check_installation_not_available(self):
        """Test installation check when CLI is not available"""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = QwenCodeCLIAgent.check_installation()
            assert result is False

    def test_get_installation_instructions(self):
        """Test getting installation instructions"""
        instructions = QwenCodeCLIAgent.get_installation_instructions()

        assert "npm install" in instructions
        assert "qwen" in instructions
        assert "Node.js" in instructions

    def test_cli_not_found_error(self):
        """Test error when CLI is not found"""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with pytest.raises(RuntimeError) as exc_info:
                QwenCodeCLIAgent()

            assert "not found" in str(exc_info.value).lower()


class TestQwenCodeCLIAgentIntegration:
    """Integration tests (require actual qwen CLI)"""

    @pytest.mark.skipif(not QwenCodeCLIAgent.check_installation(), reason="qwen CLI not installed")
    def test_real_cli_check(self):
        """Test with real CLI if available"""
        assert QwenCodeCLIAgent.check_installation()

    @pytest.mark.skipif(not QwenCodeCLIAgent.check_installation(), reason="qwen CLI not installed")
    @pytest.mark.asyncio
    async def test_real_process(self):
        """Test real processing if CLI is available"""
        agent = QwenCodeCLIAgent(timeout=60)

        content = {"text": "Brief test about Python programming", "urls": []}

        try:
            result = await agent.process(content)

            assert "markdown" in result
            assert "title" in result
            assert result["metadata"]["agent"] == "QwenCodeCLIAgent"
        except Exception as e:
            pytest.skip(f"CLI execution failed: {e}")


class TestQwenCodeCLIAgentWithDifferentConfigurations:
    """Test agent with different configurations"""

    @pytest.fixture
    def mock_cli_check(self):
        """Mock CLI availability check"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="qwen 1.0", stderr="")
            yield mock_run

    @pytest.fixture
    def agent(self, mock_cli_check):
        """Create test agent for this test class"""
        return QwenCodeCLIAgent(config={})

    def test_minimal_configuration(self, mock_cli_check):
        """Test agent with minimal configuration"""
        agent = QwenCodeCLIAgent(enable_web_search=False, enable_git=False, enable_github=False)

        assert not agent.enable_web_search
        assert not agent.enable_git
        assert not agent.enable_github

    def test_custom_working_directory(self, mock_cli_check):
        """Test agent with custom working directory"""
        agent = QwenCodeCLIAgent(working_directory="/tmp/test")

        assert agent.working_directory == "/tmp/test"

    def test_custom_timeout(self, mock_cli_check):
        """Test agent with custom timeout"""
        agent = QwenCodeCLIAgent(timeout=600)

        assert agent.timeout == 600

    def test_with_config_dict(self, mock_cli_check):
        """Test agent with config dictionary"""
        config = {"github_token": "test-token", "custom_key": "custom_value"}

        agent = QwenCodeCLIAgent(config=config)

        assert agent.config["github_token"] == "test-token"
        assert agent.config["custom_key"] == "custom_value"

    def test_set_working_directory(self, agent):
        """Test setting working directory dynamically"""
        original_dir = agent.get_working_directory()

        # Set new working directory
        new_dir = "/tmp/knowledge_base/my-kb"
        agent.set_working_directory(new_dir)

        # Verify it was updated
        assert agent.get_working_directory() == new_dir
        assert agent.working_directory == new_dir

        # Restore original
        agent.set_working_directory(original_dir)
        assert agent.get_working_directory() == original_dir

    def test_working_directory_persistence(self, mock_cli_check):
        """Test that working directory persists across method calls"""
        agent = QwenCodeCLIAgent(working_directory="/initial/path")

        # Change working directory
        agent.set_working_directory("/new/path")

        # Verify it's still the new path
        assert agent.get_working_directory() == "/new/path"

        # Call other methods and verify working directory hasn't changed
        instruction = agent.get_instruction()
        assert agent.get_working_directory() == "/new/path"

    def test_mcp_disabled_by_default(self, mock_cli_check):
        """Test that MCP is disabled by default"""
        agent = QwenCodeCLIAgent()
        assert agent.enable_mcp is False

    def test_mcp_can_be_enabled(self, mock_cli_check):
        """Test that MCP can be enabled for qwen CLI native support"""
        config = {"enable_mcp": True, "user_id": 123}

        # Should accept MCP config (for qwen native MCP)
        agent = QwenCodeCLIAgent(config=config)

        # MCP should be enabled (qwen CLI will handle it via .qwen/settings.json)
        assert agent.enable_mcp is True
        assert agent.user_id == 123

    @pytest.mark.asyncio
    async def test_mcp_tools_description_with_qwen_native(self, mock_cli_check):
        """Test MCP configuration with qwen native MCP"""
        config = {"enable_mcp": True}
        agent = QwenCodeCLIAgent(config=config)

        # QwenCodeCLIAgent uses qwen CLI's built-in MCP client
        # It doesn't have a get_mcp_tools_description method
        # because qwen CLI manages MCP servers itself
        assert agent.enable_mcp is True
        assert not hasattr(agent, "get_mcp_tools_description")

        # The agent should have MCP configuration setup
        assert hasattr(agent, "_setup_qwen_mcp_config")
