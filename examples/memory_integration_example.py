#!/usr/bin/env python3
"""
Example: Using integrated memory storage with different backends

This example demonstrates how to use the unified memory storage interface
with different backends: JSON, Vector, and Mem-Agent.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.mcp.memory import MemoryStorageFactory


def example_json_storage():
    """Example using JSON storage (default, fastest)"""
    print("\n=== JSON Storage Example ===")
    
    storage = MemoryStorageFactory.create(
        storage_type="json",
        data_dir=Path("/tmp/memory_example/json")
    )
    
    # Store information
    result = storage.store(
        content="Python is my preferred language for backend development",
        category="preferences",
        tags=["programming", "backend"]
    )
    print(f"Store result: {result['success']}")
    
    # Retrieve information
    results = storage.retrieve(query="Python", limit=5)
    print(f"Found {results['count']} memories")
    if results['memories']:
        print(f"First memory: {results['memories'][0]['content'][:100]}")


def example_vector_storage():
    """Example using Vector storage (semantic search)"""
    print("\n=== Vector Storage Example ===")
    
    try:
        storage = MemoryStorageFactory.create(
            storage_type="vector",
            data_dir=Path("/tmp/memory_example/vector"),
            model_name="all-MiniLM-L6-v2"  # Small model for testing
        )
        
        # Store related information
        storage.store("I love working with Python", category="preferences")
        storage.store("FastAPI is my favorite framework", category="preferences")
        storage.store("I prefer PostgreSQL for databases", category="preferences")
        
        # Semantic search - should find related content even without exact keywords
        results = storage.retrieve(query="favorite programming tools", limit=3)
        print(f"Semantic search found {results['count']} memories")
        for i, memory in enumerate(results['memories'], 1):
            print(f"{i}. {memory['content'][:80]}")
    
    except ImportError as e:
        print(f"Vector storage not available: {e}")
        print("Install with: pip install sentence-transformers torch")


def example_mem_agent_storage():
    """Example using Mem-Agent storage (LLM-based intelligent memory)"""
    print("\n=== Mem-Agent Storage Example ===")
    
    try:
        storage = MemoryStorageFactory.create(
            storage_type="mem-agent",
            data_dir=Path("/tmp/memory_example/mem_agent"),
            model="driaforall/mem-agent",
            use_vllm=False,  # Use OpenRouter for this example
            max_tool_turns=10
        )
        
        # Store complex information - agent will organize it intelligently
        result = storage.store(
            content=(
                "I work at TechCorp as a Senior Engineer. "
                "My team focuses on backend systems using Python and Go. "
                "I report to Sarah, the Engineering Manager."
            ),
            category="work",
            tags=["job", "team"]
        )
        print(f"Store result: {result['success']}")
        print(f"Agent reply: {result.get('agent_reply', 'N/A')[:100]}")
        
        # Query - agent will search through organized memory
        results = storage.retrieve(query="Who is my manager?", limit=1)
        if results['memories']:
            print(f"\nAgent response: {results['memories'][0]['content'][:200]}")
    
    except ImportError as e:
        print(f"Mem-agent storage not available: {e}")
        print("Install with: pip install fastmcp transformers openai")
    except Exception as e:
        print(f"Error using mem-agent: {e}")
        print("Make sure OPENROUTER_API_KEY is set or vLLM server is running")


def example_unified_interface():
    """Example showing unified interface across all storage types"""
    print("\n=== Unified Interface Example ===")
    
    # All storage types implement the same interface
    storage_configs = [
        ("json", {"storage_type": "json"}),
        # Uncomment to test other types:
        # ("vector", {"storage_type": "vector", "model_name": "all-MiniLM-L6-v2"}),
        # ("mem-agent", {"storage_type": "mem-agent", "use_vllm": False}),
    ]
    
    for name, config in storage_configs:
        try:
            print(f"\nTesting {name} storage...")
            storage = MemoryStorageFactory.create(
                data_dir=Path(f"/tmp/memory_example/{name}_unified"),
                **config
            )
            
            # Same interface for all!
            storage.store("Test information", category="test")
            results = storage.retrieve(query="Test")
            print(f"✓ {name}: Stored and retrieved successfully")
            
        except Exception as e:
            print(f"✗ {name}: {e}")


def main():
    """Run all examples"""
    print("Memory Storage Integration Examples")
    print("=" * 50)
    
    # Basic examples
    example_json_storage()
    example_vector_storage()
    example_mem_agent_storage()
    
    # Unified interface demonstration
    example_unified_interface()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nNote: Some examples may be skipped if dependencies are not installed.")
    print("See README.md for installation instructions.")


if __name__ == "__main__":
    main()
