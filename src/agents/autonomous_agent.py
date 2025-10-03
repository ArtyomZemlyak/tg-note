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
        kb_root_path: Optional[Path] = None
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
        
        # Knowledge base root path for safe file operations
        self.kb_root_path = kb_root_path or Path("./knowledge_base")
        self.kb_root_path = self.kb_root_path.resolve()
        
        # Agent state
        self.current_plan: Optional[TodoPlan] = None
        self.execution_log: List[Dict[str, Any]] = []
        
        # Register all tools
        self._register_all_tools()
        
        logger.info(
            f"AutonomousAgent initialized: "
            f"max_iterations={max_iterations}, "
            f"llm_connector={llm_connector.__class__.__name__ if llm_connector else 'None'}, "
            f"kb_root={self.kb_root_path}"
        )
        logger.info(f"Enabled tools: {list(self.tools.keys())}")
    
    def _register_all_tools(self) -> None:
        """Register all available tools"""
        # Plan TODO tool (always available)
        self.register_tool("plan_todo", self._tool_plan_todo)
        
        # Analyze content tool (always available)
        self.register_tool("analyze_content", self._tool_analyze_content)
        
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
    
    def register_tool(self, name: str, handler: callable) -> None:
        """
        Зарегистрировать тулз
        
        Args:
            name: Название тулза
            handler: Функция-обработчик
        """
        self.tools[name] = handler
        logger.debug(f"Registered tool: {name}")
    
    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Построить схему тулзов для OpenAI function calling
        
        Returns:
            List of tool definitions
        """
        tools = []
        
        # Plan TODO tool
        if "plan_todo" in self.tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": "plan_todo",
                    "description": "Создать план действий (TODO список). ОБЯЗАТЕЛЬНО вызови первым!",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "tasks": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Список задач для выполнения"
                            }
                        },
                        "required": ["tasks"]
                    }
                }
            })
        
        # Web search tool
        if "web_search" in self.tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Поиск информации в интернете",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Поисковый запрос или URL"
                            }
                        },
                        "required": ["query"]
                    }
                }
            })
        
        # File create tool
        if "file_create" in self.tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": "file_create",
                    "description": "Создать файл в базе знаний",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Относительный путь к файлу (например: 'ai/neural-networks.md')"
                            },
                            "content": {
                                "type": "string",
                                "description": "Содержимое файла в markdown формате"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            })
        
        # File edit tool
        if "file_edit" in self.tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": "file_edit",
                    "description": "Редактировать существующий файл",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Относительный путь к файлу"
                            },
                            "content": {
                                "type": "string",
                                "description": "Новое содержимое файла"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            })
        
        # Folder create tool
        if "folder_create" in self.tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": "folder_create",
                    "description": "Создать папку в базе знаний",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Относительный путь к папке (например: 'ai/concepts')"
                            }
                        },
                        "required": ["path"]
                    }
                }
            })
        
        # Analyze content tool
        if "analyze_content" in self.tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": "analyze_content",
                    "description": "Анализировать контент и извлечь ключевую информацию",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Текст для анализа"
                            }
                        },
                        "required": ["text"]
                    }
                }
            })
        
        return tools
    
    def get_tools_description(self) -> str:
        """Получить описание доступных тулзов"""
        if not self.tools:
            return "Нет доступных тулзов."
        
        lines = []
        for tool_name in self.tools.keys():
            lines.append(f"- {tool_name}")
        
        return "\n".join(lines)
    
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
        
        return {
            "markdown": result.markdown,
            "title": result.title,
            "kb_structure": result.kb_structure,
            "metadata": result.metadata
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
        
        # Подготовить сообщения
        messages = [
            {
                "role": "system",
                "content": self.instruction
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
        if tool_name not in self.tools:
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
            handler = self.tools[tool_name]
            result = await handler(params)
            
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
    # TOOL IMPLEMENTATIONS (from QwenCodeAgent)
    # ====================================================================
    
    async def _tool_plan_todo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plan_todo tool call"""
        tasks = params.get("tasks", [])
        
        logger.info(f"[AutonomousAgent] Creating plan with {len(tasks)} tasks")
        
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
            "keywords": BaseAgent.extract_keywords(text),
            "category": BaseAgent.detect_category(text)
        }
        
        return analysis
    
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
    
    async def _tool_web_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Web search tool"""
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
                            
                            logger.info(f"[web_search] ✓ Fetched URL: {query}")
                            return {
                                "success": True,
                                "url": query,
                                "title": title,
                                "status": response.status
                            }
            
            # For non-URL queries, return placeholder
            logger.info(f"[web_search] Executed search: {query}")
            return {
                "success": True,
                "query": query,
                "message": "Web search executed (placeholder)"
            }
        
        except Exception as e:
            logger.error(f"[web_search] Failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _tool_git_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Git command tool"""
        command = params.get("command", "")
        cwd = params.get("cwd", ".")
        
        try:
            # Security: only allow specific safe git commands from config
            safe_commands = SAFE_GIT_COMMANDS
            
            cmd_parts = command.split()
            if not cmd_parts or cmd_parts[0] != "git":
                logger.error("[git_command] Command must start with 'git'")
                return {"success": False, "error": "Command must start with 'git'"}
            
            if len(cmd_parts) < 2 or cmd_parts[1] not in safe_commands:
                logger.error(f"[git_command] Command not allowed: {cmd_parts[1]}")
                return {
                    "success": False,
                    "error": f"Git command not allowed. Allowed: {safe_commands}"
                }
            
            # Execute command
            result = subprocess.run(
                command.split(),
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            success = result.returncode == 0
            if success:
                logger.info(f"[git_command] ✓ Executed: {command}")
            else:
                logger.warning(f"[git_command] Failed: {command} (code {result.returncode})")
            
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        
        except Exception as e:
            logger.error(f"[git_command] Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _tool_github_api(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """GitHub API tool"""
        endpoint = params.get("endpoint", "")
        method = params.get("method", "GET").upper()
        data = params.get("data")
        
        try:
            base_url = "https://api.github.com"
            url = f"{base_url}/{endpoint.lstrip('/')}"
            
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AutonomousAgent/1.0"
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
                    success = response.status < 400
                    
                    if success:
                        logger.info(f"[github_api] ✓ {method} {endpoint}")
                    else:
                        logger.warning(f"[github_api] Failed: {method} {endpoint} (status {response.status})")
                    
                    return {
                        "success": success,
                        "status": response.status,
                        "data": result
                    }
        
        except Exception as e:
            logger.error(f"[github_api] Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _tool_shell_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Shell command tool (SECURITY RISK - disabled by default)"""
        if not self.enable_shell:
            logger.warning("[shell_command] Tool is disabled for security")
            return {"success": False, "error": "Shell command tool is disabled for security"}
        
        command = params.get("command", "")
        cwd = params.get("cwd", ".")
        
        try:
            # Security: block dangerous commands from config
            dangerous_patterns = DANGEROUS_SHELL_PATTERNS
            
            if any(pattern in command for pattern in dangerous_patterns):
                logger.error(f"[shell_command] Dangerous pattern detected in: {command}")
                return {"success": False, "error": "Command contains dangerous patterns"}
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            success = result.returncode == 0
            if success:
                logger.info(f"[shell_command] ✓ Executed: {command}")
            else:
                logger.warning(f"[shell_command] Failed: {command} (code {result.returncode})")
            
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        
        except Exception as e:
            logger.error(f"[shell_command] Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _tool_file_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new file"""
        relative_path = params.get("path", "")
        content = params.get("content", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            logger.error(f"[file_create] Path validation failed: {error}")
            return {"success": False, "error": error}
        
        try:
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists
            if full_path.exists():
                error_msg = f"File already exists: {relative_path}"
                logger.warning(f"[file_create] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Write file
            full_path.write_text(content, encoding="utf-8")
            
            logger.info(f"[file_create] ✓ Created file: {relative_path} ({len(content)} bytes)")
            return {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "size": len(content),
                "message": f"File created successfully: {relative_path}"
            }
            
        except Exception as e:
            logger.error(f"[file_create] Failed to create file: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to create file: {e}"}
    
    async def _tool_file_edit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Edit an existing file"""
        relative_path = params.get("path", "")
        content = params.get("content", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            logger.error(f"[file_edit] Path validation failed: {error}")
            return {"success": False, "error": error}
        
        try:
            # Check if file exists
            if not full_path.exists():
                error_msg = f"File does not exist: {relative_path}"
                logger.warning(f"[file_edit] {error_msg}")
                return {"success": False, "error": error_msg}
            
            if not full_path.is_file():
                error_msg = f"Path is not a file: {relative_path}"
                logger.warning(f"[file_edit] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Backup old content
            old_content = full_path.read_text(encoding="utf-8")
            
            # Write new content
            full_path.write_text(content, encoding="utf-8")
            
            logger.info(f"[file_edit] ✓ Edited file: {relative_path} ({len(old_content)} → {len(content)} bytes)")
            return {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "old_size": len(old_content),
                "new_size": len(content),
                "message": f"File edited successfully: {relative_path}"
            }
            
        except Exception as e:
            logger.error(f"[file_edit] Failed to edit file: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to edit file: {e}"}
    
    async def _tool_file_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a file"""
        relative_path = params.get("path", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            logger.error(f"[file_delete] Path validation failed: {error}")
            return {"success": False, "error": error}
        
        try:
            # Check if file exists
            if not full_path.exists():
                error_msg = f"File does not exist: {relative_path}"
                logger.warning(f"[file_delete] {error_msg}")
                return {"success": False, "error": error_msg}
            
            if not full_path.is_file():
                error_msg = f"Path is not a file: {relative_path}"
                logger.warning(f"[file_delete] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Delete file
            full_path.unlink()
            
            logger.info(f"[file_delete] ✓ Deleted file: {relative_path}")
            return {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "message": f"File deleted successfully: {relative_path}"
            }
            
        except Exception as e:
            logger.error(f"[file_delete] Failed to delete file: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to delete file: {e}"}
    
    async def _tool_file_move(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Move/rename a file"""
        source_path = params.get("source", "")
        dest_path = params.get("destination", "")
        
        # Validate source path
        is_valid, full_source, error = self._validate_safe_path(source_path)
        if not is_valid:
            logger.error(f"[file_move] Invalid source: {error}")
            return {"success": False, "error": f"Invalid source: {error}"}
        
        # Validate destination path
        is_valid, full_dest, error = self._validate_safe_path(dest_path)
        if not is_valid:
            logger.error(f"[file_move] Invalid destination: {error}")
            return {"success": False, "error": f"Invalid destination: {error}"}
        
        try:
            # Check if source exists
            if not full_source.exists():
                error_msg = f"Source file does not exist: {source_path}"
                logger.warning(f"[file_move] {error_msg}")
                return {"success": False, "error": error_msg}
            
            if not full_source.is_file():
                error_msg = f"Source is not a file: {source_path}"
                logger.warning(f"[file_move] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Check if destination already exists
            if full_dest.exists():
                error_msg = f"Destination already exists: {dest_path}"
                logger.warning(f"[file_move] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Create parent directories if needed
            full_dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            full_source.rename(full_dest)
            
            logger.info(f"[file_move] ✓ Moved file: {source_path} → {dest_path}")
            return {
                "success": True,
                "source": source_path,
                "destination": dest_path,
                "full_source": str(full_source),
                "full_destination": str(full_dest),
                "message": f"File moved successfully: {source_path} → {dest_path}"
            }
            
        except Exception as e:
            logger.error(f"[file_move] Failed to move file: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to move file: {e}"}
    
    async def _tool_folder_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new folder"""
        relative_path = params.get("path", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            logger.error(f"[folder_create] Path validation failed: {error}")
            return {"success": False, "error": error}
        
        try:
            # Check if already exists
            if full_path.exists():
                if full_path.is_dir():
                    error_msg = f"Folder already exists: {relative_path}"
                    logger.warning(f"[folder_create] {error_msg}")
                    return {"success": False, "error": error_msg}
                else:
                    error_msg = f"Path exists but is not a folder: {relative_path}"
                    logger.warning(f"[folder_create] {error_msg}")
                    return {"success": False, "error": error_msg}
            
            # Create folder
            full_path.mkdir(parents=True, exist_ok=False)
            
            logger.info(f"[folder_create] ✓ Created folder: {relative_path}")
            return {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "message": f"Folder created successfully: {relative_path}"
            }
            
        except Exception as e:
            logger.error(f"[folder_create] Failed to create folder: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to create folder: {e}"}
    
    async def _tool_folder_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a folder and its contents"""
        import shutil
        
        relative_path = params.get("path", "")
        
        # Validate path
        is_valid, full_path, error = self._validate_safe_path(relative_path)
        if not is_valid:
            logger.error(f"[folder_delete] Path validation failed: {error}")
            return {"success": False, "error": error}
        
        try:
            # Check if exists
            if not full_path.exists():
                error_msg = f"Folder does not exist: {relative_path}"
                logger.warning(f"[folder_delete] {error_msg}")
                return {"success": False, "error": error_msg}
            
            if not full_path.is_dir():
                error_msg = f"Path is not a folder: {relative_path}"
                logger.warning(f"[folder_delete] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Prevent deleting KB root itself
            if full_path == self.kb_root_path:
                error_msg = "Cannot delete knowledge base root folder"
                logger.error(f"[folder_delete] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Delete folder and contents
            shutil.rmtree(full_path)
            
            logger.info(f"[folder_delete] ✓ Deleted folder: {relative_path}")
            return {
                "success": True,
                "path": relative_path,
                "full_path": str(full_path),
                "message": f"Folder deleted successfully: {relative_path}"
            }
            
        except Exception as e:
            logger.error(f"[folder_delete] Failed to delete folder: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to delete folder: {e}"}
    
    async def _tool_folder_move(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Move/rename a folder"""
        import shutil
        
        source_path = params.get("source", "")
        dest_path = params.get("destination", "")
        
        # Validate source path
        is_valid, full_source, error = self._validate_safe_path(source_path)
        if not is_valid:
            logger.error(f"[folder_move] Invalid source: {error}")
            return {"success": False, "error": f"Invalid source: {error}"}
        
        # Validate destination path
        is_valid, full_dest, error = self._validate_safe_path(dest_path)
        if not is_valid:
            logger.error(f"[folder_move] Invalid destination: {error}")
            return {"success": False, "error": f"Invalid destination: {error}"}
        
        try:
            # Check if source exists
            if not full_source.exists():
                error_msg = f"Source folder does not exist: {source_path}"
                logger.warning(f"[folder_move] {error_msg}")
                return {"success": False, "error": error_msg}
            
            if not full_source.is_dir():
                error_msg = f"Source is not a folder: {source_path}"
                logger.warning(f"[folder_move] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Prevent moving KB root itself
            if full_source == self.kb_root_path:
                error_msg = "Cannot move knowledge base root folder"
                logger.error(f"[folder_move] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Check if destination already exists
            if full_dest.exists():
                error_msg = f"Destination already exists: {dest_path}"
                logger.warning(f"[folder_move] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Create parent directories if needed
            full_dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Move folder
            shutil.move(str(full_source), str(full_dest))
            
            logger.info(f"[folder_move] ✓ Moved folder: {source_path} → {dest_path}")
            return {
                "success": True,
                "source": source_path,
                "destination": dest_path,
                "full_source": str(full_source),
                "full_destination": str(full_dest),
                "message": f"Folder moved successfully: {source_path} → {dest_path}"
            }
            
        except Exception as e:
            logger.error(f"[folder_move] Failed to move folder: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to move folder: {e}"}
    
    # ====================================================================
    # BACKWARD COMPATIBILITY METHODS (from QwenCodeAgent)
    # ====================================================================
    
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
