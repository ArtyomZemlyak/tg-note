"""
Example: Using Different Memory Storage Types

This example demonstrates the new memory storage architecture with two types:
1. JSON Storage (simple, fast, no ML dependencies)
2. Vector-Based Storage (AI-powered semantic search)

Both implement the same interface, following SOLID principles.
"""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from loguru import logger

# Import the factory and storage types
from src.mcp.memory import MemoryStorage  # Legacy wrapper
from src.mcp.memory import JsonMemoryStorage, MemoryStorageFactory, VectorBasedMemoryStorage


def example_json_storage():
    """Example: Using JSON storage (simple, fast)"""

    logger.info("=== JSON Storage Example ===\n")

    with TemporaryDirectory() as tmpdir:
        # Create JSON storage using factory
        storage = MemoryStorageFactory.create(storage_type="json", data_dir=Path(tmpdir))

        logger.info("1. Storing memories...")

        # Store some memories
        storage.store(
            content="SQL injection vulnerability in login endpoint",
            category="security",
            tags=["vulnerability", "sql"],
        )

        storage.store(
            content="Database uses PostgreSQL 14 with proper indexing",
            category="infrastructure",
            tags=["database", "postgres"],
        )

        storage.store(
            content="Authentication uses JWT tokens with 1-hour expiration",
            category="security",
            tags=["auth", "jwt"],
        )

        logger.info("✓ Stored 3 memories\n")

        # Retrieve with substring search
        logger.info("2. Searching with keyword 'vulnerability'...")
        results = storage.retrieve(query="vulnerability", limit=5)
        logger.info(f"Found {results['count']} memories:")
        for memory in results["memories"]:
            logger.info(f"  - {memory['content'][:60]}...")

        logger.info("\n3. Filtering by category 'security'...")
        results = storage.retrieve(category="security", limit=5)
        logger.info(f"Found {results['count']} memories in 'security' category")

        logger.info("\n4. Listing all categories...")
        categories = storage.list_categories()
        for cat in categories["categories"]:
            logger.info(f"  - {cat['name']}: {cat['count']} memories")


def example_model_storage():
    """Example: Using vector-based storage (semantic search)"""

    logger.info("\n\n=== Vector-Based Storage Example ===\n")

    with TemporaryDirectory() as tmpdir:
        try:
            # Create vector-based storage using factory
            logger.info("Loading model for semantic search...")
            storage = MemoryStorageFactory.create(
                storage_type="vector",
                data_dir=Path(tmpdir),
                model_name="all-MiniLM-L6-v2",  # Small, fast model for demo
            )

            logger.info("✓ Model loaded\n")

            logger.info("1. Storing memories...")

            # Store memories with similar meanings
            storage.store(
                content="Found a security flaw in the authentication system",
                category="security",
                tags=["vulnerability", "auth"],
            )

            storage.store(
                content="The login mechanism has a potential exploit",
                category="security",
                tags=["vulnerability", "login"],
            )

            storage.store(
                content="Database connection pool is well optimized",
                category="performance",
                tags=["database", "optimization"],
            )

            logger.info("✓ Stored 3 memories\n")

            # Semantic search - finds similar meanings, not just keywords
            logger.info("2. Semantic search for 'authentication vulnerability'...")
            logger.info("   (Note: This will find similar concepts, not just exact words)\n")

            results = storage.retrieve(query="authentication vulnerability", limit=5)

            logger.info(f"Found {results['count']} semantically similar memories:")
            for memory in results["memories"]:
                score = memory.get("_score", 0)
                logger.info(f"  - [Score: {score:.3f}] {memory['content'][:70]}...")

            logger.info("\n3. Semantic search for 'login security issue'...")
            results = storage.retrieve(query="login security issue", limit=5)

            logger.info(f"Found {results['count']} semantically similar memories:")
            for memory in results["memories"]:
                score = memory.get("_score", 0)
                logger.info(f"  - [Score: {score:.3f}] {memory['content'][:70]}...")

            logger.info("\n✓ Notice how semantic search finds related concepts!")
            logger.info("  Even though queries use different words, it finds the right memories.")

        except ImportError as e:
            logger.warning(f"Vector-based storage requires additional dependencies: {e}")
            logger.warning("Install with: pip install sentence-transformers transformers torch")
        except Exception as e:
            logger.error(f"Error with vector-based storage: {e}")


def example_legacy_interface():
    """Example: Using legacy MemoryStorage interface (backward compatible)"""

    logger.info("\n\n=== Legacy Interface Example (Backward Compatible) ===\n")

    with TemporaryDirectory() as tmpdir:
        # Old code continues to work - automatically uses JSON storage by default
        storage = MemoryStorage(Path(tmpdir))

        logger.info("Using legacy MemoryStorage class (auto-selects JSON storage)")

        # Same interface as before
        result = storage.store(content="This is a test memory", category="test")
        logger.info(f"✓ Stored memory: {result}")

        results = storage.retrieve(query="test")
        logger.info(f"✓ Retrieved {results['count']} memories")

        logger.info("\n✓ Legacy code works without changes!")


def example_comparison():
    """Example: Comparing JSON vs Vector-based storage"""

    logger.info("\n\n=== Storage Type Comparison ===\n")

    test_memories = [
        "The cat sat on the mat",
        "A feline rested on the carpet",
        "Dogs are great pets",
        "Puppies are very cute animals",
    ]

    query = "kitten on rug"

    with TemporaryDirectory() as tmpdir:
        # JSON Storage
        logger.info("1. JSON Storage (substring search):")
        json_storage = MemoryStorageFactory.create("json", Path(tmpdir) / "json")

        for content in test_memories:
            json_storage.store(content, category="animals")

        results = json_storage.retrieve(query=query, limit=4)
        logger.info(f"   Query: '{query}'")
        logger.info(f"   Found {results['count']} results (substring match)")
        for memory in results["memories"]:
            logger.info(f"   - {memory['content']}")

        # Vector-Based Storage
        try:
            logger.info("\n2. Vector-Based Storage (semantic search):")
            model_storage = MemoryStorageFactory.create(
                "vector", Path(tmpdir) / "vector", model_name="all-MiniLM-L6-v2"
            )

            for content in test_memories:
                model_storage.store(content, category="animals")

            results = model_storage.retrieve(query=query, limit=4)
            logger.info(f"   Query: '{query}'")
            logger.info(f"   Found {results['count']} results (semantic similarity)")
            for memory in results["memories"]:
                score = memory.get("_score", 0)
                logger.info(f"   - [Score: {score:.3f}] {memory['content']}")

            logger.info("\n✓ Semantic search understands 'kitten'≈'cat' and 'rug'≈'mat'!")

        except (ImportError, Exception) as e:
            logger.warning(f"Vector-based storage skipped: {e}")


def main():
    """Run all examples"""

    logger.info("=" * 70)
    logger.info("Memory Storage Types Examples")
    logger.info("=" * 70)

    try:
        # Example 1: JSON storage
        example_json_storage()

        # Example 2: Vector-based storage
        example_model_storage()

        # Example 3: Legacy interface
        example_legacy_interface()

        # Example 4: Comparison
        example_comparison()

        logger.info("\n" + "=" * 70)
        logger.info("All examples completed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO",
    )

    # Run examples
    main()
