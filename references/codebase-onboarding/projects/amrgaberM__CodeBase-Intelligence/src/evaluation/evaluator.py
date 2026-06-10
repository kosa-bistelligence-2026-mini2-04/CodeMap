"""Evaluation metrics for RAG system."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..utils import logger


@dataclass
class EvaluationResult:
    """Container for evaluation results."""
    
    query: str
    retrieved_chunks: List[Dict] = field(default_factory=list)
    generated_answer: str = ""
    
    # Metrics
    retrieval_precision: float = 0.0
    retrieval_recall: float = 0.0
    answer_relevance: float = 0.0
    faithfulness: float = 0.0
    
    # Ground truth (if available)
    expected_files: List[str] = field(default_factory=list)
    expected_answer: str = ""


class RAGEvaluator:
    """Evaluate RAG system performance."""
    
    def __init__(self, generator=None):
        """Initialize evaluator."""
        self.generator = generator
    
    def evaluate_retrieval(
        self,
        query: str,
        retrieved: List[Dict],
        relevant_files: List[str],
    ) -> Dict[str, float]:
        """Evaluate retrieval quality."""
        if not relevant_files:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        
        retrieved_files = set()
        for chunk in retrieved:
            file_path = chunk.get("metadata", {}).get("file_path", "")
            if file_path:
                retrieved_files.add(file_path)
        
        relevant_set = set(relevant_files)
        true_positives = len(retrieved_files & relevant_set)
        
        precision = true_positives / len(retrieved_files) if retrieved_files else 0.0
        recall = true_positives / len(relevant_set) if relevant_set else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {"precision": precision, "recall": recall, "f1": f1}
    
    def evaluate_answer_relevance(self, query: str, answer: str) -> float:
        """Evaluate if answer is relevant to query."""
        if not answer:
            return 0.0
        
        query_terms = set(query.lower().split())
        answer_lower = answer.lower()
        
        matches = sum(1 for term in query_terms if term in answer_lower)
        return matches / len(query_terms) if query_terms else 0.0
    
    def evaluate_faithfulness(self, answer: str, context: List[Dict]) -> float:
        """Check if answer is grounded in context."""
        if not answer or not context:
            return 0.0
        
        context_text = " ".join(c.get("content", "") for c in context).lower()
        answer_sentences = answer.split(".")
        
        grounded = 0
        for sentence in answer_sentences:
            sentence = sentence.strip().lower()
            if len(sentence) > 20:
                words = sentence.split()[:5]
                if any(word in context_text for word in words):
                    grounded += 1
        
        return grounded / len(answer_sentences) if answer_sentences else 0.0
    
    def full_evaluation(
        self,
        query: str,
        retrieved: List[Dict],
        answer: str,
        relevant_files: Optional[List[str]] = None,
    ) -> EvaluationResult:
        """Run full evaluation."""
        result = EvaluationResult(
            query=query,
            retrieved_chunks=retrieved,
            generated_answer=answer,
        )
        
        if relevant_files:
            retrieval_metrics = self.evaluate_retrieval(query, retrieved, relevant_files)
            result.retrieval_precision = retrieval_metrics["precision"]
            result.retrieval_recall = retrieval_metrics["recall"]
            result.expected_files = relevant_files
        
        result.answer_relevance = self.evaluate_answer_relevance(query, answer)
        result.faithfulness = self.evaluate_faithfulness(answer, retrieved)
        
        return result
