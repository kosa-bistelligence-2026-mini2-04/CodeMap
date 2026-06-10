"""AST-based chunker for intelligent code splitting."""

from typing import List, Optional

from ..ingestion import FileContent, CodeElement, get_parser
from ..utils import config, logger
from .base_chunker import BaseChunker, CodeChunk


class ASTChunker(BaseChunker):
    """Chunk code based on AST structure.
    
    This chunker understands code structure and creates chunks at
    meaningful boundaries (functions, classes, methods) rather than
    arbitrary character limits.
    """
    
    def __init__(
        self,
        max_chunk_size: Optional[int] = None,
        include_docstrings: bool = True,
        include_imports: bool = True,
    ):
        """Initialize AST chunker.
        
        Args:
            max_chunk_size: Max characters per chunk (splits large functions)
            include_docstrings: Include docstrings in chunks
            include_imports: Track imports for context
        """
        self.max_chunk_size = max_chunk_size or config.get("chunking.max_chunk_size", 1500)
        self.include_docstrings = include_docstrings
        self.include_imports = include_imports
    
    def chunk_file(self, file_content: FileContent) -> List[CodeChunk]:
        """Chunk a file using AST parsing.
        
        Args:
            file_content: FileContent object from loader
            
        Returns:
            List of CodeChunk objects
        """
        chunks = []
        
        # Get appropriate parser
        parser = get_parser(file_content.language)
        
        # Parse file into elements
        elements = parser.parse(
            file_content.content,
            file_content.path
        )
        
        logger.debug(f"Parsed {len(elements)} elements from {file_content.path}")
        
        # Convert elements to chunks
        for element in elements:
            element_chunks = self._element_to_chunks(element, file_content)
            chunks.extend(element_chunks)
        
        return chunks
    
    def _element_to_chunks(
        self,
        element: CodeElement,
        file_content: FileContent
    ) -> List[CodeChunk]:
        """Convert a CodeElement to one or more chunks.
        
        Large elements may be split into multiple chunks.
        """
        chunks = []
        
        content = element.content
        
        # Check if we need to split
        if len(content) > self.max_chunk_size and element.element_type != "class":
            # Split large functions/modules
            split_chunks = self._split_large_element(element, file_content)
            chunks.extend(split_chunks)
        else:
            # Create single chunk
            chunk = self._create_chunk(element, file_content, content)
            chunks.append(chunk)
        
        # Optionally create separate docstring chunk for better retrieval
        if self.include_docstrings and element.docstring:
            docstring_chunk = self._create_docstring_chunk(element, file_content)
            if docstring_chunk:
                chunks.append(docstring_chunk)
        
        return chunks
    
    def _create_chunk(
        self,
        element: CodeElement,
        file_content: FileContent,
        content: str,
        suffix: str = ""
    ) -> CodeChunk:
        """Create a CodeChunk from a CodeElement."""
        
        chunk_id = self._generate_chunk_id(
            file_content.path,
            element.element_type,
            element.name,
            element.start_line
        )
        if suffix:
            chunk_id += f"_{suffix}"
        
        return CodeChunk(
            content=content,
            chunk_id=chunk_id,
            file_path=file_content.path,
            start_line=element.start_line,
            end_line=element.end_line,
            chunk_type=element.element_type,
            name=element.name,
            parent=element.parent,
            language=file_content.language,
            imports=element.imports if self.include_imports else [],
            metadata={
                "repo_name": file_content.metadata.get("repo_name", ""),
                "docstring": element.docstring[:200] if element.docstring else None,
                "calls": element.calls[:10],  # Limit for storage
                **element.metadata
            }
        )
    
    def _create_docstring_chunk(
        self,
        element: CodeElement,
        file_content: FileContent
    ) -> Optional[CodeChunk]:
        """Create a separate chunk for docstring.
        
        This helps with retrieval when users ask about what a function does.
        """
        if not element.docstring or len(element.docstring) < 50:
            return None
        
        # Format docstring with context
        content = f'"""{element.docstring}"""\n\n# From: {element.element_type} {element.name}'
        
        chunk_id = self._generate_chunk_id(
            file_content.path,
            "docstring",
            element.name,
            element.start_line
        )
        
        return CodeChunk(
            content=content,
            chunk_id=chunk_id,
            file_path=file_content.path,
            start_line=element.start_line,
            end_line=element.start_line,
            chunk_type="docstring",
            name=f"{element.name}_docstring",
            parent=element.parent,
            language="text",
            metadata={
                "original_element": element.name,
                "original_type": element.element_type,
            }
        )
    
    def _split_large_element(
        self,
        element: CodeElement,
        file_content: FileContent
    ) -> List[CodeChunk]:
        """Split a large element into multiple chunks.
        
        For large functions, we split by logical boundaries
        (try to split at empty lines or statement boundaries).
        """
        chunks = []
        content = element.content
        lines = content.split("\n")
        
        current_chunk_lines = []
        current_size = 0
        chunk_index = 0
        
        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline
            
            # Check if adding this line exceeds limit
            if current_size + line_size > self.max_chunk_size and current_chunk_lines:
                # Save current chunk
                chunk_content = "\n".join(current_chunk_lines)
                chunk = self._create_chunk(
                    element,
                    file_content,
                    chunk_content,
                    suffix=f"part{chunk_index}"
                )
                chunk.start_line = element.start_line + (i - len(current_chunk_lines))
                chunk.end_line = element.start_line + i - 1
                chunks.append(chunk)
                
                # Start new chunk with context
                current_chunk_lines = [f"# ... continued from {element.name}"]
                current_size = len(current_chunk_lines[0])
                chunk_index += 1
            
            current_chunk_lines.append(line)
            current_size += line_size
        
        # Don't forget the last chunk
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            chunk = self._create_chunk(
                element,
                file_content,
                chunk_content,
                suffix=f"part{chunk_index}" if chunk_index > 0 else ""
            )
            chunks.append(chunk)
        
        return chunks


