from typing import Optional, Union

from openai import OpenAI
from pydantic import BaseModel

from src.agents.mcp.memory.mem_agent_impl.schemas import ChatMessage, Role
from src.agents.mcp.memory.mem_agent_impl.settings import (
    MEM_AGENT_BASE_URL,
    MEM_AGENT_OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_STRONG_MODEL,
)


def create_openai_client() -> OpenAI:
    """Create a new OpenAI-compatible client instance.

    Priority:
    1) Explicit mem-agent endpoint (MEM_AGENT_BASE_URL, MEM_AGENT_OPENAI_API_KEY)
    2) Legacy OpenRouter endpoint
    """
    base_url = MEM_AGENT_BASE_URL or OPENROUTER_BASE_URL
    api_key = MEM_AGENT_OPENAI_API_KEY or OPENROUTER_API_KEY
    return OpenAI(api_key=api_key, base_url=base_url)


def create_vllm_client(host: str = "0.0.0.0", port: int = 8000) -> OpenAI:
    """Create a new vLLM client instance (OpenAI-compatible)."""
    return OpenAI(
        base_url=f"http://{host}:{port}/v1",
        api_key="EMPTY",
    )


def _as_dict(msg: Union[ChatMessage, dict]) -> dict:
    """
    Accept either ChatMessage or raw dict and return the raw dict.

    Args:
        msg: A ChatMessage object or a raw dict.

    Returns:
        A raw dict.
    """
    return msg if isinstance(msg, dict) else msg.model_dump()


def get_model_response(
    messages: Optional[list[ChatMessage]] = None,
    message: Optional[str] = None,
    system_prompt: Optional[str] = None,
    model: str = OPENROUTER_STRONG_MODEL,
    client: Optional[OpenAI] = None,
    use_vllm: bool = False,
) -> Union[str, BaseModel]:
    """
    Get a response from a model using OpenRouter or vLLM, with optional schema for structured output.

    Args:
        messages: A list of ChatMessage objects (optional).
        message: A single message string (optional).
        system_prompt: A system prompt for the model (optional).
        model: The model to use.
        schema: A Pydantic BaseModel for structured output (optional).
        client: Optional OpenAI client to use. If None, uses the global client.
        use_vllm: Whether to use vLLM backend instead of OpenRouter.

    Returns:
        A string response from the model if schema is None, otherwise a BaseModel object.
    """
    if messages is None and message is None:
        raise ValueError("Either 'messages' or 'message' must be provided.")

    # Use provided clients or fall back to global ones
    if client is None:
        if use_vllm:
            client = create_vllm_client()
        else:
            client = create_openai_client()

    # Build message history
    if messages is None:
        messages = []
        if system_prompt:
            messages.append(_as_dict(ChatMessage(role=Role.SYSTEM, content=system_prompt)))
        messages.append(_as_dict(ChatMessage(role=Role.USER, content=message)))
    else:
        messages = [_as_dict(m) for m in messages]

    if use_vllm:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            # stop=["</reply>", "</python>"]
        )

        return completion.choices[0].message.content
    else:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            # stop=["</reply>", "</python>"]
        )
        return completion.choices[0].message.content
