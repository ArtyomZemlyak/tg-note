#!/usr/bin/env python3
"""
Basic test script for mem-agent implementation
Tests imports and basic functionality without requiring pytest
"""

import sys
import tempfile
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from src.agents.mem_agent import Agent, AgentResponse, ChatMessage, Role, StaticMemory
        print("✓ Main imports successful")
        
        from src.agents.mem_agent.settings import MAX_TOOL_TURNS, get_memory_path
        print("✓ Settings import successful")
        
        from src.agents.mem_agent.utils import extract_python_code, extract_reply
        print("✓ Utils import successful")
        
        from src.agents.mem_agent.tools import create_file, read_file
        print("✓ Tools import successful")
        
        from src.agents.mem_agent.mcp_server import mcp, get_agent
        print("✓ MCP server import successful")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schemas():
    """Test schema objects"""
    print("\nTesting schemas...")
    
    try:
        from src.agents.mem_agent.schemas import ChatMessage, Role, AgentResponse
        
        # Test ChatMessage
        msg = ChatMessage(role=Role.USER, content="Test message")
        assert msg.role == Role.USER
        print("✓ ChatMessage works")
        
        # Test AgentResponse
        response = AgentResponse(
            thoughts="Test thoughts",
            reply="Test reply",
            python_block="test_code"
        )
        assert response.thoughts == "Test thoughts"
        print("✓ AgentResponse works")
        
        return True
    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        return False


def test_utils():
    """Test utility functions"""
    print("\nTesting utility functions...")
    
    try:
        from src.agents.mem_agent.utils import (
            extract_python_code,
            extract_reply,
            extract_thoughts
        )
        
        test_response = """
        <think>Thinking about it</think>
        <python>x = 1</python>
        <reply>Done!</reply>
        """
        
        thoughts = extract_thoughts(test_response)
        assert "Thinking" in thoughts
        print("✓ extract_thoughts works")
        
        code = extract_python_code(test_response)
        assert "x = 1" in code
        print("✓ extract_python_code works")
        
        reply = extract_reply(test_response)
        assert "Done" in reply
        print("✓ extract_reply works")
        
        return True
    except Exception as e:
        print(f"✗ Utils test failed: {e}")
        return False


def test_tools():
    """Test tool functions"""
    print("\nTesting tool functions...")
    
    try:
        from src.agents.mem_agent.tools import (
            create_file,
            read_file,
            check_if_file_exists,
            list_files
        )
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            
            try:
                # Test file creation
                result = create_file("test.md", "Test content")
                assert result is True
                print("✓ create_file works")
                
                # Test file existence
                exists = check_if_file_exists("test.md")
                assert exists is True
                print("✓ check_if_file_exists works")
                
                # Test file reading
                content = read_file("test.md")
                assert content == "Test content"
                print("✓ read_file works")
                
                # Test list_files
                file_list = list_files()
                assert "test.md" in file_list
                print("✓ list_files works")
                
            finally:
                os.chdir(old_cwd)
        
        return True
    except Exception as e:
        print(f"✗ Tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_settings():
    """Test settings integration"""
    print("\nTesting settings...")
    
    try:
        from src.agents.mem_agent.settings import (
            MAX_TOOL_TURNS,
            VLLM_HOST,
            VLLM_PORT,
            FILE_SIZE_LIMIT,
            SANDBOX_TIMEOUT,
            get_memory_path
        )
        
        # Check basic types
        assert isinstance(MAX_TOOL_TURNS, int)
        assert isinstance(VLLM_PORT, int)
        assert isinstance(FILE_SIZE_LIMIT, int)
        print("✓ Settings values are correct types")
        
        # Test get_memory_path
        path = get_memory_path()
        assert isinstance(path, Path)
        print("✓ get_memory_path works")
        
        return True
    except Exception as e:
        print(f"✗ Settings test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Memory Agent Basic Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Schemas", test_schemas()))
    results.append(("Utils", test_utils()))
    results.append(("Tools", test_tools()))
    results.append(("Settings", test_settings()))
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:20s} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    else:
        print("Some tests failed! ✗")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
