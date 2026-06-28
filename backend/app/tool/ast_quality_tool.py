"""AST 기반 코드 복잡도 및 결합도 분석 도구."""

from __future__ import annotations

import ast
from pathlib import Path


def calculate_ast_quality(clone_path: str, rel_path: str | None = None) -> dict[str, int]:
    """지정된 경로의 코드 복잡도와 모듈화 점수를 계산한다."""
    target = (Path(clone_path) / (rel_path or "")).resolve()
    root = Path(clone_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return {"complexity": 50, "modularity": 50}

    total_complexity = 0
    total_functions = 0
    total_imports = 0
    file_count = 0

    candidates = [target] if target.is_file() else target.rglob("*.py")

    for file_path in candidates:
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
            file_count += 1
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    total_functions += 1
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                    total_complexity += 1
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    total_imports += 1
        except Exception:
            pass

    if file_count == 0:
        return {"complexity": 80, "modularity": 80}

    avg_complexity = total_complexity / max(total_functions, 1)
    
    # 복잡도 점수 (낮을수록 좋음, 100점 만점)
    complexity_score = max(0, 100 - int(avg_complexity * 10))
    
    # 모듈화 점수 (import 수에 기반, 단순화된 휴리스틱)
    avg_imports = total_imports / file_count
    modularity_score = max(0, 100 - int(avg_imports * 2))

    return {
        "complexity": min(100, complexity_score),
        "modularity": min(100, modularity_score),
    }

def analyze_ast_quality(clone_path: str, rel_path: str | None = None) -> str:
    """MCP Job 반환용 텍스트 포맷팅"""
    metrics = calculate_ast_quality(clone_path, rel_path)
    return f"Complexity Score: {metrics['complexity']}\nModularity Score: {metrics['modularity']}"
