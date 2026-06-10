from typing import Dict, List, Any, Optional
from ..utils import logger


class CrossEncoderReranker:
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None
        logger.info(f"CrossEncoderReranker initialized with model: {model_name}")
    
    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self._model = CrossEncoder(self.model_name)
        return self._model
    
    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not results:
            return []
        
        pairs = []
        for result in results:
            content = result.get("content", "")
            if len(content) > 512:
                content = content[:512]
            pairs.append([query, content])
        
        scores = self.model.predict(pairs)
        
        for i, result in enumerate(results):
            result["cross_encoder_score"] = float(scores[i])
            result["original_score"] = result.get("score", 0)
        
        reranked = sorted(results, key=lambda x: x["cross_encoder_score"], reverse=True)
        
        if top_k:
            reranked = reranked[:top_k]
        
        for result in reranked:
            result["score"] = result["cross_encoder_score"]
        
        return reranked


class LightweightReranker:
    
    def __init__(self):
        pass
    
    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not results:
            return []
        
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        
        for result in results:
            boost = 0.0
            content_lower = result.get("content", "").lower()
            metadata = result.get("metadata", {})
            
            for term in query_terms:
                if len(term) > 2 and term in content_lower:
                    boost += 0.1
                    
            name = metadata.get("name", "")
            if name:
                name_lower = name.lower()
                if name_lower in query_lower:
                    boost += 0.3
                for term in query_terms:
                    if term in name_lower:
                        boost += 0.15
            
            chunk_type = metadata.get("chunk_type", "")
            if chunk_type == "function":
                boost += 0.1
            elif chunk_type == "class":
                boost += 0.05
            
            original_score = result.get("score", 0)
            if original_score is None:
                original_score = 0
            
            result["rerank_score"] = original_score + boost
            result["original_score"] = original_score
        
        reranked = sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        if top_k:
            reranked = reranked[:top_k]
        
        for result in reranked:
            result["score"] = result.get("rerank_score", 0)
        
        return reranked
