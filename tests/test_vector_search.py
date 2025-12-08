"""
Tests for Vector Search Module
"""

import tempfile
from pathlib import Path

import pytest

from src.mcp.vector_search import ChunkingStrategy, DocumentChunker

# Note: These tests only test the chunking functionality
# Full vector search tests require optional dependencies


@pytest.fixture
def temp_kb():
    """Create a temporary knowledge base for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        kb_path = Path(tmpdir)

        # Create test directory structure
        (kb_path / "topics" / "ai").mkdir(parents=True)

        # Create test file with headers
        (kb_path / "topics" / "ai" / "neural-networks.md").write_text(
            "# Neural Networks\n\n"
            "Neural networks are machine learning models.\n\n"
            "## Deep Learning\n\n"
            "Deep learning uses multiple layers.\n\n"
            "## Applications\n\n"
            "Used in computer vision and NLP."
        )

        yield kb_path


def test_chunking_fixed_size():
    """Test fixed size chunking"""
    chunker = DocumentChunker(strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=50, chunk_overlap=0)

    text = "This is a test document with some content. " * 5
    metadata = {"file_path": "test.md"}

    chunks = chunker.chunk_document(text, metadata, "test.md")

    assert len(chunks) > 0
    assert all(len(chunk.text) <= 50 for chunk in chunks)
    assert all(chunk.source_file == "test.md" for chunk in chunks)


def test_chunking_with_overlap():
    """Test chunking with overlap"""
    chunker = DocumentChunker(
        strategy=ChunkingStrategy.FIXED_SIZE_WITH_OVERLAP, chunk_size=100, chunk_overlap=20
    )

    text = "This is a test document. " * 10
    metadata = {"file_path": "test.md"}

    chunks = chunker.chunk_document(text, metadata, "test.md")

    assert len(chunks) > 0
    # Check that chunks overlap
    if len(chunks) > 1:
        # First chunk should be full size
        assert len(chunks[0].text) <= 100


def test_chunking_semantic():
    """Test semantic chunking with headers"""
    chunker = DocumentChunker(
        strategy=ChunkingStrategy.SEMANTIC, chunk_size=500, respect_headers=True
    )

    text = """# Main Title

This is the introduction.

## Section 1

Content of section 1.

## Section 2

Content of section 2.

### Subsection 2.1

More content here.
"""

    metadata = {"file_path": "test.md"}
    chunks = chunker.chunk_document(text, metadata, "test.md")

    assert len(chunks) > 0
    # Check that headers are preserved in metadata
    header_chunks = [c for c in chunks if "header" in c.metadata]
    assert len(header_chunks) > 0


def test_chunking_paragraph_splitting():
    """Test paragraph-based splitting"""
    chunker = DocumentChunker(
        strategy=ChunkingStrategy.SEMANTIC, chunk_size=100, respect_headers=False
    )

    text = """This is paragraph one.

This is paragraph two with more content.

