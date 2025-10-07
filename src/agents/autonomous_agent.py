"""
Autonomous Agent
Автономный агент с циклом планирования и вызовом тулзов
Использует LLM коннекторы для взаимодействия с различными LLM API
"""

import json
import subprocess
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp
import requests
from loguru import logger

from .base_agent import AgentResult as BaseAgentResult, BaseAgent, KBStructure
from .llm_connectors import BaseLLMConnector, LLMResponse
from .tools import ToolManager, build_default_tool_manager
from config.agent_prompts import QWEN_CODE_AGENT_INSTRUCTION


class ActionType(Enum):
    """Типы действий агента"""
    TOOL_CALL = "tool_call"
    END = "end"


@dataclass
class AgentDecision:
    """Решение агента о следующем действии"""
    action: ActionType
    reasoning: str
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    final_result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "action": self.action.value,
            "reasoning": self.reasoning,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "final_result": self.final_result
        }


@dataclass
class ToolExecution:
    """Результат выполнения тулза"""
    tool_name: str
    params: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "params": self.params,
            "result": self.result,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp
        }


@dataclass
class AgentContext:
    """Контекст выполнения агента"""
    task: str
    executions: List[ToolExecution] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def add_execution(self, execution: ToolExecution) -> None:
        """Добавить выполнение тулза"""
        self.executions.append(execution)
    
    def add_error(self, error: str) -> None:
        """Добавить ошибку"""
        self.errors.append(error)
    
    def get_history(self) -> str:
        """Получить историю выполнения в текстовом формате"""
        if not self.executions:
            return "Пока не выполнено ни одного действия."
        
        lines = []
        for i, exec in enumerate(self.executions, 1):
            status = "✓" if exec.success else "✗"
            lines.append(f"{i}. {status} {exec.tool_name}")
            lines.append(f"   Параметры: {exec.params}")
            if exec.success:
                lines.append(f"   Результат: {exec.result}")
            else:
                lines.append(f"   Ошибка: {exec.error}")
        
        return "\n".join(lines)
    
    def get_tools_used(self) -> List[str]:
        """Получить список использованных тулзов"""
        return list(set([exec.tool_name for exec in self.executions]))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task": self.task,
            "executions": [exec.to_dict() for exec in self.executions],
            "errors": self.errors,
            "tools_used": self.get_tools_used()
        }


