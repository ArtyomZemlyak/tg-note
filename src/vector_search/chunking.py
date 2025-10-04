"""
Document Chunking
Provides different strategies for splitting documents into chunks
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

from loguru import logger


class ChunkingStrategy(Enum):
    """Document chunking strategies"""
    FIXED_SIZE = "fixed_size"  # Fixed character/token chunks
    FIXED_SIZE_WITH_OVERLAP = "fixed_size_overlap"  # With overlap between chunks
    SEMANTIC = "semantic"  # Split by headers and structure


@dataclass
class DocumentChunk:
    """A chunk of a document"""
    text: str
    metadata: Dict[str, Any]
    chunk_index: int
    source_file: str
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class DocumentChunker:
    """Splits documents into chunks using various strategies"""
    
    def __init__(
        self,
        strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE_WITH_OVERLAP,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        respect_headers: bool = True
    ):
        """
        Initialize document chunker
        
        Args:
            strategy: Chunking strategy to use
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks (for FIXED_SIZE_WITH_OVERLAP)
            respect_headers: Whether to split by markdown headers (for SEMANTIC)
        """
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_headers = respect_headers
    
    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, Any],
        source_file: str
    ) -> List[DocumentChunk]:
        """
        Chunk a document according to the strategy
        
        Args:
            text: Document text
            metadata: Document metadata
            source_file: Source file path
            
        Returns:
            List of document chunks
        """
        if self.strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(text, metadata, source_file)
        elif self.strategy == ChunkingStrategy.FIXED_SIZE_WITH_OVERLAP:
            return self._chunk_fixed_size_overlap(text, metadata, source_file)
        elif self.strategy == ChunkingStrategy.SEMANTIC:
            return self._chunk_semantic(text, metadata, source_file)
        else:
            raise ValueError(f"Unknown chunking strategy: {self.strategy}")
    
    def _chunk_fixed_size(
        self,
        text: str,
        metadata: Dict[str, Any],
        source_file: str
    ) -> List[DocumentChunk]:
        """Split into fixed-size chunks without overlap"""
        chunks = []
        
        for i in range(0, len(text), self.chunk_size):
            chunk_text = text[i:i + self.chunk_size]
            if chunk_text.strip():  # Skip empty chunks
                chunks.append(
                    DocumentChunk(
                        text=chunk_text,
                        metadata=metadata.copy(),
                        chunk_index=len(chunks),
                        source_file=source_file,
                        start_char=i,
                        end_char=i + len(chunk_text)
                    )
                )
        
        logger.debug(f"Created {len(chunks)} fixed-size chunks from {source_file}")
        return chunks
    
    def _chunk_fixed_size_overlap(
        self,
        text: str,
        metadata: Dict[str, Any],
        source_file: str
    ) -> List[DocumentChunk]:
        """Split into fixed-size chunks with overlap"""
        chunks = []
        stride = self.chunk_size - self.chunk_overlap
        
        if stride <= 0:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        
        for i in range(0, len(text), stride):
            chunk_text = text[i:i + self.chunk_size]
            if chunk_text.strip():  # Skip empty chunks
                chunks.append(
                    DocumentChunk(
                        text=chunk_text,
                        metadata=metadata.copy(),
                        chunk_index=len(chunks),
                        source_file=source_file,
                        start_char=i,
                        end_char=i + len(chunk_text)
                    )
                )
            
            # Stop if we've reached the end
            if i + self.chunk_size >= len(text):
                break
        
        logger.debug(
            f"Created {len(chunks)} overlapping chunks from {source_file} "
            f"(overlap: {self.chunk_overlap})"
        )
        return chunks
    
    def _chunk_semantic(
        self,
        text: str,
        metadata: Dict[str, Any],
        source_file: str
    ) -> List[DocumentChunk]:
        """
        Split by semantic boundaries (headers, paragraphs)
        
        For markdown documents, splits by headers while respecting chunk size limits
        """
        chunks = []
        
        if self.respect_headers:
            # Try to split by markdown headers
            chunks = self._split_by_headers(text, metadata, source_file)
        
        # If no header-based chunks or not markdown, fall back to paragraph splitting
        if not chunks:
            chunks = self._split_by_paragraphs(text, metadata, source_file)
        
        logger.debug(f"Created {len(chunks)} semantic chunks from {source_file}")
        return chunks
    
    def _split_by_headers(
        self,
        text: str,
        metadata: Dict[str, Any],
        source_file: str
    ) -> List[DocumentChunk]:
        """Split markdown by headers"""
        # Regex to match markdown headers (# Header)
        header_pattern = r'^(#{1,6})\s+(.+)$'
        
        sections = []
        current_section = []
        current_header = None
        current_level = 0
        
        for line in text.split('\n'):
            header_match = re.match(header_pattern, line)
            
            if header_match:
                # Save previous section
                if current_section:
                    sections.append({
                        'header': current_header,
                        'level': current_level,
                        'text': '\n'.join(current_section)
                    })
                
                # Start new section
                current_level = len(header_match.group(1))
                current_header = header_match.group(2)
                current_section = [line]
            else:
                current_section.append(line)
        
        # Add last section
        if current_section:
            sections.append({
                'header': current_header,
                'level': current_level,
                'text': '\n'.join(current_section)
            })
        
        # Convert sections to chunks, splitting if too large
        chunks = []
        for section in sections:
            section_text = section['text']
            section_metadata = metadata.copy()
            if section['header']:
                section_metadata['header'] = section['header']
                section_metadata['header_level'] = section['level']
            
            # If section is small enough, use as-is
            if len(section_text) <= self.chunk_size:
                chunks.append(
                    DocumentChunk(
                        text=section_text,
                        metadata=section_metadata,
                        chunk_index=len(chunks),
                        source_file=source_file
                    )
                )
            else:
                # Split large section into smaller chunks
                sub_chunks = self._chunk_fixed_size_overlap(
                    section_text,
                    section_metadata,
                    source_file
                )
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _split_by_paragraphs(
        self,
        text: str,
        metadata: Dict[str, Any],
        source_file: str
    ) -> List[DocumentChunk]:
        """Split by paragraphs (double newline)"""
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # If paragraph alone is too large, split it
            if para_size > self.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(
                        DocumentChunk(
                            text=chunk_text,
                            metadata=metadata.copy(),
                            chunk_index=len(chunks),
                            source_file=source_file
                        )
                    )
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph
                sub_chunks = self._chunk_fixed_size_overlap(
                    para,
                    metadata,
                    source_file
                )
                chunks.extend(sub_chunks)
            
            # If adding this paragraph would exceed chunk size
            elif current_size + para_size + 2 > self.chunk_size:  # +2 for \n\n
                # Save current chunk
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(
                        DocumentChunk(
                            text=chunk_text,
                            metadata=metadata.copy(),
                            chunk_index=len(chunks),
                            source_file=source_file
                        )
                    )
                
                # Start new chunk with this paragraph
                current_chunk = [para]
                current_size = para_size
            
            else:
                # Add to current chunk
                current_chunk.append(para)
                current_size += para_size + 2  # +2 for \n\n
        
        # Add last chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(
                DocumentChunk(
                    text=chunk_text,
                    metadata=metadata.copy(),
                    chunk_index=len(chunks),
                    source_file=source_file
                )
            )
        
        return chunks
