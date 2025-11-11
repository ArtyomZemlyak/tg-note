"""
Logging utilities for truncating large content in log messages.
"""

import json
from typing import Any, Dict, List, Union


def truncate_for_log(data: Any, max_length: int = 50) -> Any:
    """
    Truncate content length in data for logging to avoid flooding logs with large payloads.

    This function recursively processes dictionaries, lists, and strings to ensure
    that string values don't exceed the specified maximum length.

    Args:
        data: Data to truncate (dict, list, str, or other)
        max_length: Maximum length for string values (default: 50 chars)

    Returns:
        Data with truncated content lengths

    Examples:
        >>> truncate_for_log("short")
        'short'
        >>> truncate_for_log("a" * 100, max_length=50)
        'aaaaa... (truncated, total: 100 chars)'
        >>> truncate_for_log({"content": "a" * 100}, max_length=50)
        {'content': 'aaaaa... (truncated, total: 100 chars)'}
    """
    if isinstance(data, dict):
        truncated = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > max_length:
                truncated[key] = f"{value[:max_length]}... (truncated, total: {len(value)} chars)"
            elif isinstance(value, (dict, list)):
                truncated[key] = truncate_for_log(value, max_length)
            else:
                truncated[key] = value
        return truncated
    elif isinstance(data, list):
        return [truncate_for_log(item, max_length) for item in data]
    elif isinstance(data, str) and len(data) > max_length:
        return f"{data[:max_length]}... (truncated, total: {len(data)} chars)"
    else:
        return data


def format_for_log(
    data: Any, max_length: int = 50, as_json: bool = True, indent: int = 2
) -> Union[str, Any]:
    """
    Format data for logging with content truncation.

    Args:
        data: Data to format
        max_length: Maximum length for string values (default: 50 chars)
        as_json: If True, return JSON string; if False, return truncated data
        indent: JSON indentation (default: 2)

    Returns:
        JSON string if as_json=True, otherwise truncated data

    Examples:
        >>> format_for_log({"content": "a" * 100}, max_length=50)
        '{\n  "content": "aaaaa... (truncated, total: 100 chars)"\n}'
        >>> format_for_log({"content": "short"}, as_json=False)
        {'content': 'short'}
    """
    truncated = truncate_for_log(data, max_length)
    if as_json:
        return json.dumps(truncated, ensure_ascii=False, indent=indent)
    return truncated
