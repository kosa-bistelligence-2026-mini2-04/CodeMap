import re
from typing import Dict, List, Any
from rank_bm25 import BM25Okapi

from ..chunking import CodeChunk
from ..utils import logger


class BM25Retriever:
    
    def __init__(self):
        self.bm25 = None
        self.chunks: List[CodeChunk] = []
        self.tokenized_corpus: List[List[str]] = []
    
    def index(self, chunks: List[CodeChunk]) -> None:
        if not chunks:
            logger.warning("No chunks to index for BM25")
            return
        
        self.chunks = chunks
        
        self.tokenized_corpus = [
            self._tokenize(chunk.content) for chunk in chunks
        ]
        
        # Filter out empty tokenized documents
        valid_indices = []
        valid_corpus = []
        for i, tokens in enumerate(self.tokenized_corpus):
            if tokens:  # Only include non-empty
                valid_indices.append(i)
                valid_corpus.append(tokens)
        
        if not valid_corpus:
            logger.warning("No valid tokens found for BM25 indexing")
            self.bm25 = None
            return
        
        # Keep only chunks with valid tokens
        self.chunks = [self.chunks[i] for i in valid_indices]
        self.tokenized_corpus = valid_corpus
        
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        
        logger.info(f"BM25 indexed {len(self.chunks)} chunks")
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if self.bm25 is None or not self.chunks:
            return []
        
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            return []
        
        scores = self.bm25.get_scores(query_tokens)
        
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                chunk = self.chunks[idx]
                results.append({
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "metadata": {
                        "file_path": chunk.file_path,
                        "chunk_type": chunk.chunk_type,
                        "name": chunk.name,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "language": chunk.language,
                    },
                    "score": float(scores[idx]),
                })
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        
        text = text.lower()
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = text.replace("_", " ")
        tokens = re.findall(r'[a-z0-9]+', text)
        tokens = [t for t in tokens if len(t) > 1]
        
        return tokens
