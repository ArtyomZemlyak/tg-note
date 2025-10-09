"""
Tests for Autonomous Agent (formerly Qwen Code Agent)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents import QwenCodeAgent  # Backward compatibility alias
from src.agents import (
    ActionType,
    AgentContext,
    AgentDecision,
    AutonomousAgent,
    TodoPlan,
    ToolExecution,
)
from src.agents.base_agent import BaseAgent, KBStructure


class TestTodoPlan:
    """Test TodoPlan class"""

    def test_add_task(self):
        """Test adding tasks to plan"""
        plan = TodoPlan()
        plan.add_task("Task 1", priority=1)
        plan.add_task("Task 2", priority=2)

        assert len(plan.tasks) == 2
        assert plan.tasks[0]["task"] == "Task 1"
        assert plan.tasks[0]["priority"] == 1
        assert plan.tasks[0]["status"] == "pending"

    def test_update_task_status(self):
        """Test updating task status"""
        plan = TodoPlan()
        plan.add_task("Task 1")
        plan.update_task_status(0, "completed")

        assert plan.tasks[0]["status"] == "completed"

    def test_get_pending_tasks(self):
        """Test getting pending tasks"""
        plan = TodoPlan()
        plan.add_task("Task 1", status="pending")
        plan.add_task("Task 2", status="completed")
        plan.add_task("Task 3", status="pending")

        pending = plan.get_pending_tasks()
        assert len(pending) == 2
        assert all(t["status"] == "pending" for t in pending)

    def test_to_dict(self):
        """Test converting plan to dictionary"""
        plan = TodoPlan()
        plan.add_task("Task 1")

        result = plan.to_dict()
        assert "tasks" in result
        assert len(result["tasks"]) == 1


class TestToolExecution:
    """Test ToolExecution class"""

    def test_success_execution(self):
        """Test successful tool execution"""
        execution = ToolExecution(
            tool_name="analyze_content",
            params={"text": "test"},
            result={"success": True},
            success=True,
        )

        assert execution.success
        assert execution.tool_name == "analyze_content"
        assert execution.error is None

    def test_error_execution(self):
        """Test error tool execution"""
        execution = ToolExecution(
            tool_name="web_search",
            params={"query": "test"},
            result=None,
            success=False,
            error="Connection failed",
        )

        assert not execution.success
        assert execution.result is None
        assert execution.error == "Connection failed"

    def test_to_dict(self):
        """Test converting execution to dictionary"""
        execution = ToolExecution(tool_name="test", params={}, result="data", success=True)

        data = execution.to_dict()
        assert data["success"]
        assert data["tool_name"] == "test"
        assert data["result"] == "data"


class TestAutonomousAgent:
    """Test AutonomousAgent class"""

    @pytest.fixture
    def agent(self):
        """Create test agent without LLM connector (rule-based)"""
        return AutonomousAgent(
            llm_connector=None,  # Use rule-based decision making
            config={},
            enable_web_search=True,
            enable_git=True,
            enable_github=True,
            enable_shell=False,
        )

    @pytest.fixture
    def sample_content(self):
        """Sample content for testing"""
        return {
            "text": "This is a test about machine learning and AI. "
            "Neural networks are powerful tools for deep learning.",
            "urls": ["https://example.com/article"],
            "metadata": {},
        }

    def test_initialization(self, agent):
        """Test agent initialization"""
        assert agent is not None
        assert agent.enable_web_search
        assert agent.enable_git
        assert agent.enable_github
        assert not agent.enable_shell
        assert "web_search" in agent.tools
        assert "git_command" in agent.tools
        assert "github_api" in agent.tools
        assert "shell_command" not in agent.tools
        assert "plan_todo" in agent.tools
        assert "analyze_content" in agent.tools

    def test_backward_compatibility_alias(self):
        """Test that QwenCodeAgent is alias for AutonomousAgent"""
        assert QwenCodeAgent == AutonomousAgent

    def test_custom_instruction(self):
        """Test custom instruction setting"""
        custom_instruction = "Custom instruction for testing"
        agent = AutonomousAgent(instruction=custom_instruction)

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

    @pytest.mark.asyncio
    async def test_create_todo_plan(self, agent, sample_content):
        """Test TODO plan creation"""
        plan = await agent._create_todo_plan(sample_content)

        assert plan is not None
        assert len(plan.tasks) > 0
        assert all(task["status"] == "pending" for task in plan.tasks)

    def test_extract_keywords(self):
        """Test keyword extraction"""
        text = "machine learning neural networks deep learning AI artificial intelligence"
        keywords = BaseAgent.extract_keywords(text, top_n=3)

        assert len(keywords) <= 3
        assert "machine" in keywords or "learning" in keywords

    def test_detect_category_ai(self):
        """Test category detection for AI content"""
        text = "This article discusses machine learning and neural networks in AI"
        category = BaseAgent.detect_category(text)

        assert category == "ai"

    def test_detect_category_tech(self):
        """Test category detection for tech content"""
        text = "Python programming and software development with APIs"
        category = BaseAgent.detect_category(text)

        assert category == "tech"

    def test_detect_category_general(self):
        """Test category detection for general content"""
        text = "This is some random text without specific keywords"
        category = BaseAgent.detect_category(text)

        assert category == "general"

    def test_generate_title(self):
        """Test title generation"""
        text = "Machine Learning Fundamentals\n\nThis is the content..."
        title = BaseAgent.generate_title(text)

        assert title == "Machine Learning Fundamentals"

    def test_generate_title_long(self):
        """Test title generation with long text"""
        text = "A" * 100
        title = BaseAgent.generate_title(text, max_length=50)

        assert len(title) <= 53  # 50 + "..."
        assert title.endswith("...")

    def test_generate_summary(self):
        """Test summary generation"""
        text = "First paragraph with summary.\n\nSecond paragraph."
        summary = BaseAgent.generate_summary(text)

        assert summary == "First paragraph with summary."

    @pytest.mark.asyncio
    async def test_analyze_content(self, agent, sample_content):
        """Test content analysis"""
        result = await agent._analyze_content(sample_content)

        assert "text_length" in result
        assert "word_count" in result
        assert "url_count" in result
        assert "keywords" in result
        assert result["url_count"] == 1

    @pytest.mark.asyncio
    async def test_extract_metadata(self, agent, sample_content):
        """Test metadata extraction"""
        result = await agent._extract_metadata(sample_content)

        assert "category" in result
        assert "tags" in result
        assert "title" in result
        assert result["category"] in [
            "ai",
            "tech",
            "general",
            "biology",
            "physics",
            "business",
            "science",
        ]

    @pytest.mark.asyncio
    async def test_structure_content(self, agent, sample_content):
        """Test content structuring"""
        execution_results = [
            {"keywords": ["ai", "machine", "learning"]},
            {"category": "ai", "tags": ["ai", "ml"], "title": "Test Title"},
        ]

        structured = await agent._structure_content(sample_content, execution_results)

        assert "title" in structured
        assert "category" in structured
        assert "tags" in structured
        assert "content" in structured
        assert structured["category"] == "ai"

    @pytest.mark.asyncio
    async def test_generate_markdown(self, agent):
        """Test markdown generation"""
        structured_content = {
            "title": "Test Article",
            "category": "ai",
            "tags": ["machine-learning", "neural-networks"],
            "content": "This is the main content.",
            "urls": ["https://example.com"],
            "summary": "This is a summary.",
            "analysis": {"keywords": ["ai", "ml"]},
        }

        markdown = await agent._generate_markdown(structured_content)

        assert "# Test Article" in markdown
        assert "## Metadata" in markdown
        assert "## Summary" in markdown
        assert "## Content" in markdown
        assert "## Links" in markdown
        assert "## Keywords" in markdown
        assert "machine-learning" in markdown

    @pytest.mark.asyncio
    async def test_determine_kb_structure(self, agent):
        """Test KB structure determination"""
        structured_content = {
            "category": "ai",
            "tags": ["ml", "neural-networks"],
            "content": "machine learning neural network deep learning",
        }

        kb_structure = await agent._determine_kb_structure(structured_content)

        assert isinstance(kb_structure, KBStructure)
        assert kb_structure.category == "ai"
        assert kb_structure.subcategory == "machine-learning"
        assert "ml" in kb_structure.tags

    @pytest.mark.asyncio
    async def test_process_full(self, agent, sample_content):
        """Test full process workflow"""
        result = await agent.process(sample_content)

        assert "markdown" in result
        assert "metadata" in result
        assert "title" in result
        assert "kb_structure" in result

        assert isinstance(result["kb_structure"], KBStructure)
        assert result["metadata"]["agent"] == "AutonomousAgent"
        assert "iterations" in result["metadata"]
        assert "executions" in result["metadata"]

    @pytest.mark.asyncio
    async def test_tool_web_search(self, agent):
        """Test web search tool (checks tool execution, not actual HTTP requests)"""
        # Test with non-URL query (returns placeholder)
        result = await agent.tool_manager.execute("web_search", {"query": "test query"})
        
        assert result["success"]
        assert "query" in result
        assert result["query"] == "test query"

    @pytest.mark.asyncio
    async def test_tool_git_command_safe(self, agent):
        """Test git command tool with safe command"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="On branch main", stderr="")

            result = await agent.tool_manager.execute("git_command", {"command": "git status"})

            assert result["success"]
            assert "stdout" in result

    @pytest.mark.asyncio
    async def test_tool_git_command_unsafe(self, agent):
        """Test git command tool with unsafe command"""
        result = await agent.tool_manager.execute("git_command", {"command": "git push"})

        assert not result["success"]
        assert "not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_tool_github_api(self, agent):
        """Test GitHub API tool (checks tool is registered and callable)"""
        # Test that the tool exists and can be called
        # Without mocking HTTP, it will make a real API call and likely get 404
        result = await agent.tool_manager.execute("github_api", {"endpoint": "/repos/user/repo"})
        
        # Tool should execute and return a result
        assert "success" in result
        # Should have either error message or data from API
        if not result["success"]:
            assert "error" in result or "data" in result

    @pytest.mark.asyncio
    async def test_tool_shell_command_disabled(self, agent):
        """Test shell command tool when disabled"""
        result = await agent.tool_manager.execute("shell_command", {"command": "echo test"})

        assert not result["success"]
        # When tool is disabled, it's not registered, so we get "Tool not found"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_tool_shell_command_enabled(self):
        """Test shell command tool when enabled"""
        agent = AutonomousAgent(enable_shell=True)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="test output", stderr="")

            result = await agent.tool_manager.execute("shell_command", {"command": "echo test"})

            assert result["success"]

    @pytest.mark.asyncio
    async def test_tool_shell_command_dangerous(self):
        """Test shell command tool blocks dangerous commands"""
        agent = AutonomousAgent(enable_shell=True)

        result = await agent.tool_manager.execute("shell_command", {"command": "rm -rf /"})

        assert not result["success"]
        assert "dangerous" in result["error"]

    @pytest.mark.asyncio
    async def test_tool_plan_todo(self, agent):
        """Test plan_todo tool"""
        tasks = ["Task 1", "Task 2", "Task 3"]
        result = await agent.tool_manager.execute("plan_todo", {"tasks": tasks})

        assert result["success"]
        assert agent.current_plan is not None
        assert len(agent.current_plan.tasks) == 3

    @pytest.mark.asyncio
    async def test_tool_analyze_content(self, agent):
        """Test analyze_content tool"""
        text = "This is test content about AI and machine learning"
        result = await agent.tool_manager.execute("analyze_content", {"text": text})

        assert "text_length" in result
        assert "word_count" in result
        assert "keywords" in result
        assert "category" in result


