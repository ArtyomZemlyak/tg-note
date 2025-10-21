#!/usr/bin/env python3
"""
Analyze SSE reader task issue
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

async def analyze_sse_issue():
    """Analyze why SSE reader task fails"""
    
    # Use a non-existent URL to trigger the issue
    mcp_hub_url = "http://non-existent-host:8765"
    
    logger.info(f"Analyzing SSE issue with: {mcp_hub_url}")
    
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
        
        return True
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return False
    finally:
        await client.disconnect()
        logger.info("Disconnected from MCP client")

if __name__ == "__main__":
    asyncio.run(analyze_sse_issue())