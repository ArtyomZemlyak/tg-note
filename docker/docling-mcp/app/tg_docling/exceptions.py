"""
Exception classes for tg_docling MCP tools.
"""

from mcp.types import ErrorData


class McpError(Exception):
    """
    Exception raised for MCP-related errors.

    This exception wraps MCP ErrorData to provide structured error information.
    """

    def __init__(self, error_data: ErrorData) -> None:
        """
        Initialize McpError with MCP ErrorData.

        Args:
            error_data: The MCP ErrorData object containing error details.
        """
        self.error_data = error_data
        super().__init__(error_data.message)