class SemanticChunker(BaseChunker):
    """Fallback chunker using text-based semantic splitting.
    
    Used for non-code files or when AST parsing fails.
    """
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        """Initialize semantic chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size or config.get("chunking.max_chunk_size", 1500)
        self.chunk_overlap = chunk_overlap or config.get("chunking.chunk_overlap", 200)
    
    def chunk_file(self, file_content: FileContent) -> List[CodeChunk]:
        """Chunk file by text splitting."""
        chunks = []
        content = file_content.content
        
        # Split by paragraphs/sections first
        sections = self._split_by_sections(content)
        
        for i, section in enumerate(sections):
            if len(section) <= self.chunk_size:
                # Section fits in one chunk
                chunk = CodeChunk(
                    content=section,
                    chunk_id=self._generate_chunk_id(
                        file_content.path, "section", None, i
                    ),
                    file_path=file_content.path,
                    start_line=1,  # Approximate
                    end_line=section.count("\n") + 1,
                    chunk_type="section",
                    language=file_content.language,
                    metadata={"section_index": i}
                )
                chunks.append(chunk)
            else:
                # Split section further
                sub_chunks = self._split_section(section, file_content, i)
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _split_by_sections(self, content: str) -> List[str]:
        """Split content by logical sections."""
        # Split by double newlines (paragraphs) or markdown headers
        sections = []
        current = []
        
        for line in content.split("\n"):
            if line.startswith("#") or (not line.strip() and current):
                if current:
                    sections.append("\n".join(current))
                    current = []
            current.append(line)
        
        if current:
            sections.append("\n".join(current))
        
        return [s for s in sections if s.strip()]
    
    def _split_section(
        self,
        section: str,
        file_content: FileContent,
        section_index: int
    ) -> List[CodeChunk]:
        """Split a large section with overlap."""
        chunks = []
        
        start = 0
        chunk_num = 0
        
        while start < len(section):
            end = start + self.chunk_size
            
            # Try to end at a sentence or line boundary
            if end < len(section):
                # Look for newline near the end
                newline_pos = section.rfind("\n", start + self.chunk_size - 200, end)
                if newline_pos > start:
                    end = newline_pos + 1
            
            chunk_content = section[start:end].strip()
            
            if chunk_content:
                chunk = CodeChunk(
                    content=chunk_content,
                    chunk_id=self._generate_chunk_id(
                        file_content.path,
                        "section",
                        f"{section_index}_{chunk_num}",
                        0
                    ),
                    file_path=file_content.path,
                    start_line=1,
                    end_line=chunk_content.count("\n") + 1,
                    chunk_type="section",
                    language=file_content.language,
                    metadata={
                        "section_index": section_index,
                        "chunk_num": chunk_num
                    }
                )
                chunks.append(chunk)
            
            # Move start with overlap
            start = end - self.chunk_overlap
            chunk_num += 1
        
        return chunks
