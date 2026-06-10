"""Evaluation benchmark for CodeBase Intelligence RAG.

Tests the system on a known repository with predefined questions.
"""

import json
import time
from typing import Dict, List
from pathlib import Path

from src.ingestion import GitHubLoader
from src.chunking import ASTChunker
from src.retrieval import HybridRetriever, LightweightReranker
from src.generation import CodeGenerator
from src.utils import logger


class BenchmarkEvaluator:
    """Evaluate RAG system performance on benchmark questions."""
    
    def __init__(self):
        """Initialize evaluator."""
        self.loader = GitHubLoader()
        self.chunker = ASTChunker()
        self.retriever = HybridRetriever()
        self.generator = CodeGenerator()
        self.reranker = LightweightReranker()
        
        self.results = []
    
    def run_benchmark(
        self,
        repo_url: str,
        questions: List[Dict[str, str]],
        output_file: str = "benchmark_results.json"
    ) -> Dict:
        """Run benchmark on a repository.
        
        Args:
            repo_url: GitHub repository URL
            questions: List of {"question": str, "expected_files": List[str]}
            output_file: Path to save results
            
        Returns:
            Summary statistics
        """
        logger.info(f"🎯 Starting benchmark on {repo_url}")
        
        # Step 1: Ingest repository
        logger.info("📦 Ingesting repository...")
        start = time.time()
        files = self.loader.clone_repo(repo_url)
        chunks = self.chunker.chunk_files(files)
        self.retriever.index(chunks)
        ingestion_time = time.time() - start
        
        logger.info(f"✅ Indexed {len(chunks)} chunks in {ingestion_time:.2f}s")
        
        # Step 2: Run queries
        logger.info(f"🔍 Running {len(questions)} test queries...")
        
        for i, q_data in enumerate(questions, 1):
            question = q_data["question"]
            expected_files = q_data.get("expected_files", [])
            
            logger.info(f"[{i}/{len(questions)}] {question}")
            
            # Retrieve
            start = time.time()
            results = self.retriever.search(question, top_k=10)
            results = self.reranker.rerank(question, results, top_k=5)
            retrieval_time = time.time() - start
            
            # Generate
            start = time.time()
            answer = self.generator.generate(question, results)
            generation_time = time.time() - start
            
            # Extract retrieved files
            retrieved_files = list(set(
                r.get("metadata", {}).get("file_path", "")
                for r in results
            ))
            
            # Calculate metrics
            if expected_files:
                relevant = set(expected_files)
                retrieved = set(retrieved_files)
                
                precision = (
                    len(relevant & retrieved) / len(retrieved)
                    if retrieved else 0
                )
                recall = (
                    len(relevant & retrieved) / len(relevant)
                    if relevant else 0
                )
                f1 = (
                    2 * precision * recall / (precision + recall)
                    if (precision + recall) > 0 else 0
                )
            else:
                precision = recall = f1 = None
            
            # Store result
            self.results.append({
                "question": question,
                "answer": answer,
                "expected_files": expected_files,
                "retrieved_files": retrieved_files,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "retrieval_time_ms": retrieval_time * 1000,
                "generation_time_ms": generation_time * 1000,
            })
            
            logger.info(f"  ⏱️  {retrieval_time*1000:.0f}ms retrieval | {generation_time*1000:.0f}ms generation")
            if f1 is not None:
                logger.info(f"  📊 Precision: {precision:.2f} | Recall: {recall:.2f} | F1: {f1:.2f}")
        
        # Calculate summary
        valid_results = [r for r in self.results if r["f1"] is not None]
        
        summary = {
            "repo_url": repo_url,
            "total_questions": len(questions),
            "total_files": len(files),
            "total_chunks": len(chunks),
            "ingestion_time_s": ingestion_time,
            "avg_retrieval_time_ms": sum(r["retrieval_time_ms"] for r in self.results) / len(self.results),
            "avg_generation_time_ms": sum(r["generation_time_ms"] for r in self.results) / len(self.results),
            "avg_precision": sum(r["precision"] for r in valid_results) / len(valid_results) if valid_results else None,
            "avg_recall": sum(r["recall"] for r in valid_results) / len(valid_results) if valid_results else None,
            "avg_f1": sum(r["f1"] for r in valid_results) / len(valid_results) if valid_results else None,
        }
        
        # Save results
        output = {
            "summary": summary,
            "questions": self.results
        }
        
        Path(output_file).write_text(json.dumps(output, indent=2))
        logger.info(f"💾 Results saved to {output_file}")
        
        # Print summary
        self._print_summary(summary)
        
        return summary
    
    def _print_summary(self, summary: Dict):
        """Print benchmark summary."""
        logger.info("\n" + "="*60)
        logger.info("📊 BENCHMARK SUMMARY")
        logger.info("="*60)
        logger.info(f"Repository: {summary['repo_url']}")
        logger.info(f"Questions: {summary['total_questions']}")
        logger.info(f"Chunks Indexed: {summary['total_chunks']}")
        logger.info(f"Ingestion Time: {summary['ingestion_time_s']:.2f}s")
        logger.info(f"Avg Retrieval Time: {summary['avg_retrieval_time_ms']:.0f}ms")
        logger.info(f"Avg Generation Time: {summary['avg_generation_time_ms']:.0f}ms")
        
        if summary['avg_f1'] is not None:
            logger.info(f"Avg Precision: {summary['avg_precision']:.2%}")
            logger.info(f"Avg Recall: {summary['avg_recall']:.2%}")
            logger.info(f"Avg F1 Score: {summary['avg_f1']:.2%}")
        
        logger.info("="*60 + "\n")


