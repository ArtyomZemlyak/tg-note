"""
Agent System
Analyzes and processes content using AI agents
"""

from .agent_factory import AgentFactory
from .autonomous_agent import (
    ActionType,
    AgentContext,
    AgentDecision,
    AutonomousAgent,
    AutonomousAgentResult,
    TodoPlan,
    ToolExecution,
)
from .base_agent import BaseAgent, KBStructure
from .llm_connectors import BaseLLMConnector, LLMResponse, OpenAIConnector
from .qwen_code_cli_agent import QwenCodeCLIAgent
from .stub_agent import StubAgent

# Backward compatibility aliases
QwenCodeAgent = AutonomousAgent

__all__ = [
    "BaseAgent",
    "KBStructure",
    "StubAgent",
    "AutonomousAgent",
    "ActionType",
    "AgentContext",
    "AgentDecision",
    "ToolExecution",
    "AutonomousAgentResult",
    "TodoPlan",
    "QwenCodeCLIAgent",
    "AgentFactory",
    "BaseLLMConnector",
    "LLMResponse",
    "OpenAIConnector",
    # Backward compatibility
    "QwenCodeAgent",
]