class TestAgentWithDifferentConfigurations:
    """Test agent with different configurations"""

    def test_minimal_tools(self):
        """Test agent with minimal tools"""
        agent = AutonomousAgent(
            enable_web_search=False,
            enable_git=False,
            enable_github=False,
            enable_shell=False,
            enable_file_management=False,
            enable_folder_management=False,
        )

        # Should still have plan_todo and analyze_content
        assert "plan_todo" in agent.tools
        assert "analyze_content" in agent.tools
        assert "web_search" not in agent.tools

    def test_all_tools_enabled(self):
        """Test agent with all tools enabled"""
        agent = AutonomousAgent(
            enable_web_search=True,
            enable_git=True,
            enable_github=True,
            enable_shell=True,
            enable_file_management=True,
            enable_folder_management=True,
        )

        assert "web_search" in agent.tools
        assert "git_command" in agent.tools
        assert "github_api" in agent.tools
        assert "shell_command" in agent.tools
        assert "file_create" in agent.tools
        assert "folder_create" in agent.tools

    def test_with_llm_connector(self):
        """Test agent with mock LLM connector"""
        from unittest.mock import Mock

        mock_connector = Mock()
        mock_connector.get_model_name.return_value = "test-model"

        agent = AutonomousAgent(llm_connector=mock_connector)

        assert agent.llm_connector == mock_connector