# Example benchmark questions for different repos
TYPER_QUESTIONS = [
    {
        "question": "How do I create a CLI command?",
        "expected_files": ["typer/main.py", "typer/core.py"]
    },
    {
        "question": "How does argument parsing work?",
        "expected_files": ["typer/core.py", "typer/models.py"]
    },
    {
        "question": "What is the Typer class used for?",
        "expected_files": ["typer/main.py"]
    },
    {
        "question": "How do I add options to a command?",
        "expected_files": ["typer/main.py", "typer/core.py"]
    },
    {
        "question": "How does colored output work?",
        "expected_files": ["typer/colors.py"]
    },
]

FASTAPI_QUESTIONS = [
    {
        "question": "How do I create a route?",
        "expected_files": ["fastapi/routing.py", "fastapi/applications.py"]
    },
    {
        "question": "How does dependency injection work?",
        "expected_files": ["fastapi/dependencies/utils.py"]
    },
    {
        "question": "What is the FastAPI class?",
        "expected_files": ["fastapi/applications.py"]
    },
    {
        "question": "How do I handle request validation?",
        "expected_files": ["fastapi/routing.py"]
    },
    {
        "question": "How does the OpenAPI schema generation work?",
        "expected_files": ["fastapi/openapi/utils.py"]
    },
]


def run_quick_test():
    """Run a quick test on Typer repository."""
    evaluator = BenchmarkEvaluator()
    
    evaluator.run_benchmark(
        repo_url="https://github.com/tiangolo/typer",
        questions=TYPER_QUESTIONS[:3],  # Just 3 questions for quick test
        output_file="benchmark_typer_quick.json"
    )


def run_full_benchmark():
    """Run full benchmark on multiple repositories."""
    evaluator = BenchmarkEvaluator()
    
    # Test on Typer (smaller repo)
    logger.info("🎯 Benchmarking Typer...")
    evaluator.run_benchmark(
        repo_url="https://github.com/tiangolo/typer",
        questions=TYPER_QUESTIONS,
        output_file="benchmark_typer.json"
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        run_quick_test()
    else:
        run_full_benchmark()