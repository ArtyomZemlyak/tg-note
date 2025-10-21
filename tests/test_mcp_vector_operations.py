"""
Tests for MCP Vector Operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.bot.mcp_vector_operations import MCPVectorOperations
from src.bot.mcp_hub_client import MCPHubError, MCPHubUnavailableError


class TestMCPVectorOperations:
    """Test cases for MCPVectorOperations"""

    @pytest.fixture
    def mock_mcp_client(self):
        """Create a mock MCP Hub client"""
        return AsyncMock()

    @pytest.fixture
    def operations(self, mock_mcp_client):
        """Create MCPVectorOperations instance with mock client"""
        return MCPVectorOperations(mock_mcp_client)

    @pytest.mark.asyncio
    async def test_reindex_documents_success(self, operations, mock_mcp_client):
        """Test successful reindex operation"""
        mock_mcp_client.vector_reindex.return_value = {"success": True, "message": "Success"}

        result = await operations.reindex_documents(
            documents=[{"id": "doc1", "content": "content1"}],
            force=True,
            kb_id="test_kb",
            user_id=123
        )

        assert result is True
        mock_mcp_client.vector_reindex.assert_called_once_with(
            documents=[{"id": "doc1", "content": "content1"}],
            force=True,
            kb_id="test_kb",
            user_id=123
        )

    @pytest.mark.asyncio
    async def test_reindex_documents_failure(self, operations, mock_mcp_client):
        """Test failed reindex operation"""
        mock_mcp_client.vector_reindex.return_value = {"success": False, "error": "Test error"}

        result = await operations.reindex_documents(
            documents=[{"id": "doc1", "content": "content1"}]
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_reindex_documents_mcp_hub_unavailable(self, operations, mock_mcp_client):
        """Test reindex operation when MCP Hub is unavailable"""
        mock_mcp_client.vector_reindex.side_effect = MCPHubUnavailableError("Service unavailable")

        result = await operations.reindex_documents(
            documents=[{"id": "doc1", "content": "content1"}]
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_reindex_documents_mcp_hub_error(self, operations, mock_mcp_client):
        """Test reindex operation with MCP Hub error"""
        mock_mcp_client.vector_reindex.side_effect = MCPHubError("MCP error")

        result = await operations.reindex_documents(
            documents=[{"id": "doc1", "content": "content1"}]
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_reindex_documents_exception(self, operations, mock_mcp_client):
        """Test reindex operation with unexpected exception"""
        mock_mcp_client.vector_reindex.side_effect = Exception("Unexpected error")

        result = await operations.reindex_documents(
            documents=[{"id": "doc1", "content": "content1"}]
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_add_documents_success(self, operations, mock_mcp_client):
        """Test successful add documents operation"""
        mock_mcp_client.vector_add_documents.return_value = {"success": True, "message": "Added"}

        result = await operations.add_documents(
            documents=[{"id": "doc1", "content": "content1"}],
            kb_id="test_kb",
            user_id=123
        )

        assert result is True
        mock_mcp_client.vector_add_documents.assert_called_once_with(
            documents=[{"id": "doc1", "content": "content1"}],
            kb_id="test_kb",
            user_id=123
        )

    @pytest.mark.asyncio
    async def test_add_documents_failure(self, operations, mock_mcp_client):
        """Test failed add documents operation"""
        mock_mcp_client.vector_add_documents.return_value = {"success": False, "error": "Test error"}

        result = await operations.add_documents(
            documents=[{"id": "doc1", "content": "content1"}]
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_documents_success(self, operations, mock_mcp_client):
        """Test successful delete documents operation"""
        mock_mcp_client.vector_delete_documents.return_value = {"success": True, "message": "Deleted"}

        result = await operations.delete_documents(
            document_ids=["doc1", "doc2"],
            kb_id="test_kb",
            user_id=123
        )

        assert result is True
        mock_mcp_client.vector_delete_documents.assert_called_once_with(
            document_ids=["doc1", "doc2"],
            kb_id="test_kb",
            user_id=123
        )

    @pytest.mark.asyncio
    async def test_delete_documents_failure(self, operations, mock_mcp_client):
        """Test failed delete documents operation"""
        mock_mcp_client.vector_delete_documents.return_value = {"success": False, "error": "Test error"}

        result = await operations.delete_documents(
            document_ids=["doc1", "doc2"]
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_documents_success(self, operations, mock_mcp_client):
        """Test successful update documents operation"""
        mock_mcp_client.vector_update_documents.return_value = {"success": True, "message": "Updated"}

        result = await operations.update_documents(
            documents=[{"id": "doc1", "content": "content1"}],
            kb_id="test_kb",
            user_id=123
        )

        assert result is True
        mock_mcp_client.vector_update_documents.assert_called_once_with(
            documents=[{"id": "doc1", "content": "content1"}],
            kb_id="test_kb",
            user_id=123
        )

    @pytest.mark.asyncio
    async def test_update_documents_failure(self, operations, mock_mcp_client):
        """Test failed update documents operation"""
        mock_mcp_client.vector_update_documents.return_value = {"success": False, "error": "Test error"}

        result = await operations.update_documents(
            documents=[{"id": "doc1", "content": "content1"}]
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_availability_success(self, operations, mock_mcp_client):
        """Test successful availability check"""
        mock_mcp_client.health_check.return_value = {
            "builtin_tools": {
                "names": ["vector_search", "other_tool"]
            }
        }

        result = await operations.check_availability()

        assert result is True
        mock_mcp_client.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_availability_missing_tool(self, operations, mock_mcp_client):
        """Test availability check when vector_search tool is missing"""
        mock_mcp_client.health_check.return_value = {
            "builtin_tools": {
                "names": ["other_tool"]
            }
        }

        result = await operations.check_availability()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_availability_no_tools(self, operations, mock_mcp_client):
        """Test availability check when no tools are available"""
        mock_mcp_client.health_check.return_value = {
            "builtin_tools": {
                "names": []
            }
        }

        result = await operations.check_availability()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_availability_exception(self, operations, mock_mcp_client):
        """Test availability check with exception"""
        mock_mcp_client.health_check.side_effect = Exception("Test error")

        result = await operations.check_availability()

        assert result is False

    @pytest.mark.asyncio
    async def test_all_operations_with_defaults(self, operations, mock_mcp_client):
        """Test all operations with default parameters"""
        # Mock all operations to return success
        mock_mcp_client.vector_reindex.return_value = {"success": True}
        mock_mcp_client.vector_add_documents.return_value = {"success": True}
        mock_mcp_client.vector_delete_documents.return_value = {"success": True}
        mock_mcp_client.vector_update_documents.return_value = {"success": True}

        # Test with default parameters
        result1 = await operations.reindex_documents([{"id": "doc1", "content": "content1"}])
        result2 = await operations.add_documents([{"id": "doc1", "content": "content1"}])
        result3 = await operations.delete_documents(["doc1"])
        result4 = await operations.update_documents([{"id": "doc1", "content": "content1"}])

        assert all([result1, result2, result3, result4])

        # Verify default parameters were used
        mock_mcp_client.vector_reindex.assert_called_with(
            documents=[{"id": "doc1", "content": "content1"}],
            force=False,
            kb_id="default",
            user_id=None
        )
        mock_mcp_client.vector_add_documents.assert_called_with(
            documents=[{"id": "doc1", "content": "content1"}],
            kb_id="default",
            user_id=None
        )
        mock_mcp_client.vector_delete_documents.assert_called_with(
            document_ids=["doc1"],
            kb_id="default",
            user_id=None
        )
        mock_mcp_client.vector_update_documents.assert_called_with(
            documents=[{"id": "doc1", "content": "content1"}],
            kb_id="default",
            user_id=None
        )