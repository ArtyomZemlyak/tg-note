"""
Agent System
Analyzes and processes content using AI agents
"""

from .base_agent import BaseAgent, KBStructure
from .stub_agent import StubAgent
from .autonomous_agent import (
    AutonomousAgent,
    ActionType,
    AgentContext,
    AgentDecision,
    ToolExecution,
    AutonomousAgentResult,
    TodoPlan
)
from .qwen_code_cli_agent import QwenCodeCLIAgent
from .agent_factory import AgentFactory
from .llm_connectors import BaseLLMConnector, LLMResponse, OpenAIConnector

# Backward compatibility aliases
QwenCodeAgent = AutonomousAgent

__all__ = [
    'BaseAgent',
    'KBStructure',
    'StubAgent',
    'AutonomousAgent',
    'ActionType',
    'AgentContext',
    'AgentDecision',
    'ToolExecution',
    'AutonomousAgentResult',
    'TodoPlan',
    'QwenCodeCLIAgent',
    'AgentFactory',
    'BaseLLMConnector',
    'LLMResponse',
    'OpenAIConnector',
    # Backward compatibility
    'QwenCodeAgent',
]