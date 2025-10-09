"""
Example: Using Knowledge Base Reading Tools with Autonomous Agent

This example demonstrates how to use the new KB reading tools:
- kb_read_file: Read files from knowledge base
- kb_list_directory: List directory contents
- kb_search_files: Search files by name/pattern
- kb_search_content: Search by file contents
"""

import asyncio
from pathlib import Path

from src.agents.autonomous_agent import AutonomousAgent


async def example_kb_read_file(agent: AutonomousAgent):
    """Example: Reading files from knowledge base"""
    print("\n=== Example 1: Reading Files ===")

    # Read single file
    result = await agent._tool_kb_read_file({"paths": ["topics/ai/neural-networks.md"]})

    if result["success"]:
        print(f"✓ Read {result['files_read']} file(s)")
        for file_info in result["results"]:
            print(f"  - {file_info['path']}: {file_info['size']} bytes")
            print(f"    Preview: {file_info['content'][:100]}...")
    else:
        print("✗ Failed to read files")

    # Read multiple files
    print("\nReading multiple files...")
    result = await agent._tool_kb_read_file(
        {"paths": ["topics/ai/neural-networks.md", "topics/tech/python.md"]}
    )

    if result["success"]:
        print(f"✓ Read {result['files_read']} files")


async def example_kb_list_directory(agent: AutonomousAgent):
    """Example: Listing directory contents"""
    print("\n=== Example 2: Listing Directories ===")

    # Non-recursive listing
    result = await agent._tool_kb_list_directory({"path": "topics", "recursive": False})

    if result["success"]:
        print(f"✓ Listed directory: {result['path']}")
        print(f"  Files: {result['file_count']}")
        print(f"  Directories: {result['directory_count']}")

        if result["directories"]:
            print("\n  Subdirectories:")
            for dir_info in result["directories"]:
                print(f"    - {dir_info['name']}")

    # Recursive listing
    print("\nRecursive listing...")
    result = await agent._tool_kb_list_directory({"path": "topics/ai", "recursive": True})

    if result["success"]:
        print(f"✓ Found {result['file_count']} files recursively")
        if result["files"]:
            print("  Files:")
            for file_info in result["files"][:5]:  # Show first 5
                print(f"    - {file_info['path']} ({file_info['size']} bytes)")


async def example_kb_search_files(agent: AutonomousAgent):
    """Example: Searching files by name/pattern"""
    print("\n=== Example 3: Searching Files ===")

    # Search all markdown files
    result = await agent._tool_kb_search_files({"pattern": "*.md"})

    if result["success"]:
        print(f"✓ Found {result['file_count']} markdown files")

    # Search files containing "neural" in name
    print("\nSearching for files with 'neural' in name...")
    result = await agent._tool_kb_search_files({"pattern": "*neural*", "case_sensitive": False})

    if result["success"]:
        print(f"✓ Found {result['file_count']} matching files")
        for file_info in result["files"]:
            print(f"  - {file_info['name']}")

    # Search in specific directory
    print("\nSearching in specific directory...")
    result = await agent._tool_kb_search_files({"pattern": "topics/ai/**/*.md"})

    if result["success"]:
        print(f"✓ Found {result['file_count']} files in topics/ai/")


async def example_kb_search_content(agent: AutonomousAgent):
    """Example: Searching by file contents"""
    print("\n=== Example 4: Searching Content ===")

    # Search for "machine learning"
    result = await agent._tool_kb_search_content(
        {"query": "machine learning", "case_sensitive": False, "file_pattern": "*.md"}
    )

    if result["success"]:
        print(f"✓ Found '{result['query']}' in {result['files_found']} files")

        for match in result["matches"][:3]:  # Show first 3
            print(f"\n  File: {match['path']}")
            print(f"  Occurrences: {match['occurrences']}")

            if match["matches"]:
                first_match = match["matches"][0]
                print(f"  Line {first_match['line_number']}: {first_match['line']}")

    # Search with specific file pattern
    print("\nSearching only in AI directory...")
    result = await agent._tool_kb_search_content(
        {"query": "neural", "file_pattern": "topics/ai/*.md"}
    )

    if result["success"]:
        print(f"✓ Found in {result['files_found']} files")


