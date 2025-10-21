# MCP Hub Client Unification

## Overview

This document describes the unification of HTTP calls from the bot container to the MCP Hub server. The refactoring eliminates boilerplate code and provides a centralized, consistent interface for all MCP Hub communication.

## Problem

Previously, HTTP calls to MCP Hub were scattered across multiple files with significant code duplication:

- `src/bot/vector_search_manager.py` - Vector search operations
- `src/bot/mcp_handlers.py` - Registry operations  
- `main.py` - Health checks and server listing
- `src/mcp/client.py` - MCP client HTTP operations

### Issues with Previous Approach

1. **Code Duplication**: Each file implemented its own HTTP client logic
2. **Inconsistent Error Handling**: Different error handling patterns across files
3. **Scattered Configuration**: Timeout and retry settings spread across files
4. **Maintenance Burden**: Changes required updates in multiple locations
5. **Testing Complexity**: Each file required separate HTTP mocking

## Solution

### Unified HTTP Client

Created `src/bot/mcp_hub_client.py` - a centralized HTTP client that provides:

- **Unified API**: Single interface for all MCP Hub operations
- **Consistent Error Handling**: Standardized error types and handling
- **Centralized Configuration**: Single place for timeout, retry, and other settings
- **Type Safety**: Proper typing for all operations
- **Comprehensive Logging**: Consistent logging across all operations

### Key Features

#### 1. Centralized Operations

```python
# Vector Search Operations
await client.vector_reindex(documents, force=True)
await client.vector_add_documents(documents)
await client.vector_delete_documents(document_ids)
await client.vector_update_documents(documents)

# Registry Operations
await client.registry_list_servers()
await client.registry_register_server(config)
await client.registry_enable_server(name)
await client.registry_disable_server(name)
await client.registry_remove_server(name)

# Health Check
await client.health_check()
```

#### 2. Consistent Error Handling

```python
try:
    result = await client.vector_reindex(documents)
except MCPHubUnavailableError:
    # Service unavailable (503)
    logger.warning("Vector search not available")
except MCPHubTimeoutError:
    # Request timeout
    logger.warning("Request timed out")
except MCPHubError as e:
    # Other HTTP errors
    logger.error(f"HTTP error: {e}")
```

#### 3. Retry Logic

- Configurable retry attempts (default: 3)
- Exponential backoff between retries
- Different retry strategies for different error types

#### 4. Async Context Manager

```python
async with MCPHubClient("http://mcp-hub:8765") as client:
    result = await client.health_check()
    # Session automatically closed
```

## Implementation Details

### Error Types

- `MCPHubError`: Base exception for all MCP Hub errors
- `MCPHubTimeoutError`: Request timeout errors
- `MCPHubUnavailableError`: Service unavailable (503) errors

### Configuration

```python
client = MCPHubClient(
    base_url="http://mcp-hub:8765",
    timeout=30.0,           # Request timeout
    retry_attempts=3,       # Number of retries
    retry_delay=1.0         # Delay between retries
)
```

### Request Flow

1. **Request Preparation**: Build URL, headers, payload
2. **Retry Loop**: Attempt request with retry logic
3. **Status Code Handling**: Handle different HTTP status codes
4. **Error Classification**: Categorize errors by type
5. **Response Parsing**: Parse JSON response
6. **Logging**: Log success/failure with context

## Migration

### Files Updated

1. **`src/bot/vector_search_manager.py`**
   - Replaced `aiohttp.ClientSession` with `MCPHubClient`
   - Simplified error handling
   - Removed boilerplate HTTP code

2. **`src/bot/mcp_handlers.py`**
   - Replaced `aiohttp.ClientSession` with `MCPHubClient`
   - Unified registry operations
   - Consistent error handling

3. **`main.py`**
   - Replaced `aiohttp.ClientSession` with `MCPHubClient`
   - Simplified health check logic
   - Better error handling

### Before vs After

#### Before (Vector Search Manager)

```python
async def _call_mcp_reindex(self, documents, force=False):
    try:
        api_url = f"{self.mcp_hub_url}/vector/reindex"
        payload = {
            "documents": documents,
            "force": force,
            "kb_id": "default",
            "user_id": None
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url, 
                json=payload, 
                timeout=aiohttp.ClientTimeout(total=settings.MCP_TIMEOUT)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return True
                    else:
                        logger.warning(f"Failed: {result.get('error')}")
                        return False
                elif response.status == 503:
                    error_text = await response.text()
                    logger.warning(f"Service unavailable: {error_text}")
                    return False
                else:
                    error_text = await response.text()
                    logger.warning(f"HTTP {response.status}: {error_text}")
                    return False
    except Exception as e:
        logger.error(f"Exception: {e}", exc_info=True)
        return False
```

#### After (Vector Search Manager)

```python
async def _call_mcp_reindex(self, documents, force=False):
    try:
        result = await self._mcp_client.vector_reindex(
            documents=documents,
            force=force,
            kb_id="default",
            user_id=None
        )
        
        if result.get("success"):
            logger.info("✅ HTTP reindex_vector completed successfully")
            return True
        else:
            logger.warning(f"⚠️ HTTP reindex_vector failed: {result.get('error')}")
            return False
            
    except MCPHubUnavailableError as e:
        logger.warning(f"⚠️ Vector search not available: {e}")
        return False
    except MCPHubError as e:
        logger.warning(f"⚠️ HTTP reindex_vector failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Exception: {e}", exc_info=True)
        return False
```

## Benefits

### 1. Code Reduction

- **Eliminated ~200 lines** of boilerplate HTTP code
- **Centralized configuration** in one place
- **Consistent patterns** across all files

### 2. Improved Maintainability

- **Single point of change** for HTTP logic
- **Unified error handling** patterns
- **Easier testing** with centralized mocking

### 3. Better Error Handling

- **Type-safe errors** with specific exception types
- **Consistent retry logic** across all operations
- **Better logging** with context information

### 4. Enhanced Testing

- **Centralized test suite** for HTTP operations
- **Easier mocking** with single client interface
- **Comprehensive coverage** of error scenarios

## Testing

### Test Coverage

- **Unit tests** for all client methods
- **Error handling** tests for different scenarios
- **Retry logic** tests
- **Context manager** tests
- **Integration tests** with mocked HTTP responses

### Test Structure

```python
class TestMCPHubClient:
    @pytest.mark.asyncio
    async def test_vector_reindex_success(self, client):
        # Test successful vector reindex
        
    @pytest.mark.asyncio
    async def test_make_request_503_error(self, client):
        # Test 503 error handling
        
    @pytest.mark.asyncio
    async def test_make_request_retry_logic(self, client):
        # Test retry logic
```

## Future Enhancements

### 1. Connection Pooling

- Reuse HTTP connections for better performance
- Configurable pool size and limits

### 2. Circuit Breaker

- Automatic circuit breaking on repeated failures
- Configurable failure thresholds

### 3. Metrics and Monitoring

- Request/response metrics
- Error rate monitoring
- Performance tracking

### 4. Caching

- Response caching for read-only operations
- Configurable cache TTL

## Conclusion

The MCP Hub client unification successfully eliminates boilerplate code while providing a robust, maintainable, and testable interface for all MCP Hub communication. The centralized approach improves code quality, reduces maintenance burden, and provides a solid foundation for future enhancements.