from typing import Optional, Union

from loguru import logger
from openai import OpenAI
from pydantic import BaseModel

from config.settings import (
    MEM_AGENT_BASE_URL,
    MEM_AGENT_MODEL,
    MEM_AGENT_OPENAI_API_KEY,
    OPENROUTER_API_KEY,
)
from src.core.log_utils import truncate_for_log
from src.mcp.memory.mem_agent_impl.schemas import ChatMessage, Role


def create_openai_client() -> OpenAI:
    """Create a new OpenAI-compatible client instance.

    Priority:
    1) Explicit mem-agent endpoint (MEM_AGENT_BASE_URL, MEM_AGENT_OPENAI_API_KEY)
    2) Legacy OpenRouter endpoint (if OPENROUTER_API_KEY is set)
    """
    base_url = MEM_AGENT_BASE_URL
    api_key = MEM_AGENT_OPENAI_API_KEY or OPENROUTER_API_KEY

    logger.debug("🔧 Creating OpenAI-compatible client")
    logger.debug(f"  Base URL: {base_url or 'default'}")
    logger.debug(f"  API key: {'set' if api_key else 'not set'}")

    return OpenAI(api_key=api_key, base_url=base_url)


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
    model: str = MEM_AGENT_MODEL,
    client: Optional[OpenAI] = None,
) -> Union[str, BaseModel]:
    """
    Get a response from a model using OpenAI-compatible endpoint.

    Args:
        messages: A list of ChatMessage objects (optional).
        message: A single message string (optional).
        system_prompt: A system prompt for the model (optional).
        model: The model to use.
        schema: A Pydantic BaseModel for structured output (optional).
        client: Optional OpenAI client to use. If None, uses the global client.

    Returns:
        A string response from the model if schema is None, otherwise a BaseModel object.
    """
    if messages is None and message is None:
        raise ValueError("Either 'messages' or 'message' must be provided.")

    logger.debug("=" * 60)
    logger.debug("🧠 GET_MODEL_RESPONSE called")
    logger.debug(f"  Model: {model}")
    logger.debug(f"  Backend: OpenAI-compatible")

    # Use provided client or create a new one
    if client is None:
        logger.debug("  No client provided, creating new one...")
        client = create_openai_client()

    # Build message history
    if messages is None:
        logger.debug(f"  Building message history from single message")
        messages = []
        if system_prompt:
            messages.append(_as_dict(ChatMessage(role=Role.SYSTEM, content=system_prompt)))
        messages.append(_as_dict(ChatMessage(role=Role.USER, content=message)))
    else:
        logger.debug(f"  Using provided message history: {len(messages)} messages")
        messages = [_as_dict(m) for m in messages]

    # Calculate total tokens (rough estimate)
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    logger.debug(f"  Total message characters: {total_chars}")
    logger.debug("=" * 60)

    try:
        logger.info("📤 Sending request to model...")
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            # stop=["</reply>", "</python>"]
        )

        response_content = completion.choices[0].message.content
        logger.info(f"✅ Model response received: {len(response_content)} chars")
        logger.debug(f"  Response preview: {response_content[:50]}...")

        return response_content

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Error getting model response: {e}")
        logger.error(f"  Model: {model}")
        logger.error(f"  Backend: OpenAI-compatible")
        logger.error("=" * 60, exc_info=True)
        raise
