"""
Bot utility functions
"""

from typing import List


def is_user_allowed(user_id: int, allowed_ids: List[int]) -> bool:
    """
    Check if user is allowed to use the bot

    Args:
        user_id: Telegram user ID
        allowed_ids: List of allowed user IDs

    Returns:
        True if user is allowed, False otherwise
    """
    return user_id in allowed_ids


def format_status_message(status: str, details: str = "") -> str:
    """
    Format status message for user

    Args:
        status: Status type (processing, completed, error)
        details: Additional details

    Returns:
        Formatted status message
    """
    status_emoji = {"processing": "⏳", "completed": "✅", "error": "❌"}

    emoji = status_emoji.get(status, "ℹ️")
    message = f"{emoji} {status.capitalize()}"

    if details:
        message += f"\n{details}"

    return message
