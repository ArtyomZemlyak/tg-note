#!/usr/bin/env python3
"""
Mock MCP Hub server for testing
"""

import asyncio
import json
import logging
from aiohttp import web, web_request

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Store pending requests
pending_requests = {}

# Store active SSE connections
active_connections = set()

async def handle_sse(request: web_request.Request):
    """Handle SSE connection"""
    logger.info("New SSE connection established")
    
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    await response.prepare(request)
    
    # Send endpoint event with session_id
    session_id = "test-session-123"
    endpoint_data = f"/messages/?session_id={session_id}"
    
    await response.write(f"event: endpoint\n".encode())
    await response.write(f"data: {endpoint_data}\n\n".encode())
    
    logger.info(f"Sent endpoint event with session_id: {session_id}")
    
    # Add connection to active set
    active_connections.add(response)
    
    # Keep connection open and send responses
    try:
        while True:
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
    except asyncio.CancelledError:
        logger.info("SSE connection cancelled")
    finally:
        active_connections.discard(response)
        logger.info("SSE connection closed")
    
    return response

async def handle_messages(request: web_request.Request):
    """Handle JSON-RPC messages"""
    try:
        data = await request.json()
        logger.info(f"Received message: {data}")
        
        # Extract request ID
        request_id = data.get('id')
        method = data.get('method')
        
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {"listChanged": True},
                    },
                    "serverInfo": {
                        "name": "mock-mcp-hub",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "tools/call":
            tool_name = data.get('params', {}).get('name')
            if tool_name == "reindex_vector":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": "Reindex completed successfully"
                        }],
                        "isError": False
                    }
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {tool_name}"
                    }
                }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
        
        # Send response back via SSE (simulate FastMCP behavior)
        logger.info(f"Sending response via SSE: {response}")
        
        # Send response through all active SSE connections
        response_json = json.dumps(response)
        for conn in list(active_connections):
            try:
                await conn.write(f"event: message\n".encode())
                await conn.write(f"data: {response_json}\n\n".encode())
                logger.info(f"Sent response to SSE connection")
            except Exception as e:
                logger.warning(f"Failed to send to SSE connection: {e}")
                active_connections.discard(conn)
        
        return web.json_response(response)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        return web.json_response({
            "jsonrpc": "2.0",
            "id": data.get('id') if 'data' in locals() else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }, status=500)

async def handle_health(request: web_request.Request):
    """Handle health check"""
    return web.json_response({
        "status": "healthy",
        "builtin_tools": {
            "names": [
                "vector_search",
                "reindex_vector", 
                "add_vector_documents",
                "delete_vector_documents",
                "update_vector_documents"
            ]
        }
    })

async def create_app():
    """Create web application"""
    app = web.Application()
    
    # Routes
    app.router.add_get('/sse', handle_sse)
    app.router.add_get('/sse/', handle_sse)  # Add trailing slash version
    app.router.add_post('/messages/', handle_messages)
    app.router.add_get('/health', handle_health)
    
    return app

async def main():
    """Main function"""
    app = await create_app()
    
    logger.info("Starting mock MCP Hub server on http://localhost:8765")
    logger.info("SSE endpoint: http://localhost:8765/sse")
    logger.info("Messages endpoint: http://localhost:8765/messages/")
    logger.info("Health endpoint: http://localhost:8765/health")
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, 'localhost', 8765)
    await site.start()
    
    logger.info("Mock MCP Hub server started successfully")
    
    try:
        # Keep server running
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("Shutting down mock MCP Hub server...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())