"""Basic tests for CodeBase RAG components."""

import pytest
from pathlib import Path


class TestIngestion:
    """Test GitHub loading and file parsing."""
    
    def test_parse_repo_name(self):
        """Test repository name parsing from URL."""
        from src.ingestion import GitHubLoader
        
        loader = GitHubLoader()
        
        # HTTPS URL
        assert loader._parse_repo_name("https://github.com/owner/repo") == "owner_repo"
        assert loader._parse_repo_name("https://github.com/owner/repo.git") == "owner_repo"
        
        # SSH URL
        assert loader._parse_repo_name("git@github.com:owner/repo.git") == "owner_repo"
    
    def test_file_extension_mapping(self):
        """Test language detection from file extension."""
        from src.ingestion import GitHubLoader
        
        loader = GitHubLoader()
        
        assert loader.LANGUAGE_MAP[".py"] == "python"
        assert loader.LANGUAGE_MAP[".js"] == "javascript"
        assert loader.LANGUAGE_MAP[".md"] == "markdown"


class TestChunking:
    """Test chunking strategies."""
    
    def test_chunk_id_generation(self):
        """Test unique chunk ID generation."""
        from src.chunking import ASTChunker
        
        chunker = ASTChunker()
        
        chunk_id = chunker._generate_chunk_id(
            file_path="src/main.py",
            chunk_type="function",
            name="test_func",
            start_line=10
        )
        
        assert "src_main_py" in chunk_id
        assert "function" in chunk_id
        assert "test_func" in chunk_id
        assert "10" in chunk_id
    
    def test_simple_chunking(self):
        """Test basic code chunking."""
        from src.chunking import ASTChunker
        from src.ingestion import FileContent
        
        chunker = ASTChunker()
        
        # Simple Python code
        code = """
def hello():
    '''Say hello'''
    print("Hello, World!")

def goodbye():
    '''Say goodbye'''
    print("Goodbye!")
"""
        
        file_content = FileContent(
            path="test.py",
            content=code,
            extension=".py",
            language="python",
            size=len(code),
            metadata={"repo_name": "test"}
        )
        
        chunks = chunker.chunk_file(file_content)
        
        # Should create at least 2 chunks (one for each function)
        assert len(chunks) >= 2
        assert any("hello" in chunk.content for chunk in chunks)
        assert any("goodbye" in chunk.content for chunk in chunks)


class TestEmbeddings:
    """Test embedding generation."""
    
    def test_embedder_initialization(self):
        """Test embedder can be initialized."""
        from src.embeddings import CodeEmbedder
        
        embedder = CodeEmbedder()
        
        assert embedder.model_name == "BAAI/bge-base-en-v1.5"
        assert embedder._model is None  # Lazy loading
    
    def test_embedding_shape(self):
        """Test embedding output shape."""
        from src.embeddings import CodeEmbedder
        
        embedder = CodeEmbedder()
        
        text = "def hello(): print('world')"
        embedding = embedder.embed(text)
        
        # BGE-base produces 768-dim embeddings
        assert embedding.shape == (1, 768)


class TestRetrieval:
    """Test retrieval components."""
    
    def test_bm25_tokenization(self):
        """Test BM25 tokenizer handles code properly."""
        from src.retrieval import BM25Retriever
        
        retriever = BM25Retriever()
        
        # Test camelCase splitting
        tokens = retriever._tokenize("getUserName")
        assert "get" in tokens
        assert "user" in tokens
        assert "name" in tokens
        
        # Test snake_case splitting
        tokens = retriever._tokenize("get_user_name")
        assert "get" in tokens
        assert "user" in tokens
        assert "name" in tokens


class TestGeneration:
    """Test LLM generation."""
    
    def test_prompt_building(self):
        """Test prompt construction."""
        from src.generation.prompts import build_prompt
        
        query = "How does authentication work?"
        results = [
            {
                "content": "def login():\n    return auth_token",
                "metadata": {
                    "file_path": "auth.py",
                    "chunk_type": "function",
                    "name": "login",
                    "start_line": 10,
                    "end_line": 12,
                    "language": "python"
                }
            }
        ]
        
        prompt = build_prompt(query, results)
        
        assert "How does authentication work?" in prompt
        assert "auth.py" in prompt
        assert "login" in prompt


class TestVectorStore:
    """Test vector store operations."""
    
    def test_vector_store_initialization(self):
        """Test vector store can be initialized."""
        from src.retrieval import VectorStore
        
        store = VectorStore(persist_directory="./data/vectors/test")
        
        assert store.collection_name == "codebase"
        assert store._client is None  # Lazy loading


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])