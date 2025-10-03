"""
Autonomous Agent
Автономный агент с циклом планирования и вызовом тулзов
"""

import json
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .base_agent import AgentResult as BaseAgentResult, BaseAgent, KBStructure


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


class AutonomousAgent(BaseAgent):
    """
    Автономный агент с циклом планирования
    
    Агент работает в цикле:
    1. Анализирует текущее состояние
    2. Принимает решение (вызвать тулз или завершить)
    3. Выполняет действие
    4. Обновляет контекст
    5. Повторяет до завершения задачи
    """
    
    def __init__(
        self,
        config: Optional[Dict] = None,
        instruction: Optional[str] = None,
        max_iterations: int = 10
    ):
        """
        Initialize autonomous agent
        
        Args:
            config: Configuration dictionary
            instruction: Agent instruction
            max_iterations: Maximum iterations in agent loop
        """
        super().__init__(config)
        self.instruction = instruction or self._get_default_instruction()
        self.max_iterations = max_iterations
        self.tools: Dict[str, callable] = {}
        
        logger.info(f"AutonomousAgent initialized with max_iterations={max_iterations}")
    
    def _get_default_instruction(self) -> str:
        """Get default instruction for the agent"""
        return """Ты автономный агент для обработки и сохранения информации в базу знаний.

Твоя задача:
1. Проанализировать предоставленный контент
2. Составить план действий
3. Использовать доступные тулзы для выполнения плана
4. Сохранить информацию в структурированном виде

Доступные тулзы:
- web_search: Поиск информации в интернете
- file_create: Создать файл в базе знаний
- file_edit: Редактировать файл
- folder_create: Создать папку
- analyze_content: Анализировать контент

Работай автономно, не задавай вопросов пользователю.
Когда задача выполнена, верни результат с action: "END".
"""
    
    def register_tool(self, name: str, handler: callable) -> None:
        """
        Зарегистрировать тулз
        
        Args:
            name: Название тулза
            handler: Функция-обработчик
        """
        self.tools[name] = handler
        logger.info(f"Registered tool: {name}")
    
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
            AgentResult with final output
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
    
    @abstractmethod
    async def _make_decision(self, context: AgentContext) -> AgentDecision:
        """
        Принять решение о следующем действии
        
        ВАЖНО: Это абстрактный метод - каждая реализация агента
        должна определить, как LLM принимает решения
        
        Args:
            context: Current agent context
        
        Returns:
            AgentDecision with next action
        """
        pass
    
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
            
            logger.debug(f"[AutonomousAgent] Tool {tool_name} executed successfully")
            
            return ToolExecution(
                tool_name=tool_name,
                params=params,
                result=result,
                success=True
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
            AgentResult
        """
        logger.info("[AutonomousAgent] Finalizing result")
        
        # Получить итоговый markdown
        if decision and decision.final_result:
            markdown = decision.final_result
        else:
            markdown = await self._generate_fallback_markdown(context)
        
        # Извлечь метаданные
        title = self._extract_title(markdown)
        kb_structure = await self._determine_kb_structure(markdown, context)
        
        metadata = {
            "agent": "AutonomousAgent",
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
    
    async def _determine_kb_structure(
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
        # Простая категоризация (можно улучшить)
        category = "general"
        tags = []
        
        # Попытка извлечь из markdown
        if "ai" in markdown.lower() or "machine learning" in markdown.lower():
            category = "ai"
        elif "tech" in markdown.lower() or "programming" in markdown.lower():
            category = "tech"
        
        return KBStructure(
            category=category,
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
