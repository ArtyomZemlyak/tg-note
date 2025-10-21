#!/usr/bin/env python3
"""
Test script to simulate MCP connection drop scenario
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.mcp.client import MCPClient, MCPServerConfig
from config import settings

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_mcp_connection_drop():
    """Test MCP connection drop behavior"""
    
    # Use localhost with a port that might be open but not MCP Hub
    mcp_hub_url = "http://localhost:80"  # HTTP port, not MCP Hub
    
    logger.info(f"Testing MCP connection drop with: {mcp_hub_url}")
    
    # Create SSE URL
    sse_url = mcp_hub_url
    if not sse_url.endswith("/sse"):
        sse_url = f"{sse_url}/sse"
    
    logger.info(f"SSE URL: {sse_url}")
    
    # Create MCP client with short timeout for testing
    client = MCPClient(
        MCPServerConfig(transport="sse", url=sse_url), 
        timeout=5  # Short timeout for testing
    )
    
    try:
        # Connect
        logger.info("Attempting to connect...")
        connected = await client.connect()
        logger.info(f"Connection result: {connected}")
        
        if connected:
            # Test a tool call
            logger.info("Testing tool call...")
            result = await client.call_tool("reindex_vector", {"documents": [], "force": True})
            logger.info(f"Tool call result: {result}")
        else:
            logger.info("Connection failed")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during MCP test: {e}", exc_info=True)
        return False
    finally:
        await client.disconnect()
        logger.info("Disconnected from MCP client")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection_drop())