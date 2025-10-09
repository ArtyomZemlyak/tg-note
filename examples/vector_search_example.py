"""
Example: Using Vector Search with Autonomous Agent

This example demonstrates how to configure and use vector search capabilities:
- Setting up embedding models (sentence-transformers, OpenAI, Infinity)
- Configuring vector stores (FAISS, Qdrant)
- Indexing knowledge base
- Performing semantic search
"""

import asyncio
from pathlib import Path

from src.agents.autonomous_agent import AutonomousAgent
from src.vector_search import (
    ChunkingStrategy,
    DocumentChunker,
    FAISSVectorStore,
    InfinityEmbedder,
    OpenAIEmbedder,
    QdrantVectorStore,
    SentenceTransformerEmbedder,
    VectorSearchManager,
)


async def setup_vector_search_local():
    """
    Setup vector search with local components:
    - sentence-transformers for embeddings
    - FAISS for vector storage
    """
    print("\n=== Setup 1: Local Vector Search (sentence-transformers + FAISS) ===\n")

    # Setup paths
    kb_root = Path("./data/test_kb_root")
    kb_root.mkdir(parents=True, exist_ok=True)

    # Create sample documents
    (kb_root / "ai").mkdir(exist_ok=True)
    (kb_root / "ai" / "neural-networks.md").write_text(
        """
# Neural Networks

Neural networks are computational models inspired by biological neural networks.

## Architecture

They consist of interconnected nodes (neurons) organized in layers.

## Applications

- Computer vision
- Natural language processing
- Speech recognition
"""
    )

    (kb_root / "ai" / "transformers.md").write_text(
        """
# Transformer Architecture

The Transformer is a neural network architecture based on self-attention mechanisms.

## Key Features

- Self-attention mechanism
- Parallel processing
- Long-range dependencies

## Applications

Used in modern NLP models like GPT, BERT, and others.
"""
    )

    # Initialize embedding model
    print("Loading sentence-transformers model...")
    embedder = SentenceTransformerEmbedder(model_name="all-MiniLM-L6-v2")

    # Initialize vector store
    dimension = embedder.get_dimension()
    print(f"Embedding dimension: {dimension}")

    vector_store = FAISSVectorStore(dimension=dimension)

    # Initialize document chunker
    chunker = DocumentChunker(
        strategy=ChunkingStrategy.SEMANTIC, chunk_size=512, chunk_overlap=50, respect_headers=True
    )

    # Create vector search manager
    manager = VectorSearchManager(
        embedder=embedder, vector_store=vector_store, chunker=chunker, kb_root_path=kb_root
    )

    # Initialize and index
    print("\nInitializing vector search manager...")
    await manager.initialize()

    print("\nIndexing knowledge base...")
    stats = await manager.index_knowledge_base()

    print(f"\nIndexing complete:")
    print(f"  Files processed: {stats['files_processed']}")
    print(f"  Chunks created: {stats['chunks_created']}")
    if stats["errors"]:
        print(f"  Errors: {len(stats['errors'])}")

    return manager, kb_root


async def search_examples(manager: VectorSearchManager):
    """Demonstrate different search queries"""
    print("\n=== Search Examples ===\n")

    queries = [
        "How do neural networks work?",
        "What is attention mechanism?",
        "Applications of deep learning",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 60)

        results = await manager.search(query=query, top_k=3)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result['score']:.4f}")
            print(f"   File: {result['file_path']}")
            if "header" in result:
                print(f"   Section: {result['header']}")
            print(f"   Text preview: {result['text'][:150]}...")


async def setup_vector_search_openai():
    """
    Setup vector search with OpenAI:
    - OpenAI embeddings
    - FAISS for local storage
    """
    print("\n=== Setup 2: OpenAI Embeddings + FAISS ===\n")

    # Note: Requires OPENAI_API_KEY environment variable
    import os

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set, skipping OpenAI example")
        return None, None

    kb_root = Path("./data/test_kb_root")

    # Initialize OpenAI embedder
    print("Initializing OpenAI embedder...")
    embedder = OpenAIEmbedder(model_name="text-embedding-ada-002", api_key=api_key)

    # Initialize FAISS store
    dimension = embedder.get_dimension()
    vector_store = FAISSVectorStore(dimension=dimension)

    # Initialize chunker
    chunker = DocumentChunker(
        strategy=ChunkingStrategy.FIXED_SIZE_WITH_OVERLAP, chunk_size=512, chunk_overlap=50
    )

    # Create manager
    manager = VectorSearchManager(
        embedder=embedder, vector_store=vector_store, chunker=chunker, kb_root_path=kb_root
    )

    await manager.initialize()
    stats = await manager.index_knowledge_base()

    print(f"\nIndexed {stats['files_processed']} files with OpenAI embeddings")

    return manager, kb_root


async def setup_vector_search_qdrant():
    """
    Setup vector search with Qdrant:
    - sentence-transformers for embeddings
    - Qdrant for vector storage (requires running Qdrant server)
    """
    print("\n=== Setup 3: sentence-transformers + Qdrant ===\n")

    kb_root = Path("./data/test_kb_root")

    # Initialize embedder
    embedder = SentenceTransformerEmbedder(model_name="all-MiniLM-L6-v2")
    dimension = embedder.get_dimension()

    # Initialize Qdrant vector store
    print("Connecting to Qdrant...")
    try:
        vector_store = QdrantVectorStore(
            collection_name="knowledge_base_test", dimension=dimension, url="http://localhost:6333"
        )

        # Initialize chunker
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.SEMANTIC, chunk_size=512, respect_headers=True
        )

        # Create manager
        manager = VectorSearchManager(
            embedder=embedder, vector_store=vector_store, chunker=chunker, kb_root_path=kb_root
        )

        await manager.initialize()
        stats = await manager.index_knowledge_base()

        print(f"\nIndexed {stats['files_processed']} files in Qdrant")

        return manager, kb_root

    except Exception as e:
        print(f"⚠️  Could not connect to Qdrant: {e}")
        print("   Make sure Qdrant is running at http://localhost:6333")
        return None, None


