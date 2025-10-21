#!/usr/bin/env python3
"""
Debug script to test MCP connection and understand why _send_request returns None
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

async def test_mcp_connection():
    """Test MCP connection and tool call"""
    
    # Get MCP Hub URL from environment or use default
    mcp_hub_url = "http://mcp-hub:8765"  # Adjust this URL as needed
    
    logger.info(f"Testing MCP connection to {mcp_hub_url}")
    
    # Create SSE URL
    sse_url = mcp_hub_url
    if not sse_url.endswith("/sse"):
        sse_url = f"{sse_url}/sse"
    
    logger.info(f"SSE URL: {sse_url}")
    
    # Create MCP client
    client = MCPClient(
        MCPServerConfig(transport="sse", url=sse_url), 
        timeout=settings.MCP_TIMEOUT
    )
    
    try:
        # Connect
        logger.info("Connecting to MCP Hub...")
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to MCP Hub")
            return False
        
        logger.info("✅ Connected to MCP Hub")
        
        # List tools
        logger.info("Listing available tools...")
        tools = await client.list_tools()
        logger.info(f"Available tools: {[tool.get('name') for tool in tools.get('tools', [])]}")
        
        # Test a simple tool call
        logger.info("Testing reindex_vector tool call...")
        result = await client.call_tool("reindex_vector", {"documents": [], "force": True})
        logger.info(f"Tool call result: {result}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during MCP test: {e}", exc_info=True)
        return False
    finally:
        await client.disconnect()
        logger.info("Disconnected from MCP Hub")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())