"""
Tests for MCP Hub Client improvements
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.mcp_hub_client import MCPHubClient, MCPHubError, MCPHubTimeoutError, MCPHubUnavailableError
from src.core.circuit_breaker import CircuitBreakerError


class TestMCPHubClientImprovements:
    """Test cases for MCP Hub Client improvements"""

    @pytest.fixture
    def client(self):
        """Create MCPHubClient instance for testing"""
        return MCPHubClient("http://test-hub:8765", timeout=5.0, retry_attempts=2, retry_delay=0.1)

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, client):
        """Test circuit breaker integration"""
        # Mock session and response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.text.return_value = "Service unavailable"
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            # First few calls should fail and open circuit
            for _ in range(6):  # More than failure threshold
                with pytest.raises(MCPHubUnavailableError):
                    await client._make_request("GET", "/test")

            # Next call should be blocked by circuit breaker
            with pytest.raises(MCPHubUnavailableError, match="Service temporarily unavailable"):
                await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_retry_logic_retryable_errors(self, client):
        """Test retry logic for retryable errors"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.text.return_value = "Service unavailable"
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(MCPHubUnavailableError):
                await client._make_request("GET", "/test")

            # Should have made multiple attempts
            assert mock_session.request.call_count == 2  # retry_attempts

    @pytest.mark.asyncio
    async def test_retry_logic_non_retryable_errors(self, client):
        """Test retry logic for non-retryable errors"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text.return_value = "Not found"
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(MCPHubError):
                await client._make_request("GET", "/test")

            # Should not retry for 404 errors
            assert mock_session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, client):
        """Test exponential backoff in retry logic"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.text.return_value = "Service unavailable"
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with patch('asyncio.sleep') as mock_sleep:
                with pytest.raises(MCPHubUnavailableError):
                    await client._make_request("GET", "/test")

                # Should have called sleep with exponential backoff
                assert mock_sleep.call_count == 1
                mock_sleep.assert_called_with(0.1)  # retry_delay * (2 ** 0)

    @pytest.mark.asyncio
    async def test_session_management(self, client):
        """Test session management and cleanup"""
        # Test session creation
        session1 = await client._get_session()
        assert session1 is not None

        # Test session reuse
        session2 = await client._get_session()
        assert session1 is session2

        # Test session recreation after close
        await session1.close()
        session3 = await client._get_session()
        assert session3 is not session1

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"status": "ok", "tools": ["vector_search"]}
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client.health_check()
            assert result == {"status": "ok", "tools": ["vector_search"]}

    @pytest.mark.asyncio
    async def test_vector_operations_success(self, client):
        """Test successful vector operations"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"success": True, "message": "Success"}
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            # Test reindex
            result = await client.vector_reindex(
                documents=[{"id": "doc1", "content": "content1"}],
                force=True,
                kb_id="test_kb",
                user_id=123
            )
            assert result == {"success": True, "message": "Success"}

            # Test add documents
            result = await client.vector_add_documents(
                documents=[{"id": "doc1", "content": "content1"}],
                kb_id="test_kb",
                user_id=123
            )
            assert result == {"success": True, "message": "Success"}

            # Test delete documents
            result = await client.vector_delete_documents(
                document_ids=["doc1", "doc2"],
                kb_id="test_kb",
                user_id=123
            )
            assert result == {"success": True, "message": "Success"}

            # Test update documents
            result = await client.vector_update_documents(
                documents=[{"id": "doc1", "content": "content1"}],
                kb_id="test_kb",
                user_id=123
            )
            assert result == {"success": True, "message": "Success"}

    @pytest.mark.asyncio
    async def test_error_handling_503(self, client):
        """Test error handling for 503 Service Unavailable"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 503
        mock_response.text.return_value = "Service unavailable"
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(MCPHubUnavailableError, match="Service unavailable"):
                await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_error_handling_404(self, client):
        """Test error handling for 404 Not Found"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text.return_value = "Not found"
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(MCPHubError, match="Endpoint not found"):
                await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_error_handling_timeout(self, client):
        """Test error handling for timeout"""
        mock_session = AsyncMock()
        mock_session.request.side_effect = asyncio.TimeoutError("Request timeout")

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(MCPHubTimeoutError, match="Request timeout"):
                await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_error_handling_client_error(self, client):
        """Test error handling for client errors"""
        mock_session = AsyncMock()
        mock_session.request.side_effect = Exception("Connection error")

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(MCPHubError, match="Unexpected error"):
                await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_json_decode_error(self, client):
        """Test error handling for JSON decode errors"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "Invalid JSON"
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            with pytest.raises(MCPHubError, match="Invalid JSON response"):
                await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test context manager functionality"""
        async with client as ctx_client:
            assert ctx_client is client
            # Session should be created
            assert client._session is not None

        # Session should be closed after context
        assert client._session.closed

    @pytest.mark.asyncio
    async def test_close_method(self, client):
        """Test close method"""
        # Create a session
        await client._get_session()
        assert client._session is not None

        # Close the client
        await client.close()
        assert client._session is None or client._session.closed

    @pytest.mark.asyncio
    async def test_registry_operations(self, client):
        """Test registry operations"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"success": True}
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            # Test list servers
            result = await client.registry_list_servers()
            assert result == {"success": True}

            # Test register server
            result = await client.registry_register_server({"name": "test-server"})
            assert result == {"success": True}

            # Test get server
            result = await client.registry_get_server("test-server")
            assert result == {"success": True}

            # Test enable server
            result = await client.registry_enable_server("test-server")
            assert result == {"success": True}

            # Test disable server
            result = await client.registry_disable_server("test-server")
            assert result == {"success": True}

            # Test remove server
            result = await client.registry_remove_server("test-server")
            assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_config_operations(self, client):
        """Test configuration operations"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"config": "test"}
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_context_manager

        with patch.object(client, '_get_session', return_value=mock_session):
            # Test get client config
            result = await client.get_client_config("standard", "json")
            assert result == {"config": "test"}

            # Test get client config with raw format
            result = await client.get_client_config("standard", "raw")
            assert result == {"config": "test"}