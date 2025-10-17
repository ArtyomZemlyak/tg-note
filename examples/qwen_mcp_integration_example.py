"""
Example: Qwen CLI with MCP Integration (HTTP Mode)

This example demonstrates how to use QwenCodeCLIAgent with MCP support using HTTP/SSE transport.

The agent will:
1. Automatically generate .qwen/settings.json configuration (HTTP mode)
2. Configure mem-agent MCP server with HTTP/SSE transport
3. Qwen CLI will connect to the HTTP MCP server via SSE
4. MCP tools will be available to the LLM

Prerequisites:
- qwen CLI installed: npm install -g @qwen-code/qwen-code@latest
- qwen CLI authenticated: qwen (follow prompts)
- HTTP server running: python3 -m src.mcp.mem_agent_server_http

Note: HTTP/SSE mode is now the default (use_http=True).
For STDIO mode, set use_http=False in setup_qwen_mcp_config().
"""

import asyncio
from pathlib import Path

from src.agents.qwen_code_cli_agent import QwenCodeCLIAgent


async def example_basic_usage():
    """Basic usage - automatic MCP setup."""
    print("=" * 80)
    print("Example 1: Basic Usage with Automatic MCP Setup")
    print("=" * 80)

    # Create agent with MCP enabled
    agent = QwenCodeCLIAgent(
        config={"enable_mcp": True, "user_id": 123},
        working_directory="./knowledge_bases/test-kb",
        enable_web_search=True,
    )

    # The agent has automatically:
    # 1. Generated ~/.qwen/settings.json
    # 2. Configured mem-agent MCP server

    print("\n✅ Agent initialized with MCP support")
    print(f"Working directory: {agent.working_directory}")
    print(f"MCP enabled: {agent.enable_mcp}")

    # Process some content
    # The LLM will have access to mem-agent tools:
    # - store_memory
    # - retrieve_memory
    # - list_categories

    content = {
        "text": """
        Important information to remember:
        - Project deadline: December 15, 2025
        - Team meeting: Every Monday at 10 AM
        - Budget: $50,000 for Q4

        Please analyze this and store important dates and tasks in memory.
        """
    }

    print("\n" + "=" * 80)
    print("Processing content with MCP-enabled agent...")
    print("=" * 80)

    try:
        result = await agent.process(content)

        print("\n✅ Content processed successfully!")
        print(f"Title: {result['title']}")
        print(f"\nMarkdown preview:\n{result['markdown'][:500]}...")

        # The LLM may have used MCP tools to store information
        # Check the memory data file
        memory_file = Path(f"data/memory/user_123/memory.json")
        if memory_file.exists():
            import json

            with open(memory_file) as f:
                memories = json.load(f)
            print(f"\n📝 Stored {len(memories)} memories")
            for i, mem in enumerate(memories[-3:], 1):  # Show last 3
                print(f"  {i}. [{mem['category']}] {mem['content'][:60]}...")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def example_manual_config():
    """Manual MCP configuration without agent."""
    print("\n" + "=" * 80)
    print("Example 2: Manual MCP Configuration (HTTP Mode)")
    print("=" * 80)

    # Manually generate qwen MCP config
    from src.mcp.qwen_config_generator import QwenMCPConfigGenerator

    # HTTP mode is default (use_http=True)
    generator = QwenMCPConfigGenerator(user_id=456)

    # Preview configuration
    config_json = generator.get_config_json()
    print("\nGenerated configuration (HTTP/SSE):")
    print(config_json)

    # Save to global ~/.qwen/settings.json
    saved_path = generator.save_to_qwen_dir()
    print(f"\n✅ Configuration saved to: {saved_path}")

    # Example: Generate STDIO config (backward compatibility)
    print("\n" + "-" * 80)
    print("Alternative: STDIO mode (for backward compatibility)")
    generator_stdio = QwenMCPConfigGenerator(user_id=456, use_http=False)
    config_stdio = generator_stdio.get_config_json()
    print("\nGenerated configuration (STDIO):")
    print(config_stdio)


async def example_standalone_mcp_server():
    """Test standalone MCP server directly"""

    print("\n" + "=" * 80)
    print("Example 3: Testing Standalone MCP Server")
    print("=" * 80)

    from src.mcp.memory.memory_server import MemoryMCPServer

    # Create server instance
    server = MemoryMCPServer(user_id=789)

    # Test listing tools
    tools = await server.handle_list_tools()
    print(f"\n📋 Available tools: {len(tools)}")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    # Test storing memory
    print("\n💾 Testing store_memory...")
    result = await server.handle_call_tool(
        "store_memory", {"content": "Remember to review code at 2 PM", "category": "tasks"}
    )
    print(f"Result: {result[0]['text']}")

    # Test retrieving memory
    print("\n🔍 Testing retrieve_memory...")
    result = await server.handle_call_tool("retrieve_memory", {"category": "tasks"})
    print(f"Result: {result[0]['text']}")


async def example_with_ask_mode():
    """Example using /ask mode with MCP"""

    print("\n" + "=" * 80)
    print("Example 4: Ask Mode with MCP")
    print("=" * 80)

    agent = QwenCodeCLIAgent(
        config={"enable_mcp": True, "user_id": 999}, working_directory="./knowledge_bases/qa-kb"
    )

    # Ask mode - the LLM can use MCP tools to store/retrieve context
    content = {
        "text": "What are my upcoming deadlines?",
        "prompt": """
        # Task

        Answer the user's question using available information.

        If you have access to memory tools, search stored memories for relevant information.

        ## User Question

        What are my upcoming deadlines?

        ## Instructions

        1. Search memory for deadline-related information
        2. List all found deadlines
        3. Provide a clear answer.
        """,
    }
    print("\nAsking question with memory access...")

    try:
        result = await agent.process(content)
        print(f"\n✅ Answer: {result.get('answer', 'No answer field')}")
        print(f"\nMarkdown:\n{result['markdown']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run all examples"""

    print("\n" + "=" * 80)
    print("QWEN CLI MCP INTEGRATION EXAMPLES")
    print("=" * 80)

    # Example 1: Basic usage
    await example_basic_usage()

    # Example 2: Manual config
    await example_manual_config()

    # Example 3: Standalone server
    await example_standalone_mcp_server()

    # Example 4: Ask mode
    # await example_with_ask_mode()  # Uncomment to run

    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)
    print("\n📚 Next steps:")
    print("1. Start MCP Hub: python3 -m src.mcp.mcp_hub_server")
    print("2. Check ~/.qwen/settings.json to see generated configuration")
    print("3. Run: qwen (CLI will connect to configured MCP servers)")
    print("4. Test MCP tools in qwen CLI")
    print("5. Check data/memory/user_*/memory.json for stored memories")
    print("\n🔧 Configuration:")
    print("- HTTP mode (default): use_http=True, port 8765")
    print("- STDIO mode (legacy): use_http=False")
    print("\n📖 Documentation:")
    print("- Setup guide: docs_site/agents/mem-agent-setup.md")
    print("- MCP Hub: src/agents/mcp/mcp_hub_server.py")
    print("- Test script: scripts/test_mem_agent_connection.sh")


if __name__ == "__main__":
    asyncio.run(main())
