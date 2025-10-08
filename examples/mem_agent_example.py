#!/usr/bin/env python3
"""
Memory Agent Example

This example demonstrates how to use the mem-agent for maintaining
persistent memory across conversations.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.mem_agent import Agent


def main():
    """Run mem-agent example"""
    
    print("=" * 60)
    print("Memory Agent Example")
    print("=" * 60)
    print()
    
    # Create a temporary memory directory for this example
    memory_path = Path("./data/example_memory")
    memory_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Memory path: {memory_path}")
    print()
    
    # Check if vLLM is available
    try:
        import vllm
        use_vllm = True
        print("✓ vLLM is available")
    except ImportError:
        use_vllm = False
        print("✗ vLLM not available, using OpenRouter")
        if not os.getenv("OPENAI_API_KEY"):
            print()
            print("WARNING: No OPENAI_API_KEY found in environment.")
            print("Please set it to use OpenRouter:")
            print("  export OPENAI_API_KEY=your-key-here")
            print()
            return 1
    
    print()
    
    # Create agent
    print("Creating mem-agent...")
    try:
        agent = Agent(
            memory_path=str(memory_path),
            use_vllm=use_vllm,
            model="driaforall/mem-agent" if use_vllm else None
        )
        print("✓ Agent created successfully")
    except Exception as e:
        print(f"✗ Failed to create agent: {e}")
        return 1
    
    print()
    print("=" * 60)
    print("Example Conversations")
    print("=" * 60)
    print()
    
    # Example 1: Save information to memory
    print("1. Saving information to memory")
    print("-" * 60)
    question1 = "My name is Alice and I work at Google as a software engineer. I love Python programming."
    print(f"User: {question1}")
    print()
    
    try:
        response1 = agent.chat(question1)
        print(f"Agent: {response1.reply}")
        print()
        if response1.thoughts:
            print(f"[Thoughts: {response1.thoughts[:100]}...]")
        if response1.python_block:
            print(f"[Executed code: {len(response1.python_block)} chars]")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Example 2: Query information from memory
    print("2. Querying information from memory")
    print("-" * 60)
    question2 = "What is my name and where do I work?"
    print(f"User: {question2}")
    print()
    
    try:
        response2 = agent.chat(question2)
        print(f"Agent: {response2.reply}")
        print()
        if response2.thoughts:
            print(f"[Thoughts: {response2.thoughts[:100]}...]")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Example 3: Add more related information
    print("3. Adding related information")
    print("-" * 60)
    question3 = "I have a colleague named Bob who is a project manager. We're working on a machine learning project."
    print(f"User: {question3}")
    print()
    
    try:
        response3 = agent.chat(question3)
        print(f"Agent: {response3.reply}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    # Example 4: Query complex relationships
    print("4. Querying complex relationships")
    print("-" * 60)
    question4 = "Tell me about my work relationships and projects"
    print(f"User: {question4}")
    print()
    
    try:
        response4 = agent.chat(question4)
        print(f"Agent: {response4.reply}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()
    
    print("=" * 60)
    print("Memory Structure")
    print("=" * 60)
    print()
    
    # Show memory structure
    print("Files created in memory:")
    for root, dirs, files in os.walk(memory_path):
        level = root.replace(str(memory_path), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f'{subindent}{file}')
    
    print()
    print("To explore the memory files, check:")
    print(f"  {memory_path}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
