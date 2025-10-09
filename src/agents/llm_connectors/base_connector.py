"""
Base LLM Connector
Abstract interface for LLM API calls
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class LLMResponse:
    """Unified response from LLM"""

    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: str = "stop"
    raw_response: Optional[Any] = None

    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls"""
        return self.tool_calls is not None and len(self.tool_calls) > 0


class BaseLLMConnector(ABC):
    """
    Base class for LLM connectors

    All LLM providers should implement this interface to ensure
    unified interaction with autonomous agents
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize connector

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        logger.info(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Make a chat completion request

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions (OpenAI function calling format)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with content and/or tool calls
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the model name being used

        Returns:
            Model name string
        """
        pass

    def validate_tools_schema(self, tools: List[Dict[str, Any]]) -> bool:
        """
        Validate tools schema format

        Args:
            tools: List of tool definitions

        Returns:
            True if valid
        """
        if not tools:
            return True

        for tool in tools:
            if "type" not in tool or "function" not in tool:
                return False

            func = tool["function"]
            if "name" not in func or "parameters" not in func:
                return False

        return True