async def setup_with_agent():
    """Setup autonomous agent with vector search"""
    print("\n=== Setup 4: Autonomous Agent with Vector Search ===\n")

    # Setup vector search
    manager, kb_root = await setup_vector_search_local()

    # Create agent with vector search enabled
    agent = AutonomousAgent(
        llm_connector=None,  # Can add LLM connector here
        kb_root_path=kb_root,
        enable_vector_search=True,
        vector_search_manager=manager,
    )

    print("\n✓ Agent created with vector search enabled")
    print(f"  Available tools: {list(agent.tools.keys())}")

    # Test vector search tool
    print("\n--- Testing kb_vector_search tool ---")
    result = await agent._tool_kb_vector_search(
        {"query": "neural network architecture", "top_k": 3}
    )

    if result["success"]:
        print(f"✓ Found {result['results_count']} results")
        for i, res in enumerate(result["results"][:2], 1):
            print(f"  {i}. {res['file_path']} (score: {res['score']:.4f})")
    else:
        print(f"✗ Search failed: {result['error']}")

    # Test reindexing tool
    print("\n--- Testing kb_reindex_vector tool ---")
    result = await agent._tool_kb_reindex_vector({"force": False})

    if result["success"]:
        print("✓ Reindexing complete")
        print(f"  {result['stats']}")
    else:
        print(f"✗ Reindexing failed: {result['error']}")

    return agent, manager


async def compare_search_methods():
    """Compare text search vs vector search"""
    print("\n=== Comparison: Text Search vs Vector Search ===\n")

    manager, kb_root = await setup_vector_search_local()

    query = "learning from data"

    # Vector search
    print(f"Query: '{query}'")
    print("\nVector Search (semantic):")
    vector_results = await manager.search(query=query, top_k=3)

    for i, result in enumerate(vector_results, 1):
        print(f"  {i}. {result['file_path']} (score: {result['score']:.4f})")
        print(f"     Preview: {result['text'][:100]}...")

    # Text search (simple keyword matching)
    print("\nText Search (keyword matching):")
    print("  Would look for exact matches of 'learning' and 'data'")
    print("  Vector search finds semantically similar content even without exact keywords")


async def demonstrate_chunking_strategies():
    """Demonstrate different chunking strategies"""
    print("\n=== Chunking Strategies Comparison ===\n")

    sample_text = """# Machine Learning

Machine learning is a subset of artificial intelligence.

## Supervised Learning

In supervised learning, models learn from labeled data.

### Classification

Classification predicts discrete categories.

### Regression

Regression predicts continuous values.

## Unsupervised Learning

Unsupervised learning works with unlabeled data.
"""

    strategies = [
        (ChunkingStrategy.FIXED_SIZE, "Fixed Size (100 chars)"),
        (ChunkingStrategy.FIXED_SIZE_WITH_OVERLAP, "Fixed Size with Overlap"),
        (ChunkingStrategy.SEMANTIC, "Semantic (by headers)"),
    ]

    for strategy, name in strategies:
        print(f"\n{name}:")
        print("-" * 60)

        chunker = DocumentChunker(
            strategy=strategy, chunk_size=100, chunk_overlap=20, respect_headers=True
        )

        chunks = chunker.chunk_document(
            text=sample_text, metadata={"file": "test.md"}, source_file="test.md"
        )

        print(f"Generated {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks[:3], 1):  # Show first 3
            print(f"\n  Chunk {i} ({len(chunk.text)} chars):")
            if "header" in chunk.metadata:
                print(f"    Header: {chunk.metadata['header']}")
            print(f"    Text: {chunk.text[:80]}...")


async def main():
    """Run all examples"""
    print("=" * 70)
    print("Vector Search Examples")
    print("=" * 70)

    try:
        # Example 1: Local setup with sentence-transformers
        manager, kb_root = await setup_vector_search_local()
        await search_examples(manager)

        # Example 2: Compare chunking strategies
        await demonstrate_chunking_strategies()

        # Example 3: Compare search methods
        await compare_search_methods()

        # Example 4: OpenAI embeddings (if API key available)
        openai_manager, _ = await setup_vector_search_openai()
        if openai_manager:
            await search_examples(openai_manager)

        # Example 5: Qdrant (if server running)
        qdrant_manager, _ = await setup_vector_search_qdrant()
        if qdrant_manager:
            print("\n✓ Qdrant integration working")

        # Example 6: Integration with agent
        await setup_with_agent()

        print("\n" + "=" * 70)
        print("All examples completed!")
        print("=" * 70)

        print("\nNext steps:")
        print("  1. Install optional dependencies: pip install -e '.[vector-search]'")
        print("  2. Configure vector search in config.yaml")
        print("  3. Enable vector search in agent settings")
        print("  4. For GPU acceleration: pip install faiss-gpu")

    except ImportError as e:
        print(f"\n⚠️  Missing dependency: {e}")
        print("\nInstall vector search dependencies:")
        print("  pip install sentence-transformers faiss-cpu qdrant-client")
        print("\nOr install all optional dependencies:")
        print("  pip install -e '.[vector-search]'")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
