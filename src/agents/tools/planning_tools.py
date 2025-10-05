"""
Planning tools for autonomous agent.

Tools for creating TODO plans and analyzing content.
Each tool is self-contained with its own metadata and implementation.
"""

from typing import Any, Dict
from loguru import logger

from .base_tool import BaseTool, ToolContext


class PlanTodoTool(BaseTool):
    """Tool for creating TODO plans"""
    
    @property
    def name(self) -> str:
        return "plan_todo"
    
    @property
    def description(self) -> str:
        return "Создать план действий (TODO список). ОБЯЗАТЕЛЬНО вызови первым!"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Список задач для выполнения",
                }
            },
            "required": ["tasks"],
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Handle plan_todo tool call"""
        tasks = params.get("tasks", [])
        
        logger.info(f"[plan_todo] Creating plan with {len(tasks)} tasks")
        
        # Create plan
        from ..autonomous_agent import TodoPlan
        new_plan = TodoPlan()
        for i, task in enumerate(tasks):
            new_plan.add_task(task, priority=i+1)
        
        # Update current plan via callback
        if context.set_current_plan:
            context.set_current_plan(new_plan)
        
        return {
            "success": True,
            "plan": tasks,
            "message": f"Plan created with {len(tasks)} tasks"
        }


class AnalyzeContentTool(BaseTool):
    """Tool for analyzing content and extracting key information"""
    
    @property
    def name(self) -> str:
        return "analyze_content"
    
    @property
    def description(self) -> str:
        return "Анализировать контент и извлечь ключевую информацию"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Текст для анализа"}
            },
            "required": ["text"],
        }
    
    async def execute(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Analyze content"""
        text = params.get("text", "")
        
        analysis = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "has_code": "```" in text or "def " in text or "function " in text,
            "keywords": context.base_agent_class.extract_keywords(text),
            "category": context.base_agent_class.detect_category(text)
        }
        
        return analysis


# Export all planning tools
ALL_TOOLS = [
    PlanTodoTool(),
    AnalyzeContentTool(),
]