async def example_combined_workflow(agent: AutonomousAgent):
    """Example: Combined workflow using multiple tools"""
    print("\n=== Example 5: Combined Workflow ===")
    print("Task: Find and analyze all AI-related content\n")

    # Step 1: List AI directory
    print("Step 1: Listing AI directory...")
    list_result = await agent._tool_kb_list_directory({"path": "topics/ai", "recursive": False})

    if list_result["success"]:
        print(f"✓ Found {list_result['file_count']} files")

    # Step 2: Search for "neural" in content
    print("\nStep 2: Searching for 'neural' in content...")
    search_result = await agent._tool_kb_search_content(
        {"query": "neural", "file_pattern": "topics/ai/*.md"}
    )

    if search_result["success"]:
        print(f"✓ Found in {search_result['files_found']} files")

        # Step 3: Read those files
        if search_result["matches"]:
            print("\nStep 3: Reading matching files...")
            file_paths = [m["path"] for m in search_result["matches"]]

            read_result = await agent._tool_kb_read_file({"paths": file_paths})

            if read_result["success"]:
                print(f"✓ Read {read_result['files_read']} files")

                # Analyze content
                total_words = sum(len(f["content"].split()) for f in read_result["results"])
                print(f"\nAnalysis:")
                print(f"  Total words: {total_words}")
                print(f"  Average words per file: {total_words // len(read_result['results'])}")


async def example_error_handling(agent: AutonomousAgent):
    """Example: Error handling"""
    print("\n=== Example 6: Error Handling ===")

    # Try to read non-existent file
    print("Attempting to read non-existent file...")
    result = await agent._tool_kb_read_file({"paths": ["topics/nonexistent.md"]})

    if not result["success"]:
        print("✓ Error handled correctly")
        if result.get("errors"):
            print(f"  Error: {result['errors'][0]['error']}")

    # Try path traversal (should be blocked)
    print("\nAttempting path traversal (should be blocked)...")
    result = await agent._tool_kb_read_file({"paths": ["../../../etc/passwd"]})

    if not result["success"]:
        print("✓ Security validation working")
        if result.get("errors"):
            print(f"  Blocked: {result['errors'][0]['error']}")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Knowledge Base Reading Tools - Examples")
    print("=" * 60)

    # Initialize agent with a test KB path
    # In real usage, this would point to your actual knowledge base
    kb_path = Path("./data/test_kb_root")

    # Create test KB structure if it doesn't exist
    kb_path.mkdir(parents=True, exist_ok=True)
    (kb_path / "topics" / "ai").mkdir(parents=True, exist_ok=True)
    (kb_path / "topics" / "tech").mkdir(parents=True, exist_ok=True)

    # Create sample files
    (kb_path / "topics" / "ai" / "neural-networks.md").write_text(
        "# Neural Networks\n\nNeural networks are machine learning models inspired by the brain."
    )
    (kb_path / "topics" / "ai" / "machine-learning.md").write_text(
        "# Machine Learning\n\nMachine learning is a subset of AI."
    )
    (kb_path / "topics" / "tech" / "python.md").write_text(
        "# Python\n\nPython is a versatile programming language."
    )

    # Create agent
    agent = AutonomousAgent(
        llm_connector=None, kb_root_path=kb_path  # No LLM needed for these examples
    )

    # Run examples
    try:
        await example_kb_read_file(agent)
        await example_kb_list_directory(agent)
        await example_kb_search_files(agent)
        await example_kb_search_content(agent)
        await example_combined_workflow(agent)
        await example_error_handling(agent)

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
