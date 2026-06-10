"""Base chunker interface for code chunking strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..ingestion import FileContent


@dataclass
class CodeChunk:
    """Represents a chunk of code for embedding."""
    
    # Content
    content: str  # The chunk text
    
    # Identification
    chunk_id: str  # Unique ID for this chunk
    file_path: str  # Source file path
    
    # Location
    start_line: int
    end_line: int
    
    # Context
    chunk_type: str  # "function", "class", "method", "module", "docstring"
    name: Optional[str] = None  # Function/class name if applicable
    parent: Optional[str] = None  # Parent class if method
    
    # For retrieval
    language: str = "python"
    imports: List[str] = field(default_factory=list)
    
    # Metadata for filtering/display
    metadata: Dict = field(default_factory=dict)
    
    def to_embedding_text(self) -> str:
        """Format chunk for embedding.
        
        Includes context like file path and type for better retrieval.
        """
        parts = []
        
        # Add context header
        parts.append(f"# File: {self.file_path}")
        if self.name:
            parts.append(f"# {self.chunk_type.title()}: {self.name}")
        if self.parent:
            parts.append(f"# Class: {self.parent}")
        
        parts.append("")  # Empty line
        parts.append(self.content)
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "content": self.content,
            "chunk_id": self.chunk_id,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "chunk_type": self.chunk_type,
            "name": self.name,
            "parent": self.parent,
            "language": self.language,
            "imports": self.imports,
            "metadata": self.metadata,
        }


class BaseChunker(ABC):
    """Abstract base class for code chunking strategies."""
    
    @abstractmethod
    def chunk_file(self, file_content: FileContent) -> List[CodeChunk]:
        """Chunk a single file.
        
        Args:
            file_content: FileContent object from loader
            
        Returns:
            List of CodeChunk objects
        """
        pass
    
    def chunk_files(self, files: List[FileContent]) -> List[CodeChunk]:
        """Chunk multiple files.
        
        Args:
            files: List of FileContent objects
            
        Returns:
            List of all CodeChunk objects
        """
        all_chunks = []
        
        for file in files:
            chunks = self.chunk_file(file)
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def _generate_chunk_id(
        self,
        file_path: str,
        chunk_type: str,
        name: Optional[str] = None,
        start_line: int = 0
    ) -> str:
        """Generate unique chunk ID."""
        parts = [file_path.replace("/", "_").replace(".", "_")]
        parts.append(chunk_type)
        if name:
            parts.append(name)
        parts.append(str(start_line))
        
        return "_".join(parts)