@dataclass
class AutonomousAgentResult:
    """Результат работы автономного агента (расширенный)"""
    markdown: str
    title: str
    kb_structure: KBStructure
    metadata: Dict[str, Any]
    iterations: int
    context: AgentContext
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "markdown": self.markdown,
            "title": self.title,
            "kb_structure": self.kb_structure.to_dict(),
            "metadata": self.metadata,
            "iterations": self.iterations,
            "context": self.context.to_dict()
        }
    
    def to_base_agent_result(self) -> BaseAgentResult:
        """Конвертировать в стандартный AgentResult"""
        # Извлекаем информацию о файлах из контекста
        files_created = []
        files_edited = []
        folders_created = []
        
        for execution in self.context.executions:
            if execution.tool_name == "file_create" and execution.success:
                if isinstance(execution.result, dict):
                    files_created.append(execution.result.get("path", "unknown"))
            elif execution.tool_name == "file_edit" and execution.success:
                if isinstance(execution.result, dict):
                    files_edited.append(execution.result.get("path", "unknown"))
            elif execution.tool_name == "folder_create" and execution.success:
                if isinstance(execution.result, dict):
                    folders_created.append(execution.result.get("path", "unknown"))
        
        # Генерируем summary
        summary = f"Completed in {self.iterations} iterations. "
        if files_created:
            summary += f"Created {len(files_created)} file(s). "
        if files_edited:
            summary += f"Edited {len(files_edited)} file(s). "
        if folders_created:
            summary += f"Created {len(folders_created)} folder(s)."
        
        return BaseAgentResult(
            markdown=self.markdown,
            summary=summary.strip(),
            files_created=files_created,
            files_edited=files_edited,
            folders_created=folders_created,
            metadata=self.metadata
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


class AutonomousAgent(BaseAgent):
    """
    Автономный агент с циклом планирования
    
    Агент работает в цикле:
    1. Анализирует текущее состояние
    2. Принимает решение используя LLM через коннектор
    3. Выполняет действие (вызов тулза)
    4. Обновляет контекст
    5. Повторяет до завершения задачи
    
    Особенности:
    - Использует LLM коннекторы для работы с разными API
    - Поддерживает OpenAI function calling
    - Встроенные инструменты: web search, git, github, файлы/папки
    - TODO планирование и автономное выполнение
    """
    
    DEFAULT_INSTRUCTION = QWEN_CODE_AGENT_INSTRUCTION
    
    def __init__(
        self,
        llm_connector: Optional[BaseLLMConnector] = None,
        config: Optional[Dict] = None,
        instruction: Optional[str] = None,
        max_iterations: int = 10,
        # Tool enablement flags (from QwenCodeAgent)
        enable_web_search: bool = True,
        enable_git: bool = True,
        enable_github: bool = True,
        enable_shell: bool = False,
        enable_file_management: bool = True,
        enable_folder_management: bool = True,
        kb_root_path: Optional[Path] = None,
        enable_vector_search: bool = False,
        vector_search_manager: Optional['VectorSearchManager'] = None,
        enable_mcp: bool = False,
        enable_mcp_memory: bool = False
    ):
        """
        Initialize autonomous agent
        
        Args:
            llm_connector: LLM connector instance for making API calls
            config: Configuration dictionary
            instruction: Agent instruction
            max_iterations: Maximum iterations in agent loop
            enable_web_search: Enable web search tool
            enable_git: Enable git command tool
            enable_github: Enable GitHub API tool
            enable_shell: Enable shell command tool (security risk)
            enable_file_management: Enable file management tools
            enable_folder_management: Enable folder management tools
            kb_root_path: Root path for knowledge base
            enable_vector_search: Enable vector search tool
            vector_search_manager: Optional pre-configured vector search manager
            enable_mcp: Enable MCP (Model Context Protocol) support
            enable_mcp_memory: Enable MCP memory agent tool
        """
        super().__init__(config)
        
        self.llm_connector = llm_connector
        self.instruction = instruction or self.DEFAULT_INSTRUCTION
        self.max_iterations = max_iterations
        self.tools: Dict[str, callable] = {}
        
        # Tool enablement flags
        self.enable_web_search = enable_web_search
        self.enable_git = enable_git
        self.enable_github = enable_github
        self.enable_shell = enable_shell
        self.enable_file_management = enable_file_management
        self.enable_folder_management = enable_folder_management
        self.enable_vector_search = enable_vector_search
        self.enable_mcp = enable_mcp
        self.enable_mcp_memory = enable_mcp_memory
        
        # Knowledge base root path for safe file operations
        self.kb_root_path = kb_root_path or Path("./knowledge_base")
        self.kb_root_path = self.kb_root_path.resolve()
        
        # Ensure KB root path exists
        try:
            self.kb_root_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Knowledge base root path ensured: {self.kb_root_path}")
        except Exception as e:
            logger.warning(f"Could not create KB root path {self.kb_root_path}: {e}")
        
        # Vector search manager
        self.vector_search_manager = vector_search_manager
        
        # User ID for per-user MCP server discovery
        self.user_id = self.config.get("user_id") if self.config else None
        
        # Agent state
        self.current_plan: Optional[TodoPlan] = None
        self.execution_log: List[Dict[str, Any]] = []
        
        # MCP tools description (cached)
        self._mcp_tools_description: Optional[str] = None
        
        # Initialize tool manager and lightweight wrappers
        self.tool_manager: ToolManager = build_default_tool_manager(
            kb_root_path=self.kb_root_path,
            base_agent_class=BaseAgent,
            enable_web_search=self.enable_web_search,
            enable_git=self.enable_git,
            enable_github=self.enable_github,
            enable_shell=self.enable_shell,
            enable_file_management=self.enable_file_management,
            enable_folder_management=self.enable_folder_management,
            enable_vector_search=self.enable_vector_search,
            enable_mcp=self.enable_mcp,
            enable_mcp_memory=self.enable_mcp_memory,
            github_token=self.config.get("github_token"),
            vector_search_manager=self.vector_search_manager,
            get_current_plan=lambda: self.current_plan,
            set_current_plan=lambda plan: setattr(self, "current_plan", plan),
            user_id=self.user_id,
        )

        # Back-compat mapping: name -> async callable delegating to ToolManager
        self.tools: Dict[str, callable] = {}
        for tool_name in self.tool_manager.names():
            async def _runner(params: Dict[str, Any], _name: str = tool_name):
                return await self.tool_manager.execute(_name, params)
            self.tools[tool_name] = _runner
        
        logger.info(
            f"AutonomousAgent initialized: "
            f"max_iterations={max_iterations}, "
            f"llm_connector={llm_connector.__class__.__name__ if llm_connector else 'None'}, "
            f"kb_root={self.kb_root_path}, "
            f"vector_search={enable_vector_search}"
        )
        logger.info(f"Enabled tools: {self.tool_manager.names()}")
    
    # Legacy register methods removed in favor of ToolManager
    
    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        """Delegate to ToolManager to build OpenAI function schemas."""
        return self.tool_manager.build_llm_tools_schema()
    
    def get_tools_description(self) -> str:
        """Получить описание доступных тулзов"""
        if not self.tool_manager.names():
            return "Нет доступных тулзов."
        
        lines = []
        for tool_name in self.tool_manager.names():
            lines.append(f"- {tool_name}")
        
        return "\n".join(lines)
    
    async def get_mcp_tools_description(self) -> str:
        """
        Get description of available MCP tools
        
        Returns:
            Formatted description of MCP tools for use in prompts
        """
        # Return cached description if available
        if self._mcp_tools_description is not None:
            return self._mcp_tools_description
        
        # Only generate if MCP is enabled
        if not self.enable_mcp:
            self._mcp_tools_description = ""
            return ""
        
        try:
            from .mcp import get_mcp_tools_description, format_mcp_tools_for_prompt
            
            # Get tools description
            tools_desc = await get_mcp_tools_description(user_id=self.user_id)
            
            # Format for system prompt
            formatted = format_mcp_tools_for_prompt(tools_desc, include_in_system=True)
            
            # Cache the result
            self._mcp_tools_description = formatted
            
            if formatted:
                logger.info(f"[AutonomousAgent] MCP tools description generated ({len(formatted)} chars)")
            
            return formatted
            
        except Exception as e:
            logger.error(f"[AutonomousAgent] Failed to get MCP tools description: {e}")
            self._mcp_tools_description = ""
            return ""
    
    async def process(self, content: Dict) -> Dict:
        """
        Process content using autonomous agent loop
        
        Args:
            content: Content dictionary with text, urls, etc.
        
        Returns:
            Processed content dictionary
        """
        logger.info("[AutonomousAgent] Starting autonomous processing")
        
        if not self.validate_input(content):
            raise ValueError("Invalid input content")
        
        # Подготовить задачу
        task = self._prepare_task(content)
        
        # Запустить агентский цикл
        result = await self._agent_loop(task)
        
        logger.info(f"[AutonomousAgent] Completed in {result.iterations} iterations")
        
        # Извлечь информацию о файлах из контекста для summary
        files_created = []
        files_edited = []
        folders_created = []
        
        for execution in result.context.executions:
            if execution.tool_name == "file_create" and execution.success:
                if isinstance(execution.result, dict):
                    files_created.append(execution.result.get("path", "unknown"))
            elif execution.tool_name == "file_edit" and execution.success:
                if isinstance(execution.result, dict):
                    files_edited.append(execution.result.get("path", "unknown"))
            elif execution.tool_name == "folder_create" and execution.success:
                if isinstance(execution.result, dict):
                    folders_created.append(execution.result.get("path", "unknown"))
        
        # Добавить информацию о файлах в метаданные
        metadata_with_files = {
            **result.metadata,
            "files_created": files_created,
            "files_edited": files_edited,
            "folders_created": folders_created
        }
        
        return {
            "markdown": result.markdown,
            "title": result.title,
            "kb_structure": result.kb_structure,
            "metadata": metadata_with_files
        }
    
    def _prepare_task(self, content: Dict) -> str:
        """
        Подготовить задачу из контента
        
        Args:
            content: Content dictionary
        
        Returns:
            Task description
        """
        text = content.get("text", "")
        urls = content.get("urls", [])
        
        task = f"""Обработай следующий контент и сохрани его в базу знаний:

ТЕКСТ:
{text}
"""
        
        if urls:
            task += f"\nURL:\n" + "\n".join([f"- {url}" for url in urls])
        
        return task
    
    async def _agent_loop(self, task: str) -> AutonomousAgentResult:
        """
        Основной цикл агента
        
        Args:
            task: Task description
        
        Returns:
            AutonomousAgentResult with final output
        """
        context = AgentContext(task=task)
        iteration = 0
        
        logger.info(f"[AutonomousAgent] Starting agent loop with task: {task[:100]}...")
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"[AutonomousAgent] Iteration {iteration}/{self.max_iterations}")
            
            # LLM принимает решение
            decision = await self._make_decision(context)
            logger.debug(f"[AutonomousAgent] Decision: {decision.to_dict()}")
            
            # Проверка завершения
            if decision.action == ActionType.END:
                logger.info("[AutonomousAgent] Agent decided to END")
                return await self._finalize_result(context, decision, iteration)
            
            # Выполнить тулз
            if decision.action == ActionType.TOOL_CALL:
                execution = await self._execute_tool(decision)
                context.add_execution(execution)
                
                if not execution.success:
                    logger.warning(f"[AutonomousAgent] Tool execution failed: {execution.error}")
        
        # Превышен лимит итераций
        logger.warning(f"[AutonomousAgent] Max iterations ({self.max_iterations}) reached")
        return await self._finalize_result(context, None, iteration)
    
    async def _make_decision(self, context: AgentContext) -> AgentDecision:
        """
        Принять решение используя LLM через коннектор
        
        Args:
            context: Current agent context
        
        Returns:
            AgentDecision with next action
        """
        logger.debug("[AutonomousAgent] Making decision")
        
        # If no LLM connector, use rule-based logic
        if not self.llm_connector:
            return await self._make_decision_rule_based(context)
        
        # Use LLM connector for decision making
        return await self._make_decision_llm(context)
    
    async def _make_decision_rule_based(self, context: AgentContext) -> AgentDecision:
        """
        Rule-based decision making (fallback when no LLM)
        
        Args:
            context: Current agent context
        
        Returns:
            AgentDecision
        """
        logger.debug("[AutonomousAgent] Using rule-based decision making")
        
        # Check if we have a plan yet
        if not self.current_plan:
            # First step: create TODO plan
            logger.info("[AutonomousAgent] Creating TODO plan")
            
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
            
            logger.info(f"[AutonomousAgent] Executing task: {task['task']}")
            
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
        logger.info("[AutonomousAgent] All tasks completed, generating final result")
        
        # Generate markdown from execution results
        markdown = await self._generate_final_markdown(context)
        
        return AgentDecision(
            action=ActionType.END,
            reasoning="All tasks completed successfully",
            final_result=markdown
        )
    
    async def _make_decision_llm(self, context: AgentContext) -> AgentDecision:
        """
        LLM-based decision making using connector
        
        Args:
            context: Current agent context
        
        Returns:
            AgentDecision
        """
        logger.debug("[AutonomousAgent] Using LLM-based decision making")
        
        # Get MCP tools description if enabled
        mcp_description = await self.get_mcp_tools_description()
        
        # Prepare system message with MCP tools info if available
        system_content = self.instruction
        if mcp_description:
            system_content = f"{self.instruction}\n\n{mcp_description}"
        
        # Подготовить сообщения
        messages = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": context.task
            }
        ]
        
        # Добавить историю выполнения
        if context.executions:
            history = context.get_history()
            messages.append({
                "role": "assistant",
                "content": f"История выполнения:\n{history}"
            })
        
        # Вызвать LLM через коннектор
        try:
            tools_schema = self._build_tools_schema()
            
            logger.debug(f"[AutonomousAgent] Calling LLM with {len(tools_schema)} tools")
            
            response = await self.llm_connector.chat_completion(
                messages=messages,
                tools=tools_schema,
                temperature=0.7
            )
            
            # Проверка function calling
            if response.has_tool_calls():
                tool_call = response.tool_calls[0]  # Берем первый вызов
                
                logger.info(
                    f"[AutonomousAgent] LLM decided to call tool: "
                    f"{tool_call['function']['name']}"
                )
                
                return AgentDecision(
                    action=ActionType.TOOL_CALL,
                    reasoning=response.content or "LLM decided to use a tool",
                    tool_name=tool_call['function']['name'],
                    tool_params=tool_call['function']['arguments']
                )
            
            # LLM решил завершить работу
            if response.content:
                logger.info("[AutonomousAgent] LLM decided to END")
                
                return AgentDecision(
                    action=ActionType.END,
                    reasoning="Task completed",
                    final_result=response.content
                )
            
            # Непонятный ответ
            logger.warning("[AutonomousAgent] LLM returned unclear response")
            return AgentDecision(
                action=ActionType.END,
                reasoning="Unclear response from LLM",
                final_result=await self._generate_fallback_markdown(context)
            )
        
        except Exception as e:
            logger.error(f"[AutonomousAgent] Error calling LLM: {e}", exc_info=True)
            
            # Вернуть решение о завершении с ошибкой
            return AgentDecision(
                action=ActionType.END,
                reasoning=f"Error: {e}",
                final_result=await self._generate_fallback_markdown(context)
            )
    
    def _extract_text_from_task(self, task: str) -> str:
        """Extract content text from task description"""
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
    
    async def _execute_tool(self, decision: AgentDecision) -> ToolExecution:
        """
        Выполнить тулз
        
        Args:
            decision: Agent decision with tool call
        
        Returns:
            ToolExecution with result
        """
        tool_name = decision.tool_name
        params = decision.tool_params or {}
        
        logger.info(f"[AutonomousAgent] Executing tool: {tool_name} with params: {params}")
        
        # Проверка существования тулза
        if not self.tool_manager.has(tool_name):
            error = f"Tool not found: {tool_name}"
            logger.error(f"[AutonomousAgent] {error}")
            return ToolExecution(
                tool_name=tool_name,
                params=params,
                result=None,
                success=False,
                error=error
            )
        
        # Выполнить тулз
        try:
            result = await self.tool_manager.execute(tool_name, params)
            
            # Check if result indicates success
            success = True
            if isinstance(result, dict):
                success = result.get("success", True)
            
            logger.debug(f"[AutonomousAgent] Tool {tool_name} executed successfully")
            
            return ToolExecution(
                tool_name=tool_name,
                params=params,
                result=result,
                success=success
            )
        
        except Exception as e:
            error = f"Tool execution error: {e}"
            logger.error(f"[AutonomousAgent] {error}", exc_info=True)
            
            return ToolExecution(
                tool_name=tool_name,
                params=params,
                result=None,
                success=False,
                error=error
            )
    
    async def _finalize_result(
        self,
        context: AgentContext,
        decision: Optional[AgentDecision],
        iterations: int
    ) -> AutonomousAgentResult:
        """
        Финализировать результат работы агента
        
        Args:
            context: Agent context
            decision: Final decision (if any)
            iterations: Number of iterations
        
        Returns:
            AutonomousAgentResult
        """
        logger.info("[AutonomousAgent] Finalizing result")
        
        # Получить итоговый markdown
        if decision and decision.final_result:
            markdown = decision.final_result
        else:
            markdown = await self._generate_fallback_markdown(context)
        
        # Извлечь метаданные
        title = self._extract_title(markdown)
        kb_structure = await self._determine_kb_structure_from_markdown(markdown, context)
        
        metadata = {
            "agent": "AutonomousAgent",
            "llm_model": self.llm_connector.get_model_name() if self.llm_connector else "rule-based",
            "processed_at": datetime.now().isoformat(),
            "iterations": iterations,
            "tools_used": context.get_tools_used(),
            "executions": [exec.to_dict() for exec in context.executions],
            "errors": context.errors
        }
        
        return AutonomousAgentResult(
            markdown=markdown,
            title=title,
            kb_structure=kb_structure,
            metadata=metadata,
            iterations=iterations,
            context=context
        )
    
    async def _generate_fallback_markdown(self, context: AgentContext) -> str:
        """
        Сгенерировать markdown если агент не вернул результат
        
        Args:
            context: Agent context
        
        Returns:
            Markdown content
        """
        lines = [
            "# Результат обработки",
            "",
            "## Задача",
            context.task,
            "",
            "## Выполненные действия",
            context.get_history(),
            ""
        ]
        
        if context.errors:
            lines.extend([
                "## Ошибки",
                "\n".join([f"- {error}" for error in context.errors]),
                ""
            ])
        
        return "\n".join(lines)
    
    async def _generate_final_markdown(self, context: AgentContext) -> str:
        """Generate final markdown from execution results"""
        # Collect all analysis results
        analysis_results = []
        web_results = []
        files_created = []
        folders_created = []
        files_modified = []
        
        for execution in context.executions:
            if execution.tool_name == "analyze_content" and execution.success:
                analysis_results.append(execution.result)
            elif execution.tool_name == "web_search" and execution.success:
                web_results.append(execution.result)
            elif execution.tool_name == "file_create" and execution.success:
                if isinstance(execution.result, dict):
                    files_created.append(execution.result.get("path", "unknown"))
            elif execution.tool_name == "folder_create" and execution.success:
                if isinstance(execution.result, dict):
                    folders_created.append(execution.result.get("path", "unknown"))
            elif execution.tool_name == "file_edit" and execution.success:
                if isinstance(execution.result, dict):
                    files_modified.append(execution.result.get("path", "unknown"))
        
        # Extract text from task
        text = self._extract_text_from_task(context.task)
        
        # Generate metadata
        title = BaseAgent.generate_title(text)
        category = BaseAgent.detect_category(text)
        tags = BaseAgent.extract_keywords(text, top_n=5)
        summary = BaseAgent.generate_summary(text)
        
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
        
        # Report on files/folders created during execution
        if files_created or folders_created or files_modified:
            lines.append("## Changes Applied")
            lines.append("")
            if files_created:
                lines.append("**Files Created:**")
                for path in files_created:
                    lines.append(f"- ✓ {path}")
                lines.append("")
            if folders_created:
                lines.append("**Folders Created:**")
                for path in folders_created:
                    lines.append(f"- ✓ {path}")
                lines.append("")
            if files_modified:
                lines.append("**Files Modified:**")
                for path in files_modified:
                    lines.append(f"- ✓ {path}")
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
    
    def _extract_title(self, markdown: str) -> str:
        """
        Extract title from markdown
        
        Args:
            markdown: Markdown content
        
        Returns:
            Title string
        """
        for line in markdown.split("\n"):
            if line.startswith("# "):
                return line[2:].strip()
        
        return "Untitled Note"
    
    async def _determine_kb_structure_from_markdown(
        self,
        markdown: str,
        context: AgentContext
    ) -> KBStructure:
        """
        Determine KB structure from markdown and context
        
        Args:
            markdown: Markdown content
            context: Agent context
        
        Returns:
            KBStructure
        """
        # Extract text from task
        text = self._extract_text_from_task(context.task)
        
        # Detect category
        category = BaseAgent.detect_category(text)
        tags = BaseAgent.extract_keywords(text, top_n=5)
        
        # Determine subcategory
        subcategory = None
        text_lower = text.lower()
        
        if category == "ai":
            if any(kw in text_lower for kw in ["machine learning", "ml", "neural network"]):
                subcategory = "machine-learning"
            elif any(kw in text_lower for kw in ["nlp", "natural language"]):
                subcategory = "nlp"
        elif category == "tech":
            if any(kw in text_lower for kw in ["python", "javascript", "code", "programming"]):
                subcategory = "programming"
        
        return KBStructure(
            category=category,
            subcategory=subcategory,
            tags=tags
        )
    
    # ====================================================================
    # TOOL EXECUTION
    # ====================================================================
    # All tools are now self-contained in their respective modules
    # with their own metadata, schemas, and implementation.
    # Tools are executed via ToolManager. No wrapper methods needed.
    
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
            "keywords": BaseAgent.extract_keywords(text)
        }
        
        return analysis
    
    async def _extract_metadata(self, content: Dict) -> Dict[str, Any]:
        """Extract metadata (backward compatibility)"""
        text = content.get("text", "")
        
        return {
            "category": BaseAgent.detect_category(text),
            "tags": BaseAgent.extract_keywords(text, top_n=5),
            "title": BaseAgent.generate_title(text)
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
            "title": metadata.get("title", BaseAgent.generate_title(text)),
            "category": metadata.get("category", "general"),
            "tags": metadata.get("tags", []),
            "content": text,
            "urls": urls,
            "analysis": analysis,
            "web_context": web_context,
            "summary": BaseAgent.generate_summary(text)
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
    
    def validate_input(self, content: Dict) -> bool:
        """
        Validate input content
        
        Args:
            content: Content to validate
        
        Returns:
            True if valid
        """
        return isinstance(content, dict) and "text" in content
    
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
