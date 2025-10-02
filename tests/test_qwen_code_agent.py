"""
Tests for Qwen Code Agent
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.qwen_code_agent import QwenCodeAgent, TodoPlan, ToolResult
from src.agents.base_agent import KBStructure


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


class TestToolResult:
    """Test ToolResult class"""
    
    def test_success_result(self):
        """Test successful tool result"""
        result = ToolResult(success=True, output="Success")
        
        assert result.success
        assert result.output == "Success"
        assert result.error is None
    
    def test_error_result(self):
        """Test error tool result"""
        result = ToolResult(success=False, output=None, error="Failed")
        
        assert not result.success
        assert result.output is None
        assert result.error == "Failed"
    
    def test_to_dict(self):
        """Test converting result to dictionary"""
        result = ToolResult(success=True, output="Data")
        
        data = result.to_dict()
        assert data["success"]
        assert data["output"] == "Data"
        assert data["error"] is None


class TestQwenCodeAgent:
    """Test QwenCodeAgent class"""
    
    @pytest.fixture
    def agent(self):
        """Create test agent"""
        return QwenCodeAgent(
            config={},
            enable_web_search=True,
            enable_git=True,
            enable_github=True,
            enable_shell=False
        )
    
    @pytest.fixture
    def sample_content(self):
        """Sample content for testing"""
        return {
            "text": "This is a test about machine learning and AI. "
                   "Neural networks are powerful tools for deep learning.",
            "urls": ["https://example.com/article"],
            "metadata": {}
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
    
    def test_custom_instruction(self):
        """Test custom instruction setting"""
        custom_instruction = "Custom instruction for testing"
        agent = QwenCodeAgent(instruction=custom_instruction)
        
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
    
    def test_extract_keywords(self, agent):
        """Test keyword extraction"""
        text = "machine learning neural networks deep learning AI artificial intelligence"
        keywords = agent._extract_keywords(text, top_n=3)
        
        assert len(keywords) <= 3
        assert "machine" in keywords or "learning" in keywords
    
    def test_detect_category_ai(self, agent):
        """Test category detection for AI content"""
        text = "This article discusses machine learning and neural networks in AI"
        category = agent._detect_category(text)
        
        assert category == "ai"
    
    def test_detect_category_tech(self, agent):
        """Test category detection for tech content"""
        text = "Python programming and software development with APIs"
        category = agent._detect_category(text)
        
        assert category == "tech"
    
    def test_detect_category_general(self, agent):
        """Test category detection for general content"""
        text = "This is some random text without specific keywords"
        category = agent._detect_category(text)
        
        assert category == "general"
    
    def test_generate_title(self, agent):
        """Test title generation"""
        text = "Machine Learning Fundamentals\n\nThis is the content..."
        title = agent._generate_title(text)
        
        assert title == "Machine Learning Fundamentals"
    
    def test_generate_title_long(self, agent):
        """Test title generation with long text"""
        text = "A" * 100
        title = agent._generate_title(text, max_length=50)
        
        assert len(title) <= 53  # 50 + "..."
        assert title.endswith("...")
    
    def test_generate_summary(self, agent):
        """Test summary generation"""
        text = "First paragraph with summary.\n\nSecond paragraph."
        summary = agent._generate_summary(text)
        
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
        assert result["category"] in ["ai", "tech", "general", "biology", "physics", "business", "science"]
    
    @pytest.mark.asyncio
    async def test_structure_content(self, agent, sample_content):
        """Test content structuring"""
        execution_results = [
            {"keywords": ["ai", "machine", "learning"]},
            {"category": "ai", "tags": ["ai", "ml"], "title": "Test Title"}
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
            "analysis": {"keywords": ["ai", "ml"]}
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
            "content": "machine learning neural network deep learning"
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
        assert result["metadata"]["agent"] == "QwenCodeAgent"
        assert "plan" in result["metadata"]
        assert "execution_log" in result["metadata"]
    
    @pytest.mark.asyncio
    async def test_tool_web_search(self, agent):
        """Test web search tool"""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="<title>Test Page</title>")
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            result = await agent._tool_web_search({"query": "https://example.com"})
            
            assert result.success
            assert "url" in result.output
    
    @pytest.mark.asyncio
    async def test_tool_git_command_safe(self, agent):
        """Test git command tool with safe command"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="On branch main",
                stderr=""
            )
            
            result = await agent._tool_git_command({"command": "git status"})
            
            assert result.success
            assert "stdout" in result.output
    
    @pytest.mark.asyncio
    async def test_tool_git_command_unsafe(self, agent):
        """Test git command tool with unsafe command"""
        result = await agent._tool_git_command({"command": "git push"})
        
        assert not result.success
        assert "not allowed" in result.error
    
    @pytest.mark.asyncio
    async def test_tool_github_api(self, agent):
        """Test GitHub API tool"""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"name": "test-repo"})
            
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = mock_response
            
            result = await agent._tool_github_api({"endpoint": "/repos/user/repo"})
            
            assert result.success
            assert result.output["status"] == 200
    
    @pytest.mark.asyncio
    async def test_tool_shell_command_disabled(self, agent):
        """Test shell command tool when disabled"""
        result = await agent._tool_shell_command({"command": "echo test"})
        
        assert not result.success
        assert "disabled" in result.error
    
    @pytest.mark.asyncio
    async def test_tool_shell_command_enabled(self):
        """Test shell command tool when enabled"""
        agent = QwenCodeAgent(enable_shell=True)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test output",
                stderr=""
            )
            
            result = await agent._tool_shell_command({"command": "echo test"})
            
            assert result.success
    
    @pytest.mark.asyncio
    async def test_tool_shell_command_dangerous(self):
        """Test shell command tool blocks dangerous commands"""
        agent = QwenCodeAgent(enable_shell=True)
        
        result = await agent._tool_shell_command({"command": "rm -rf /"})
        
        assert not result.success
        assert "dangerous" in result.error


class TestAgentWithDifferentConfigurations:
    """Test agent with different configurations"""
    
    def test_minimal_tools(self):
        """Test agent with minimal tools"""
        agent = QwenCodeAgent(
            enable_web_search=False,
            enable_git=False,
            enable_github=False,
            enable_shell=False
        )
        
        assert len(agent.tools) == 0
    
    def test_all_tools_enabled(self):
        """Test agent with all tools enabled"""
        agent = QwenCodeAgent(
            enable_web_search=True,
            enable_git=True,
            enable_github=True,
            enable_shell=True
        )
        
        assert len(agent.tools) == 4
        assert "web_search" in agent.tools
        assert "git_command" in agent.tools
        assert "github_api" in agent.tools
        assert "shell_command" in agent.tools
    
    def test_custom_model(self):
        """Test agent with custom model"""
        agent = QwenCodeAgent(model="qwen-plus")
        
        assert agent.model == "qwen-plus"
    
    def test_with_api_key(self):
        """Test agent with API key"""
        agent = QwenCodeAgent(api_key="test-key-123")
        
        assert agent.api_key == "test-key-123"
