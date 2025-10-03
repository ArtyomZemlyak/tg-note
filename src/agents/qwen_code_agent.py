"""
Qwen Code Agent
Autonomous agent using Qwen-Agent for processing content with tools
"""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp
import requests
from loguru import logger

from .base_agent import KBStructure
from .autonomous_agent import (
    ActionType,
    AgentContext,
    AgentDecision,
    AutonomousAgent
)
from config.agent_prompts import (
    QWEN_CODE_AGENT_INSTRUCTION,
    CATEGORY_KEYWORDS,
    DEFAULT_CATEGORY,
    STOP_WORDS,
    SAFE_GIT_COMMANDS,
    DANGEROUS_SHELL_PATTERNS,
    MAX_TITLE_LENGTH,
    MAX_SUMMARY_LENGTH,
    MAX_KEYWORD_COUNT,
    MIN_KEYWORD_LENGTH,
)


class TodoPlan:
    """TODO plan for agent execution"""
    
    def __init__(self):
        self.tasks: List[Dict[str, Any]] = []
    
    def add_task(self, task: str, status: str = "pending", priority: int = 0) -> None:
        """Add a task to the plan"""
        self.tasks.append({
            "task": task,
            "status": status,
            "priority": priority,
            "created_at": datetime.now().isoformat()
        })
    
    def update_task_status(self, index: int, status: str) -> None:
        """Update task status"""
        if 0 <= index < len(self.tasks):
            self.tasks[index]["status"] = status
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending tasks"""
        return [t for t in self.tasks if t["status"] == "pending"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {"tasks": self.tasks}


class ToolResult:
    """Result from tool execution"""
    
    def __init__(self, success: bool, output: Any, error: Optional[str] = None):
        self.success = success
        self.output = output
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error
        }


class QwenCodeAgent(AutonomousAgent):
    """
    Qwen Code Agent with autonomous processing capabilities
    
    Features:
    - Configurable instruction system
    - Autonomous mode (no user interaction)
    - TODO plan generation and execution via autonomous agent loop
    - Tool using: web search, git, github, cmd commands, file/folder management
    """
    
    DEFAULT_INSTRUCTION = QWEN_CODE_AGENT_INSTRUCTION
    
    def __init__(
        self,
        config: Optional[Dict] = None,
        instruction: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "qwen-max",
        enable_web_search: bool = True,
        enable_git: bool = True,
        enable_github: bool = True,
        enable_shell: bool = False,  # Disabled by default for security
        enable_file_management: bool = True,
        enable_folder_management: bool = True,
        kb_root_path: Optional[Path] = None,
        max_iterations: int = 10
    ):
        """
        Initialize Qwen Code Agent
        
        Args:
            config: Configuration dictionary
            instruction: Custom instruction for the agent
            api_key: API key for Qwen service
            model: Model to use (default: qwen-max)
            enable_web_search: Enable web search tool
            enable_git: Enable git command tool
            enable_github: Enable GitHub API tool
            enable_shell: Enable shell command tool (security risk)
            enable_file_management: Enable file management tools
            enable_folder_management: Enable folder management tools
            kb_root_path: Root path for knowledge base (for safe file/folder operations)
            max_iterations: Maximum iterations in autonomous agent loop
        """
        # Knowledge base root path for safe file operations
        kb_root = kb_root_path or Path("./knowledge_base")
        kb_root = kb_root.resolve()  # Get absolute path
        
        # Initialize parent AutonomousAgent with kb_root_path
        super().__init__(
            config, 
            instruction or self.DEFAULT_INSTRUCTION, 
            max_iterations,
            kb_root_path=kb_root
        )
        
        self.api_key = api_key
        self.model = model
        
        # Tool enablement flags
        self.enable_web_search = enable_web_search
        self.enable_git = enable_git
        self.enable_github = enable_github
        self.enable_shell = enable_shell
        self.enable_file_management = enable_file_management
        self.enable_folder_management = enable_folder_management
        
        # Register tools with autonomous agent
        self._register_all_tools()
        
        # Agent state
        self.current_plan: Optional[TodoPlan] = None
        self.execution_log: List[Dict[str, Any]] = []
        
        logger.info(f"QwenCodeAgent initialized with model: {model}")
        logger.info(f"KB root path: {self.kb_root_path}")
        logger.info(f"Enabled tools: {list(self.tools.keys())}")
    
    def _register_all_tools(self) -> None:
        """Register all available tools with autonomous agent"""
        if self.enable_web_search:
            self.register_tool("web_search", self._tool_web_search)
        
        if self.enable_git:
            self.register_tool("git_command", self._tool_git_command)
        
        if self.enable_github:
            self.register_tool("github_api", self._tool_github_api)
        
        if self.enable_shell:
            self.register_tool("shell_command", self._tool_shell_command)
        
        if self.enable_file_management:
            self.register_tool("file_create", self._tool_file_create)
            self.register_tool("file_edit", self._tool_file_edit)
            self.register_tool("file_delete", self._tool_file_delete)
            self.register_tool("file_move", self._tool_file_move)
        
        if self.enable_folder_management:
            self.register_tool("folder_create", self._tool_folder_create)
            self.register_tool("folder_delete", self._tool_folder_delete)
            self.register_tool("folder_move", self._tool_folder_move)
        
        # Register analyze_content tool
        self.register_tool("analyze_content", self._tool_analyze_content)
        
        # Register plan_todo tool
        self.register_tool("plan_todo", self._tool_plan_todo)
    
    async def _make_decision(self, context: AgentContext) -> AgentDecision:
        """
        Make decision using simple rule-based logic or LLM
        
        For now, we use a simplified approach:
        1. First iteration: create plan_todo
        2. Execute tasks from plan
        3. When done: return END with final markdown
        
        Args:
            context: Current agent context
        
        Returns:
            AgentDecision with next action
        """
        logger.debug("[QwenCodeAgent] Making decision")
        
        # Check if we have a plan yet
        if not self.current_plan:
            # First step: create TODO plan
            logger.info("[QwenCodeAgent] Creating TODO plan")
            
            # Extract content from task
            text = self._extract_text_from_task(context.task)
            tasks = self._generate_task_list(text)
            
            return AgentDecision(
                action=ActionType.TOOL_CALL,
                reasoning="Creating TODO plan for content processing",
                tool_name="plan_todo",
                tool_params={"tasks": tasks}
            )
        
        # Check if all tasks are completed
        pending_tasks = self.current_plan.get_pending_tasks()
        
        if pending_tasks:
            # Execute next pending task
            task = pending_tasks[0]
            task_index = self.current_plan.tasks.index(task)
            
            logger.info(f"[QwenCodeAgent] Executing task: {task['task']}")
            
            # Determine which tool to use based on task description
            tool_name, tool_params = self._task_to_tool(task, context)
            
            # Mark task as in progress
            self.current_plan.update_task_status(task_index, "in_progress")
            
            return AgentDecision(
                action=ActionType.TOOL_CALL,
                reasoning=f"Executing task: {task['task']}",
                tool_name=tool_name,
                tool_params=tool_params
            )
        
        # All tasks completed - generate final markdown
        logger.info("[QwenCodeAgent] All tasks completed, generating final result")
        
        # Generate markdown from execution results
        markdown = await self._generate_final_markdown(context)
        
        return AgentDecision(
            action=ActionType.END,
            reasoning="All tasks completed successfully",
            final_result=markdown
        )
    
    def _extract_text_from_task(self, task: str) -> str:
        """Extract content text from task description"""
        # Task format: "Обработай следующий контент...\nТЕКСТ:\n{text}\n..."
        if "ТЕКСТ:" in task:
            parts = task.split("ТЕКСТ:")
            if len(parts) > 1:
                text_part = parts[1].split("URL:")[0] if "URL:" in parts[1] else parts[1]
                return text_part.strip()
        return task
    
    def _generate_task_list(self, text: str) -> List[str]:
        """Generate a list of tasks for processing content"""
        tasks = [
            "Analyze content and extract key topics",
            "Extract metadata (topics, tags, category)",
            "Structure content for knowledge base",
            "Generate markdown formatted content"
        ]
        
        # Add web search task if URLs present
        if "URL:" in text or "http" in text:
            tasks.insert(1, "Search web for additional context")
        
        return tasks
    
    def _task_to_tool(self, task: Dict, context: AgentContext) -> tuple[str, Dict[str, Any]]:
        """Convert a task to a tool call"""
        task_desc = task["task"].lower()
        
        if "analyze content" in task_desc:
            text = self._extract_text_from_task(context.task)
            return "analyze_content", {"text": text}
        
        elif "search web" in task_desc:
            text = self._extract_text_from_task(context.task)
            # Extract URLs from text
            urls = []
            for line in text.split("\n"):
                if line.startswith("http"):
                    urls.append(line.strip())
            
            if urls:
                return "web_search", {"query": urls[0]}
            return "analyze_content", {"text": text}
        
        elif "extract metadata" in task_desc:
            text = self._extract_text_from_task(context.task)
            return "analyze_content", {"text": text}
        
        else:
            # Default: analyze content
            text = self._extract_text_from_task(context.task)
            return "analyze_content", {"text": text}
    
    async def _generate_final_markdown(self, context: AgentContext) -> str:
        """Generate final markdown from execution results"""
        # Collect all analysis results
        analysis_results = []
        web_results = []
        
        for execution in context.executions:
            if execution.tool_name == "analyze_content" and execution.success:
                analysis_results.append(execution.result)
            elif execution.tool_name == "web_search" and execution.success:
                web_results.append(execution.result)
        
        # Extract text from task
        text = self._extract_text_from_task(context.task)
        
        # Generate metadata
        title = self._generate_title(text)
        category = self._detect_category(text)
        tags = self._extract_keywords(text)[:5]
        summary = self._generate_summary(text)
        
        # Build markdown
        lines = []
        lines.append(f"# {title}")
        lines.append("")
        lines.append("## Metadata")
        lines.append("")
        lines.append(f"- **Category**: {category}")
        if tags:
            lines.append(f"- **Tags**: {', '.join(tags)}")
        lines.append(f"- **Processed**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        if summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(summary)
            lines.append("")
        
        lines.append("## Content")
        lines.append("")
        lines.append(text)
        lines.append("")
        
        # Add analysis if available
        if analysis_results:
            lines.append("## Analysis")
            lines.append("")
            for result in analysis_results:
                if isinstance(result, dict):
                    keywords = result.get("keywords", [])
                    if keywords:
                        lines.append(f"**Keywords**: {', '.join(keywords)}")
                        lines.append("")
        
        # Add web context if available
        if web_results:
            lines.append("## Additional Context")
            lines.append("")
            for i, result in enumerate(web_results, 1):
                lines.append(f"### Context {i}")
                lines.append("")
                if isinstance(result, dict):
                    lines.append(str(result.get("output", result)))
                else:
                    lines.append(str(result))
                lines.append("")
        
        return "\n".join(lines)
    
    async def _tool_plan_todo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plan_todo tool call"""
        tasks = params.get("tasks", [])
        
        logger.info(f"[QwenCodeAgent] Creating plan with {len(tasks)} tasks")
        
        # Create plan
        self.current_plan = TodoPlan()
        for i, task in enumerate(tasks):
            self.current_plan.add_task(task, priority=i+1)
        
        return {
            "success": True,
            "plan": tasks,
            "message": f"Plan created with {len(tasks)} tasks"
        }
    
    async def _tool_analyze_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content tool"""
        text = params.get("text", "")
        
        analysis = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "has_code": "```" in text or "def " in text or "function " in text,
            "keywords": self._extract_keywords(text),
            "category": self._detect_category(text)
        }
        
        return analysis
    
    # Backward compatibility methods for tests
    
    async def _create_todo_plan(self, content: Dict) -> TodoPlan:
        """Create a TODO plan (backward compatibility)"""
        plan = TodoPlan()
        text = content.get("text", "")
        urls = content.get("urls", [])
        
        plan.add_task("Analyze content and extract key topics", priority=1)
        if urls and self.enable_web_search:
            plan.add_task(f"Search web for context on {len(urls)} URLs", priority=2)
        plan.add_task("Extract metadata (topics, tags, category)", priority=3)
        plan.add_task("Structure content for knowledge base", priority=4)
        plan.add_task("Generate markdown formatted content", priority=5)
        
        return plan
    
    async def _analyze_content(self, content: Dict) -> Dict[str, Any]:
        """Analyze content (backward compatibility)"""
        text = content.get("text", "")
        urls = content.get("urls", [])
        
        analysis = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "url_count": len(urls),
            "has_code": "```" in text or "def " in text or "function " in text,
            "language": "unknown",
            "keywords": self._extract_keywords(text)
        }
        
        return analysis
    
    async def _extract_metadata(self, content: Dict) -> Dict[str, Any]:
        """Extract metadata (backward compatibility)"""
        text = content.get("text", "")
        
        return {
            "category": self._detect_category(text),
            "tags": self._extract_keywords(text)[:5],
            "title": self._generate_title(text)
        }
    
    async def _structure_content(
        self,
        content: Dict,
        execution_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Structure content (backward compatibility)"""
        text = content.get("text", "")
        urls = content.get("urls", [])
        
        analysis = {}
        web_context = []
        metadata = {}
        
        for result in execution_results:
            if "keywords" in result:
                analysis = result
            elif "web_results" in result:
                web_context = result["web_results"]
            elif "category" in result:
                metadata = result
        
        return {
            "title": metadata.get("title", self._generate_title(text)),
            "category": metadata.get("category", "general"),
            "tags": metadata.get("tags", []),
            "content": text,
            "urls": urls,
            "analysis": analysis,
            "web_context": web_context,
            "summary": self._generate_summary(text)
        }
    
    async def _generate_markdown(self, structured_content: Dict) -> str:
        """Generate markdown (backward compatibility)"""
        lines = []
        
        title = structured_content.get("title", "Untitled Note")
        lines.append(f"# {title}")
        lines.append("")
        
        lines.append("## Metadata")
        lines.append("")
        lines.append(f"- **Category**: {structured_content.get('category', 'general')}")
        
        tags = structured_content.get("tags", [])
        if tags:
            lines.append(f"- **Tags**: {', '.join(tags)}")
        
        lines.append(f"- **Processed**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        summary = structured_content.get("summary", "")
        if summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(summary)
            lines.append("")
        
        lines.append("## Content")
        lines.append("")
        lines.append(structured_content.get("content", ""))
        lines.append("")
        
        urls = structured_content.get("urls", [])
        if urls:
            lines.append("## Links")
            lines.append("")
            for url in urls:
                lines.append(f"- {url}")
            lines.append("")
        
        web_context = structured_content.get("web_context", [])
        if web_context:
            lines.append("## Additional Context")
            lines.append("")
            for i, context in enumerate(web_context, 1):
                lines.append(f"### Context {i}")
                lines.append("")
                lines.append(str(context))
                lines.append("")
        
        analysis = structured_content.get("analysis", {})
        if analysis.get("keywords"):
            lines.append("## Keywords")
            lines.append("")
            lines.append(", ".join(analysis["keywords"]))
            lines.append("")
        
        return "\n".join(lines)
    
    async def _determine_kb_structure(self, structured_content: Dict) -> KBStructure:
        """Determine KB structure (backward compatibility)"""
        category = structured_content.get("category", "general")
        tags = structured_content.get("tags", [])
        
        subcategory = None
        text = structured_content.get("content", "").lower()
        
        if category == "ai":
            if any(kw in text for kw in ["machine learning", "ml", "neural network"]):
                subcategory = "machine-learning"
            elif any(kw in text for kw in ["nlp", "natural language"]):
                subcategory = "nlp"
        elif category == "tech":
            if any(kw in text for kw in ["python", "javascript", "code", "programming"]):
                subcategory = "programming"
        
        return KBStructure(
            category=category,
            subcategory=subcategory,
            tags=tags
        )
    
    
    def _extract_keywords(self, text: str, top_n: int = MAX_KEYWORD_COUNT) -> List[str]:
        """
        Extract keywords from text (simple implementation)
        
        Args:
            text: Text to extract keywords from
            top_n: Number of top keywords to return
        
        Returns:
            List of keywords
        """
        # Use stop words from config
        stop_words = STOP_WORDS
        
        # Simple word frequency
        words = text.lower().split()
        word_freq = {}
        
        for word in words:
            # Remove punctuation
            word = word.strip(".,!?;:()[]{}\"'")
            if len(word) > MIN_KEYWORD_LENGTH and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, _ in sorted_words[:top_n]]
    
    def _detect_category(self, text: str) -> str:
        """
        Detect content category using keywords from config
        
        Args:
            text: Text to analyze
        
        Returns:
            Category name
        """
        text_lower = text.lower()
        
        # Use category keywords from config
        categories = CATEGORY_KEYWORDS
        
        # Count matches for each category
        category_scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return DEFAULT_CATEGORY
    
    def _generate_title(self, text: str, max_length: int = MAX_TITLE_LENGTH) -> str:
        """
        Generate title from text
        
        Args:
            text: Text to generate title from
            max_length: Maximum title length
        
        Returns:
            Generated title
        """
        # Try first line
        lines = text.strip().split("\n")
        first_line = lines[0].strip()
        
        # Clean up
        first_line = first_line.lstrip("#").strip()
        
        if len(first_line) > max_length:
            return first_line[:max_length].strip() + "..."
        
        return first_line or "Untitled Note"
    
    def _generate_summary(self, text: str, max_length: int = MAX_SUMMARY_LENGTH) -> str:
        """
        Generate summary from text
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
        
        Returns:
            Summary text
        """
        # Simple summary: first paragraph or first N characters
        paragraphs = text.split("\n\n")
        first_para = paragraphs[0].strip()
        
        if len(first_para) > max_length:
            return first_para[:max_length].strip() + "..."
        
        return first_para
    
    # Security helper methods
    
    def _validate_safe_path(self, relative_path: str) -> tuple[bool, Optional[Path], str]:
        """
        Validate that path is safe and within KB root
        
        Args:
            relative_path: Relative path from KB root
        
        Returns:
            Tuple of (is_valid, resolved_path, error_message)
        """
        try:
            # Remove any leading slashes to ensure it's treated as relative
            relative_path = relative_path.lstrip("/").lstrip("\\")
            
            # Check for path traversal attempts
            if ".." in relative_path:
                return False, None, "Path traversal (..) is not allowed"
            
            # Resolve full path
            full_path = (self.kb_root_path / relative_path).resolve()
            
            # Verify it's within KB root
            try:
                full_path.relative_to(self.kb_root_path)
            except ValueError:
                return False, None, f"Path must be within knowledge base root: {self.kb_root_path}"
            
            return True, full_path, ""
            
        except Exception as e:
            return False, None, f"Invalid path: {e}"
    
    # Tool implementations
    
    async def _tool_web_search(self, params: Dict[str, Any]) -> ToolResult:
        """
        Web search tool
        
        Args:
            params: Dictionary with 'query' parameter
        
        Returns:
            ToolResult object
        """
        query = params.get("query", "")
        
        try:
            # Simple implementation: fetch URL metadata
            if query.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(query, timeout=10) as response:
                        if response.status == 200:
                            text = await response.text()
                            # Extract title (simple)
                            title = "Unknown"
                            if "<title>" in text.lower():
                                start = text.lower().find("<title>") + 7
                                end = text.lower().find("</title>", start)
                                if end > start:
                                    title = text[start:end].strip()
                            
                            return ToolResult(
                                success=True,
                                output={
                                    "url": query,
                                    "title": title,
                                    "status": response.status
                                }
                            )
            
            # For non-URL queries, return placeholder
            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "message": "Web search executed (placeholder)"
                }
            )
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
    
    async def _tool_git_command(self, params: Dict[str, Any]) -> ToolResult:
        """
        Git command tool
        
        Args:
            params: Dictionary with 'command' and optional 'cwd' parameters
        
        Returns:
            ToolResult object
        """
        command = params.get("command", "")
        cwd = params.get("cwd", ".")
        
        try:
            # Security: only allow specific safe git commands from config
            safe_commands = SAFE_GIT_COMMANDS
            
            cmd_parts = command.split()
            if not cmd_parts or cmd_parts[0] != "git":
                return ToolResult(
                    success=False,
                    output=None,
                    error="Command must start with 'git'"
                )
            
            if len(cmd_parts) < 2 or cmd_parts[1] not in safe_commands:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Git command not allowed. Allowed: {safe_commands}"
                )
            
            # Execute command
            result = subprocess.run(
                command.split(),
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return ToolResult(
                success=result.returncode == 0,
                output={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            )
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
    
    async def _tool_github_api(self, params: Dict[str, Any]) -> ToolResult:
        """
        GitHub API tool
        
        Args:
            params: Dictionary with 'endpoint' and optional 'method', 'data' parameters
        
        Returns:
            ToolResult object
        """
        endpoint = params.get("endpoint", "")
        method = params.get("method", "GET").upper()
        data = params.get("data")
        
        try:
            base_url = "https://api.github.com"
            url = f"{base_url}/{endpoint.lstrip('/')}"
            
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "QwenCodeAgent/1.0"
            }
            
            # Add auth token if available
            github_token = self.config.get("github_token")
            if github_token:
                headers["Authorization"] = f"token {github_token}"
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                    timeout=30
                ) as response:
                    result = await response.json()
                    
                    return ToolResult(
                        success=response.status < 400,
                        output={
                            "status": response.status,
                            "data": result
                        }
                    )
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
    
    async def _tool_shell_command(self, params: Dict[str, Any]) -> ToolResult:
        """
        Shell command tool (SECURITY RISK - disabled by default)
        
        Args:
            params: Dictionary with 'command' and optional 'cwd' parameters
        
        Returns:
            ToolResult object
        """
        if not self.enable_shell:
            return ToolResult(
                success=False,
                output=None,
                error="Shell command tool is disabled for security"
            )
        
        command = params.get("command", "")
        cwd = params.get("cwd", ".")
        
        try:
            # Security: block dangerous commands from config
            dangerous_patterns = DANGEROUS_SHELL_PATTERNS
            
            if any(pattern in command for pattern in dangerous_patterns):
                return ToolResult(
                    success=False,
                    output=None,
                    error="Command contains dangerous patterns"
                )
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return ToolResult(
                success=result.returncode == 0,
                output={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            )
        
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
    
    async def _tool_file_create(self, params: Dict[str, Any]) -> ToolResult:
        """
        Create a new file
        
        Args:
            params: Dictionary with 'path' (relative to KB root) and 'content' parameters
        
        Returns:
            ToolResult object
        """
        relative_path = params.get("path", "")
        content = params.get("content", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            return ToolResult(success=False, output=None, error=error)
        
        try:
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists
            if full_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File already exists: {relative_path}"
                )
            
            # Write file
            full_path.write_text(content, encoding="utf-8")
            
            logger.info(f"Created file: {relative_path}")
            
            # Extract metadata from content and path
            title = self._extract_title_from_markdown(content)
            kb_structure = self._infer_kb_structure_from_path(relative_path)
            
            # Register in tracker
            self.kb_changes.add_file_created(
                path=relative_path,
                title=title,
                kb_structure=kb_structure
            )
            
            return ToolResult(
                success=True,
                output={
                    "path": relative_path,
                    "full_path": str(full_path),
                    "size": len(content)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Failed to create file: {e}")
    
    async def _tool_file_edit(self, params: Dict[str, Any]) -> ToolResult:
        """
        Edit an existing file
        
        Args:
            params: Dictionary with 'path' (relative to KB root) and 'content' parameters
        
        Returns:
            ToolResult object
        """
        relative_path = params.get("path", "")
        content = params.get("content", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            return ToolResult(success=False, output=None, error=error)
        
        try:
            # Check if file exists
            if not full_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File does not exist: {relative_path}"
                )
            
            if not full_path.is_file():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a file: {relative_path}"
                )
            
            # Backup old content
            old_content = full_path.read_text(encoding="utf-8")
            
            # Write new content
            full_path.write_text(content, encoding="utf-8")
            
            logger.info(f"Edited file: {relative_path}")
            
            # Register in tracker
            self.kb_changes.add_file_edited(relative_path)
            
            return ToolResult(
                success=True,
                output={
                    "path": relative_path,
                    "full_path": str(full_path),
                    "old_size": len(old_content),
                    "new_size": len(content)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Failed to edit file: {e}")
    
    async def _tool_file_delete(self, params: Dict[str, Any]) -> ToolResult:
        """
        Delete a file
        
        Args:
            params: Dictionary with 'path' (relative to KB root) parameter
        
        Returns:
            ToolResult object
        """
        relative_path = params.get("path", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            return ToolResult(success=False, output=None, error=error)
        
        try:
            # Check if file exists
            if not full_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File does not exist: {relative_path}"
                )
            
            if not full_path.is_file():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a file: {relative_path}"
                )
            
            # Delete file
            full_path.unlink()
            
            logger.info(f"Deleted file: {relative_path}")
            return ToolResult(
                success=True,
                output={
                    "path": relative_path,
                    "full_path": str(full_path)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Failed to delete file: {e}")
    
    async def _tool_file_move(self, params: Dict[str, Any]) -> ToolResult:
        """
        Move/rename a file
        
        Args:
            params: Dictionary with 'source' and 'destination' (both relative to KB root)
        
        Returns:
            ToolResult object
        """
        source_path = params.get("source", "")
        dest_path = params.get("destination", "")
        
        # Validate source path
        is_valid, full_source, error = self._validate_safe_path(source_path)
        if not is_valid:
            return ToolResult(success=False, output=None, error=f"Invalid source: {error}")
        
        # Validate destination path
        is_valid, full_dest, error = self._validate_safe_path(dest_path)
        if not is_valid:
            return ToolResult(success=False, output=None, error=f"Invalid destination: {error}")
        
        try:
            # Check if source exists
            if not full_source.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Source file does not exist: {source_path}"
                )
            
            if not full_source.is_file():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Source is not a file: {source_path}"
                )
            
            # Check if destination already exists
            if full_dest.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Destination already exists: {dest_path}"
                )
            
            # Create parent directories if needed
            full_dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            full_source.rename(full_dest)
            
            logger.info(f"Moved file: {source_path} -> {dest_path}")
            return ToolResult(
                success=True,
                output={
                    "source": source_path,
                    "destination": dest_path,
                    "full_source": str(full_source),
                    "full_destination": str(full_dest)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Failed to move file: {e}")
    
    async def _tool_folder_create(self, params: Dict[str, Any]) -> ToolResult:
        """
        Create a new folder
        
        Args:
            params: Dictionary with 'path' (relative to KB root) parameter
        
        Returns:
            ToolResult object
        """
        relative_path = params.get("path", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            return ToolResult(success=False, output=None, error=error)
        
        try:
            # Check if already exists
            if full_path.exists():
                if full_path.is_dir():
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Folder already exists: {relative_path}"
                    )
                else:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Path exists but is not a folder: {relative_path}"
                    )
            
            # Create folder
            full_path.mkdir(parents=True, exist_ok=False)
            
            logger.info(f"Created folder: {relative_path}")
            
            # Register in tracker
            self.kb_changes.add_folder_created(relative_path)
            
            return ToolResult(
                success=True,
                output={
                    "path": relative_path,
                    "full_path": str(full_path)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Failed to create folder: {e}")
    
    async def _tool_folder_delete(self, params: Dict[str, Any]) -> ToolResult:
        """
        Delete a folder and its contents
        
        Args:
            params: Dictionary with 'path' (relative to KB root) parameter
        
        Returns:
            ToolResult object
        """
        import shutil
        
        relative_path = params.get("path", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            return ToolResult(success=False, output=None, error=error)
        
        try:
            # Check if exists
            if not full_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Folder does not exist: {relative_path}"
                )
            
            if not full_path.is_dir():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Path is not a folder: {relative_path}"
                )
            
            # Prevent deleting KB root itself
            if full_path == self.kb_root_path:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Cannot delete knowledge base root folder"
                )
            
            # Delete folder and contents
            shutil.rmtree(full_path)
            
            logger.info(f"Deleted folder: {relative_path}")
            return ToolResult(
                success=True,
                output={
                    "path": relative_path,
                    "full_path": str(full_path)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Failed to delete folder: {e}")
    
    async def _tool_folder_move(self, params: Dict[str, Any]) -> ToolResult:
        """
        Move/rename a folder
        
        Args:
            params: Dictionary with 'source' and 'destination' (both relative to KB root)
        
        Returns:
            ToolResult object
        """
        import shutil
        
        source_path = params.get("source", "")
        dest_path = params.get("destination", "")
        
        # Validate source path
        is_valid, full_source, error = self._validate_safe_path(source_path)
        if not is_valid:
            return ToolResult(success=False, output=None, error=f"Invalid source: {error}")
        
        # Validate destination path
        is_valid, full_dest, error = self._validate_safe_path(dest_path)
        if not is_valid:
            return ToolResult(success=False, output=None, error=f"Invalid destination: {error}")
        
        try:
            # Check if source exists
            if not full_source.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Source folder does not exist: {source_path}"
                )
            
            if not full_source.is_dir():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Source is not a folder: {source_path}"
                )
            
            # Prevent moving KB root itself
            if full_source == self.kb_root_path:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Cannot move knowledge base root folder"
                )
            
            # Check if destination already exists
            if full_dest.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Destination already exists: {dest_path}"
                )
            
            # Create parent directories if needed
            full_dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Move folder
            shutil.move(str(full_source), str(full_dest))
            
            logger.info(f"Moved folder: {source_path} -> {dest_path}")
            return ToolResult(
                success=True,
                output={
                    "source": source_path,
                    "destination": dest_path,
                    "full_source": str(full_source),
                    "full_destination": str(full_dest)
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Failed to move folder: {e}")
    
    def validate_input(self, content: Dict) -> bool:
        """
        Validate input content
        
        Args:
            content: Content to validate
        
        Returns:
            True if valid, False otherwise
        """
        return isinstance(content, dict) and "text" in content
    
    def _extract_title_from_markdown(self, content: str) -> str:
        """
        Extract title from markdown content
        
        Args:
            content: Markdown content
        
        Returns:
            Extracted title or default
        """
        lines = content.split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                # Found h1 heading
                return line[2:].strip()
        
        # No h1 found, use first non-empty line
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:MAX_TITLE_LENGTH] + ("..." if len(line) > MAX_TITLE_LENGTH else "")
        
        return "Untitled"
    
    def _infer_kb_structure_from_path(self, path: str) -> KBStructure:
        """
        Infer KB structure from file path
        
        Args:
            path: Relative file path (e.g., "ai/models/gpt4.md")
        
        Returns:
            KBStructure object
        """
        parts = path.split("/")
        
        # Remove filename
        if parts and parts[-1].endswith(".md"):
            parts = parts[:-1]
        
        if len(parts) == 0:
            return KBStructure(category="general")
        elif len(parts) == 1:
            return KBStructure(category=parts[0])
        elif len(parts) >= 2:
            return KBStructure(category=parts[0], subcategory=parts[1])
        
        return KBStructure(category="general")
    
    def set_instruction(self, instruction: str) -> None:
        """
        Update agent instruction
        
        Args:
            instruction: New instruction
        """
        self.instruction = instruction
        logger.info("Agent instruction updated")
    
    def get_instruction(self) -> str:
        """
        Get current instruction
        
        Returns:
            Current instruction
        """
        return self.instruction
