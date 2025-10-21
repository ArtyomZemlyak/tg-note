# Vector Search Indexing Tools HTTP Refactoring

## Summary

Successfully refactored 4 vector search indexing tools from MCP tools to HTTP endpoints, while keeping the vector search tool as MCP for agent usage.

## Changes Made

### 1. HTTP Endpoints Created

Added 4 new HTTP endpoints in `/workspace/src/mcp/mcp_hub_server.py`:

- `POST /vector/reindex` - Reindex knowledge base for vector search
- `POST /vector/documents` - Add or update documents to vector search index  
- `DELETE /vector/documents` - Delete documents from vector search index
- `PUT /vector/documents` - Update documents in vector search index

### 2. MCP Tools Removed

Removed the following MCP tools from `mcp_hub_server.py`:
- `reindex_vector`
- `add_vector_documents` 
- `delete_vector_documents`
- `update_vector_documents`

### 3. MCP Tool Preserved

Kept `vector_search` as MCP tool for agent usage - this is the only vector search tool that agents can use.

### 4. Health Check Updated

Updated health check endpoint to include information about vector search HTTP API endpoints.

### 5. Function Updates

- Updated `get_builtin_tools()` to only include `vector_search` in MCP tools
- Updated logging to reflect the new architecture

## API Usage

### HTTP Endpoints

All endpoints expect JSON payloads and return JSON responses:

```bash
# Reindex
curl -X POST http://localhost:8765/vector/reindex \
  -H "Content-Type: application/json" \
  -d '{"documents": [...], "force": false, "kb_id": "default"}'

# Add documents
curl -X POST http://localhost:8765/vector/documents \
  -H "Content-Type: application/json" \
  -d '{"documents": [...], "kb_id": "default"}'

# Delete documents  
curl -X DELETE http://localhost:8765/vector/documents \
  -H "Content-Type: application/json" \
  -d '{"document_ids": [...], "kb_id": "default"}'

# Update documents
curl -X PUT http://localhost:8765/vector/documents \
  -H "Content-Type: application/json" \
  -d '{"documents": [...], "kb_id": "default"}'
```

### MCP Tool

The `vector_search` MCP tool remains available for agents:

```python
# Agent can still use vector search via MCP
result = await mcp_client.call_tool("vector_search", {
    "query": "machine learning",
    "top_k": 5,
    "kb_id": "default"
})
```

## Benefits

1. **Separation of Concerns**: Indexing operations are now HTTP-only, search remains MCP
2. **Better Architecture**: HTTP endpoints are more suitable for bot/docker integration
3. **Agent Simplicity**: Agents only see the search tool, not complex indexing operations
4. **Maintainability**: Clear separation between indexing (HTTP) and search (MCP) operations

## Testing

All changes have been tested and verified:
- ✅ HTTP endpoints are properly defined
- ✅ MCP indexing tools are removed
- ✅ MCP search tool is preserved
- ✅ Health check includes API information
- ✅ Code compiles without errors

## Files Modified

- `/workspace/src/mcp/mcp_hub_server.py` - Main changes
- `/workspace/VECTOR_INDEXING_HTTP_REFACTORING.md` - This documentation