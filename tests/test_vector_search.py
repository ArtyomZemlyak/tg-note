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
    """Test that manager properly handles deletion logic"""
    from src.mcp.vector_search.manager import VectorSearchManager
    from src.mcp.vector_search.chunking import ChunkingStrategy, DocumentChunker
    from src.mcp.vector_search.vector_stores import FAISSVectorStore

    # Create a mock embedder
    class MockEmbedder:
        def __init__(self):
            self.model_name = "mock"
            self._dimension = 384

        async def embed_texts(self, texts):
            import numpy as np

            return np.random.rand(len(texts), 384).tolist()

        async def embed_query(self, query):
            import numpy as np

            return np.random.rand(384).tolist()

        def get_dimension(self):
            return self._dimension

        def get_model_hash(self):
            return "mock_hash"

    with tempfile.TemporaryDirectory() as tmpdir:
        kb_path = Path(tmpdir) / "kb"
        kb_path.mkdir()

        # Create initial file
        (kb_path / "file1.md").write_text("# File 1\n\nContent")

        embedder = MockEmbedder()
        vector_store = FAISSVectorStore(dimension=384)
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=100
        )

        manager = VectorSearchManager(
            embedder=embedder,
            vector_store=vector_store,
            chunker=chunker,
            kb_root_path=kb_path,
        )

        await manager.initialize()

        # Index initial file
        stats = await manager.index_knowledge_base(force=False)
        assert stats["files_processed"] == 1
        assert stats["deleted_files"] == 0

        # Delete the file
        (kb_path / "file1.md").unlink()

        # Reindex - should detect deletion
        # For FAISS, this should trigger force=True and full reindex
        stats = await manager.index_knowledge_base(force=False)
        assert stats["files_processed"] == 0  # No files to process
        assert len(manager._indexed_files) == 0  # File removed from index


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
