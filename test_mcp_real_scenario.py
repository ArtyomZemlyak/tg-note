#!/usr/bin/env python3
"""
Test script to simulate real MCP scenario with proper error handling
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

async def test_mcp_real_scenario():
    """Test MCP with real scenario simulation"""
    
    # Try to connect to actual MCP Hub if available, otherwise use mock
    mcp_hub_url = "http://localhost:8765"  # Try localhost first
    
    logger.info(f"Testing MCP with real scenario: {mcp_hub_url}")
    
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
        logger.info("Attempting to connect to MCP Hub...")
        connected = await client.connect()
        logger.info(f"Connection result: {connected}")
        
        if connected:
            # Test a tool call
            logger.info("Testing reindex_vector tool call...")
            result = await client.call_tool("reindex_vector", {"documents": [], "force": True})
            logger.info(f"Tool call result: {result}")
            
            # Test another tool call
            logger.info("Testing list_tools...")
            tools = await client.list_tools()
            logger.info(f"Available tools: {[tool.get('name') for tool in tools.get('tools', [])]}")
        else:
            logger.info("Connection failed - this is expected if MCP Hub is not running")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during MCP test: {e}", exc_info=True)
        return False
    finally:
        await client.disconnect()
        logger.info("Disconnected from MCP client")

if __name__ == "__main__":
    asyncio.run(test_mcp_real_scenario())