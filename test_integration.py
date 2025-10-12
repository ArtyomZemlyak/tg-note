#!/usr/bin/env python3
"""
Quick integration test for mem-agent

This script verifies that:
1. All imports work correctly
2. Factory can create storage instances
3. Basic interface works
"""

import sys
from pathlib import Path


def test_imports():
    """Test that all imports work"""
    print("Testing imports...")

    try:
        # Core interfaces
        from src.mcp.memory import (
            BaseMemoryStorage,
            JsonMemoryStorage,
            MemAgentStorage,
            MemoryStorage,
            MemoryStorageFactory,
            VectorBasedMemoryStorage,
        )

        print("✓ Core imports OK")
    except ImportError as e:
        print(f"✗ Core imports failed: {e}")
        return False

    try:
        # Mem-agent implementation
        from src.mcp.memory.mem_agent_impl import Agent, AgentResponse, ChatMessage, Role

        print("✓ Mem-agent imports OK")
    except ImportError as e:
        print(f"✗ Mem-agent imports failed: {e}")
        return False

    return True


def test_factory():
    """Test factory creation"""
    print("\nTesting factory...")

    try:
        from src.mcp.memory import MemoryStorageFactory

        # List available types
        types = MemoryStorageFactory.list_available_types()
        print(f"Available storage types: {types}")

        if "mem-agent" not in types:
            print("✗ mem-agent not registered in factory")
            return False

        print("✓ Factory registration OK")
        return True

    except Exception as e:
        print(f"✗ Factory test failed: {e}")
        return False


def test_json_storage():
    """Test JSON storage (always available)"""
    print("\nTesting JSON storage...")

    try:
        from src.mcp.memory import MemoryStorageFactory

        storage = MemoryStorageFactory.create(
            storage_type="json", data_dir=Path("/tmp/test_integration_json")
        )

        # Test store
        result = storage.store("Test content", category="test")
        if not result.get("success"):
            print(f"✗ Store failed: {result}")
            return False

        # Test retrieve
        results = storage.retrieve(query="Test")
        if not results.get("success"):
            print(f"✗ Retrieve failed: {results}")
            return False

        print("✓ JSON storage OK")
        return True

    except Exception as e:
        print(f"✗ JSON storage test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_mem_agent_creation():
    """Test mem-agent storage creation (may fail if deps missing)"""
    print("\nTesting mem-agent storage creation...")

    try:
        from src.mcp.memory import MemoryStorageFactory

        # Just test creation, not actual LLM operations
        storage = MemoryStorageFactory.create(
            storage_type="mem-agent",
            data_dir=Path("/tmp/test_integration_mem_agent"),
            model="driaforall/mem-agent",
            use_vllm=False,  # Don't require vLLM
        )

        print("✓ Mem-agent storage creation OK")
        print("  (Note: Actual operations require OpenRouter API key or vLLM)")
        return True

    except ImportError as e:
        print(f"⚠ Mem-agent dependencies missing: {e}")
        print("  Install with: pip install fastmcp transformers openai")
        return False  # Not a critical failure

    except Exception as e:
        print(f"✗ Mem-agent creation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_direct_agent():
    """Test direct agent import"""
    print("\nTesting direct agent import...")

    try:
        from src.mcp.memory.mem_agent_impl import Agent

        # Just test import, not instantiation (requires config)
        print(f"✓ Agent class imported: {Agent}")
        return True

    except ImportError as e:
        print(f"✗ Direct agent import failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Mem-Agent Integration Test")
    print("=" * 60)

    results = {
        "Imports": test_imports(),
        "Factory": test_factory(),
        "JSON Storage": test_json_storage(),
        "Mem-Agent Creation": test_mem_agent_creation(),
        "Direct Agent": test_direct_agent(),
    }

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<40} {status}")

    passed_count = sum(results.values())
    total_count = len(results)

    print("=" * 60)
    print(f"Passed: {passed_count}/{total_count}")

    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