This is paragraph three."""

    metadata = {"file_path": "test.md"}
    chunks = chunker.chunk_document(text, metadata, "test.md")

    assert len(chunks) > 0


def test_empty_text():
    """Test handling of empty text"""
    chunker = DocumentChunker(strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=100)

    chunks = chunker.chunk_document("", {}, "empty.md")
    assert len(chunks) == 0


def test_very_long_paragraph():
    """Test handling of paragraph longer than chunk size"""
    chunker = DocumentChunker(
        strategy=ChunkingStrategy.SEMANTIC, chunk_size=50, chunk_overlap=10, respect_headers=False
    )

    # Create a very long paragraph (no double newlines)
    text = "This is a very long paragraph without breaks. " * 10

    chunks = chunker.chunk_document(text, {}, "long.md")

    # Should split into multiple chunks
    assert len(chunks) > 1


def test_chunk_metadata():
    """Test that chunk metadata is preserved"""
    chunker = DocumentChunker(strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=100)

    metadata = {"file_path": "test.md", "author": "Test Author", "category": "test"}

    text = "Test content " * 20
    chunks = chunker.chunk_document(text, metadata, "test.md")

    # Check that metadata is preserved in all chunks
    for chunk in chunks:
        assert chunk.metadata["file_path"] == "test.md"
        assert chunk.metadata["author"] == "Test Author"
        assert chunk.metadata["category"] == "test"


def test_chunk_indices():
    """Test that chunk indices are sequential"""
    chunker = DocumentChunker(strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=50)

    text = "Test content " * 20
    chunks = chunker.chunk_document(text, {}, "test.md")

    # Check indices are sequential starting from 0
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


@pytest.mark.asyncio
async def test_chunker_integration(temp_kb):
    """Integration test with actual file"""
    file_path = temp_kb / "topics" / "ai" / "neural-networks.md"
    content = file_path.read_text()

    chunker = DocumentChunker(
        strategy=ChunkingStrategy.SEMANTIC, chunk_size=200, respect_headers=True
    )

    metadata = {"file_path": "topics/ai/neural-networks.md"}
    chunks = chunker.chunk_document(content, metadata, "topics/ai/neural-networks.md")

    assert len(chunks) > 0
    # Should have multiple chunks due to headers
    assert len(chunks) >= 3  # Main title + at least 2 sections

    # Check that headers are captured
    headers_found = []
    for chunk in chunks:
        if "header" in chunk.metadata:
            headers_found.append(chunk.metadata["header"])

    # Should find at least the section headers
    assert len(headers_found) > 0


@pytest.mark.asyncio
async def test_manager_deletion_support():
    """Test that manager properly handles deletion logic without filesystem coupling"""
    from src.mcp.vector_search.manager import VectorSearchManager
    from src.mcp.vector_search.vector_stores import BaseVectorStore

    class InMemoryVectorStore(BaseVectorStore):
        """Simple in-memory store with deletion support for testing"""

        def __init__(self):
            self.documents = []

        async def add_documents(self, embeddings, documents, ids=None):
            self.documents.extend(documents)

        async def search(self, query_embedding, top_k=5, filter_dict=None):
            return []

        async def clear(self):
            self.documents = []

        async def get_count(self):
            return len(self.documents)

        async def save(self, path):
            return None

        async def load(self, path):
            return None

        def supports_delete_by_filter(self) -> bool:
            return True

        async def delete_by_filter(self, filter_dict):
            doc_id = filter_dict.get("document_id")
            before = len(self.documents)
            self.documents = [doc for doc in self.documents if doc.get("document_id") != doc_id]
            return before - len(self.documents)

    # Create a mock embedder
    class MockEmbedder:
        def __init__(self):
            self.model_name = "mock"
            self._dimension = 384

        async def embed_texts(self, texts):
            return [[0.0 for _ in range(self._dimension)] for _ in texts]

        async def embed_query(self, query):
            return [0.0 for _ in range(self._dimension)]

        def get_dimension(self):
            return self._dimension

        def get_model_hash(self):
            return "mock_hash"

    with tempfile.TemporaryDirectory() as tmpdir:
        embedder = MockEmbedder()
        vector_store = InMemoryVectorStore()
        chunker = DocumentChunker(strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=100)

        manager = VectorSearchManager(
            embedder=embedder,
            vector_store=vector_store,
            chunker=chunker,
            index_path=Path(tmpdir) / "index",
        )

        await manager.initialize()

        # Index initial document
        add_stats = await manager.add_documents(
            [
                {
                    "id": "file1.md",
                    "content": "# File 1\n\nContent",
                    "metadata": {"file_path": "file1.md"},
                }
            ]
        )
        assert add_stats["documents_processed"] == 1
        assert len(manager._indexed_documents) == 1

        # Delete the document by ID
        delete_stats = await manager.delete_documents(["file1.md"])
        assert delete_stats["documents_deleted"] == 1
        assert len(manager._indexed_documents) == 0
        assert await vector_store.get_count() == 0


@pytest.mark.asyncio
async def test_update_documents_aborts_when_delete_not_supported():
    """Update should halt when vector store cannot delete"""
    from src.mcp.vector_search.manager import VectorSearchManager
    from src.mcp.vector_search.vector_stores import BaseVectorStore

    class NonDeletingVectorStore(BaseVectorStore):
        """Vector store without deletion support for update flow tests"""

        def __init__(self):
            self.documents = []

        async def add_documents(self, embeddings, documents, ids=None):
            self.documents.extend(documents)

        async def search(self, query_embedding, top_k=5, filter_dict=None):
            return []

        async def clear(self):
            self.documents = []

        async def get_count(self):
            return len(self.documents)

        async def save(self, path):
            return None

        async def load(self, path):
            return None

        def supports_delete_by_filter(self) -> bool:
            return False

        async def delete_by_filter(self, filter_dict):
            raise RuntimeError("Delete should not be called")

    class MockEmbedder:
        def __init__(self):
            self.model_name = "mock"
            self._dimension = 384

        async def embed_texts(self, texts):
            return [[0.0 for _ in range(self._dimension)] for _ in texts]

        async def embed_query(self, query):
            return [0.0 for _ in range(self._dimension)]

        def get_dimension(self):
            return self._dimension

        def get_model_hash(self):
            return "mock_hash"

    with tempfile.TemporaryDirectory() as tmpdir:
        embedder = MockEmbedder()
        vector_store = NonDeletingVectorStore()
        chunker = DocumentChunker(strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=100)

        manager = VectorSearchManager(
            embedder=embedder,
            vector_store=vector_store,
            chunker=chunker,
            index_path=Path(tmpdir) / "index",
        )

        await manager.initialize()

        update_stats = await manager.update_documents(
            [
                {
                    "id": "file1.md",
                    "content": "# File 1\n\nContent",
                    "metadata": {"file_path": "file1.md"},
                }
            ]
        )

        assert update_stats["success"] is False
        assert update_stats["documents_updated"] == 0
        assert update_stats["chunks_created"] == 0
        assert update_stats["documents_deleted"] == 0
        assert "Vector store does not support deletions" in update_stats["errors"][0]
        assert vector_store.documents == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
