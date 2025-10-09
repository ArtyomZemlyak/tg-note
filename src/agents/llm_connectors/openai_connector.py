"""
OpenAI API Connector
Connector for OpenAI-compatible APIs (OpenAI, Qwen, etc.)
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai package not installed. OpenAIConnector will not work.")

from .base_connector import BaseLLMConnector, LLMResponse


class OpenAIConnector(BaseLLMConnector):
    """
    Connector for OpenAI-compatible APIs

    Supports:
    - OpenAI API
    - Qwen API (OpenAI-compatible)
    - OpenRouter
    - Any other OpenAI-compatible endpoint
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        config: Optional[Dict] = None,
    ):
        """
        Initialize OpenAI connector

        Args:
            api_key: API key for authentication
            base_url: Base URL for API (for compatible APIs)
            model: Model name to use
            config: Additional configuration
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required for OpenAIConnector. "
                "Install with: pip install openai"
            )

        super().__init__(config)

        self.api_key = api_key
        self.base_url = base_url
        self.model = model

        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        logger.info(
            f"OpenAIConnector initialized: model={model}, " f"base_url={base_url or 'default'}"
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Make a chat completion request using OpenAI API

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for OpenAI API

        Returns:
            LLMResponse with content and/or tool calls
        """
        try:
            # Validate tools if provided
            if tools and not self.validate_tools_schema(tools):
                logger.warning("[OpenAIConnector] Invalid tools schema")
                tools = None

            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                api_params["max_tokens"] = max_tokens

            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = kwargs.pop("tool_choice", "auto")

            # Add any additional kwargs
            api_params.update(kwargs)

            logger.debug(
                f"[OpenAIConnector] Calling API: model={self.model}, "
                f"messages={len(messages)}, tools={len(tools) if tools else 0}"
            )

            # Make API call
            response = await self.client.chat.completions.create(**api_params)

            # Parse response
            message = response.choices[0].message

            # Extract tool calls if present
            tool_calls_list = None
            if message.tool_calls:
                tool_calls_list = []
                for tool_call in message.tool_calls:
                    tool_calls_list.append(
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": json.loads(tool_call.function.arguments),
                            },
                        }
                    )

            llm_response = LLMResponse(
                content=message.content,
                tool_calls=tool_calls_list,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response,
            )

            if tool_calls_list:
                logger.debug(f"[OpenAIConnector] Received {len(tool_calls_list)} tool call(s)")
            else:
                logger.debug(
                    f"[OpenAIConnector] Received text response: "
                    f"{len(message.content) if message.content else 0} chars"
                )

            return llm_response

        except Exception as e:
            logger.error(f"[OpenAIConnector] API call failed: {e}", exc_info=True)
            raise

    def get_model_name(self) -> str:
        """
        Get the model name being used

        Returns:
            Model name string
        """
        return self.model
