from typing import List, Dict, Any, Optional
import re
from ..utils import logger


class QueryExpander:
    """Expand queries with synonyms and code-aware terms."""
    
    # Code-specific synonyms
    SYNONYMS = {
        "function": ["method", "def", "func", "procedure"],
        "class": ["object", "type", "model"],
        "variable": ["var", "param", "parameter", "argument", "arg"],
        "return": ["returns", "output", "result"],
        "error": ["exception", "bug", "issue", "problem"],
        "create": ["make", "build", "generate", "construct", "init", "initialize"],
        "delete": ["remove", "destroy", "drop"],
        "get": ["fetch", "retrieve", "obtain", "read", "load"],
        "set": ["update", "modify", "change", "write", "save"],
        "list": ["array", "collection", "items"],
        "dict": ["dictionary", "map", "mapping", "hash"],
        "config": ["configuration", "settings", "options"],
        "auth": ["authentication", "login", "authorize"],
        "db": ["database", "storage", "data"],
        "api": ["endpoint", "route", "interface"],
        "test": ["testing", "unittest", "spec"],
        "async": ["asynchronous", "await", "concurrent"],
    }
    
    def __init__(self):
        # Build reverse mapping
        self.reverse_synonyms: Dict[str, str] = {}
        for key, values in self.SYNONYMS.items():
            for v in values:
                self.reverse_synonyms[v] = key
    
    def expand(self, query: str) -> List[str]:
        """Expand query with synonyms.
        
        Args:
            query: Original query
            
        Returns:
            List of expanded queries
        """
        queries = [query]
        query_lower = query.lower()
        words = re.findall(r'\b\w+\b', query_lower)
        
        for word in words:
            # Check if word has synonyms
            if word in self.SYNONYMS:
                for synonym in self.SYNONYMS[word][:2]:
                    expanded = query_lower.replace(word, synonym)
                    if expanded not in queries:
                        queries.append(expanded)
            
            # Check reverse synonyms
            elif word in self.reverse_synonyms:
                main_term = self.reverse_synonyms[word]
                expanded = query_lower.replace(word, main_term)
                if expanded not in queries:
                    queries.append(expanded)
        
        return queries[:4]
    
    def extract_code_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract potential code entities from query.
        
        Returns dict with:
        - function_names: potential function names
        - class_names: potential class names
        - file_patterns: potential file patterns
        """
        entities = {
            "function_names": [],
            "class_names": [],
            "file_patterns": [],
        }
        
        # Find camelCase or snake_case patterns
        camel_case = re.findall(r'\b[a-z]+(?:[A-Z][a-z]+)+\b', query)
        snake_case = re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', query)
        
        entities["function_names"].extend(camel_case)
        entities["function_names"].extend(snake_case)
        
        # Find PascalCase (likely class names)
        pascal_case = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', query)
        entities["class_names"].extend(pascal_case)
        
        # Find file patterns
        file_patterns = re.findall(r'\b\w+\.py\b', query)
        entities["file_patterns"].extend(file_patterns)
        
        return entities


class MultiQueryRetriever:
    """Retrieve using multiple query variations."""
    
    def __init__(self, base_retriever):
        self.base_retriever = base_retriever
        self.query_expander = QueryExpander()
    
    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search using multiple query expansions."""
        
        # Expand query
        queries = self.query_expander.expand(query)
        
        # Collect results from all queries
        all_results: Dict[str, Dict] = {}
        
        for i, q in enumerate(queries):
            weight = 1.0 if i == 0 else 0.5
            results = self.base_retriever.search(q, top_k=top_k)
            
            for r in results:
                chunk_id = r["chunk_id"]
                if chunk_id in all_results:
                    all_results[chunk_id]["score"] += r["score"] * weight
                    all_results[chunk_id]["matched_queries"].append(q)
                else:
                    all_results[chunk_id] = {
                        **r,
                        "score": r["score"] * weight,
                        "matched_queries": [q],
                    }
        
        # Sort by combined score
        results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)
        
        return results[:top_k]
