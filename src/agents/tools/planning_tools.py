"""
Planning tools for autonomous agent
Handles plan creation and content analysis
"""

from typing import Any, Dict
from loguru import logger


async def tool_plan_todo(
    params: Dict[str, Any],
    current_plan: Any,
    base_agent_class: Any
) -> Dict[str, Any]:
    """
    Handle plan_todo tool call
    
    Args:
        params: Tool parameters
        current_plan: Current todo plan object
        base_agent_class: BaseAgent class for helper methods
        
    Returns:
        Dict with success status and plan information
    """
    tasks = params.get("tasks", [])
    
    logger.info(f"[plan_todo] Creating plan with {len(tasks)} tasks")
    
    # Create plan
    from ..autonomous_agent import TodoPlan
    new_plan = TodoPlan()
    for i, task in enumerate(tasks):
        new_plan.add_task(task, priority=i+1)
    
    return {
        "success": True,
        "plan": tasks,
        "message": f"Plan created with {len(tasks)} tasks"
    }, new_plan


async def tool_analyze_content(
    params: Dict[str, Any],
    base_agent_class: Any
) -> Dict[str, Any]:
    """
    Analyze content tool
    
    Args:
        params: Tool parameters with 'text' field
        base_agent_class: BaseAgent class for helper methods
        
    Returns:
        Dict with content analysis results
    """
    text = params.get("text", "")
    
    analysis = {
        "text_length": len(text),
        "word_count": len(text.split()),
        "has_code": "```" in text or "def " in text or "function " in text,
        "keywords": base_agent_class.extract_keywords(text),
        "category": base_agent_class.detect_category(text)
    }
    
    return analysis
