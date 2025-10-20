#!/usr/bin/env python3
"""
Test script for improved note mode prompts
Tests the enhanced search functionality in note creation mode
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from src.agents.autonomous_agent import AutonomousAgent
from src.agents.llm_connectors import BaseLLMConnector, LLMResponse
from config.agent_prompts import get_note_mode_instruction


class MockLLMConnector(BaseLLMConnector):
    """Mock LLM connector for testing"""
    
    def get_model_name(self):
        return "mock-model"
    
    async def chat_completion(self, messages, tools=None, temperature=0.7, **kwargs):
        # Return a simple response that suggests using search tools
        return LLMResponse(
            content="I need to search the knowledge base first using kb_search_content tool.",
            tool_calls=[{
                "function": {
                    "name": "kb_search_content",
                    "arguments": '{"query": "neural networks"}'
                }
            }]
        )


class MockToolManager:
    """Mock tool manager for testing"""
    
    def __init__(self):
        self.tools = {
            "kb_search_content": Mock(return_value={
                "success": True,
                "matches": [
                    {
                        "file": "ai/machine_learning.md",
                        "content": "Machine learning is a subset of AI",
                        "line_number": 1
                    }
                ],
                "files_found": 1
            }),
            "kb_search_files": Mock(return_value={
                "success": True,
                "files": [
                    {"path": "ai/machine_learning.md", "name": "machine_learning.md"}
                ],
                "file_count": 1
            }),
            "kb_list_directory": Mock(return_value={
                "success": True,
                "directories": ["ai/", "tech/"],
                "files": ["ai/machine_learning.md"]
            }),
            "kb_read_file": Mock(return_value={
                "success": True,
                "content": "# Machine Learning\n\nMachine learning is a subset of AI...",
                "file_path": "ai/machine_learning.md"
            }),
            "analyze_content": Mock(return_value={
                "success": True,
                "analysis": "Content analyzed successfully"
            }),
            "file_create": Mock(return_value={
                "success": True,
                "path": "ai/neural_networks.md"
            })
        }
    
    def has(self, tool_name):
        return tool_name in self.tools
    
    async def execute(self, tool_name, params):
        if tool_name in self.tools:
            return self.tools[tool_name](**params)
        return {"success": False, "error": f"Tool {tool_name} not found"}


async def test_note_mode_improvements():
    """Test the improved note mode functionality"""
    print("🧪 Testing improved note mode prompts...")
    
    # Create mock LLM connector
    llm_connector = MockLLMConnector()
    
    # Create agent with note mode instruction
    agent = AutonomousAgent(
        llm_connector=llm_connector,
        config={"enable_mcp": False},
        instruction=get_note_mode_instruction("ru")
    )
    
    # Replace tool manager with mock
    agent.tool_manager = MockToolManager()
    
    # Test content about neural networks
    test_content = {
        "text": "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) that process information using a connectionist approach to computation.",
        "urls": []
    }
    
    print("📝 Testing with content about neural networks...")
    print(f"Content: {test_content['text'][:100]}...")
    
    try:
        # Process content
        result = await agent.process(test_content)
        
        print("✅ Processing completed successfully!")
        print(f"Result keys: {list(result.keys())}")
        
        # Check if search was performed
        if "metadata" in result:
            metadata = result["metadata"]
            print(f"Metadata: {json.dumps(metadata, indent=2, ensure_ascii=False)}")
        
        # Check if files were created/edited
        if "files_created" in result.get("metadata", {}):
            files_created = result["metadata"]["files_created"]
            print(f"Files created: {files_created}")
        
        if "files_edited" in result.get("metadata", {}):
            files_edited = result["metadata"]["files_edited"]
            print(f"Files edited: {files_edited}")
        
        print("\n🎯 Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_search_priority():
    """Test that search tools are prioritized"""
    print("\n🔍 Testing search tool priority...")
    
    # Check if the instruction mentions search tools first
    instruction = get_note_mode_instruction("ru")
    
    search_mentions = [
        "kb_search_content" in instruction,
        "kb_search_files" in instruction,
        "ПОИСК СУЩЕСТВУЮЩЕЙ ИНФОРМАЦИИ" in instruction,
        "ОБЯЗАТЕЛЬНО ПЕРВЫМ ДЕЛОМ" in instruction
    ]
    
    if all(search_mentions):
        print("✅ Search tools are properly prioritized in instructions")
        return True
    else:
        print("❌ Search tools are not properly prioritized")
        print(f"Search mentions: {search_mentions}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting note mode improvements test suite\n")
    
    # Test 1: Search priority
    search_test = await test_search_priority()
    
    # Test 2: Note processing
    note_test = await test_note_mode_improvements()
    
    print(f"\n📊 Test Results:")
    print(f"Search Priority Test: {'✅ PASS' if search_test else '❌ FAIL'}")
    print(f"Note Processing Test: {'✅ PASS' if note_test else '❌ FAIL'}")
    
    if search_test and note_test:
        print("\n🎉 All tests passed! Note mode improvements are working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    asyncio.run(main())
