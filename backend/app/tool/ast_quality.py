"""AST and dependency quality analysis tool."""

from __future__ import annotations

import ast
import re
from pathlib import Path


def _get_python_complexity(text: str) -> int:
    '''
    Python 소스코드의 AST를 파싱하여 최대 순환 복잡도를 연산합니다.
    '''
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 1

    max_func_complexity = 1
    has_functions = False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_functions = True
            func_complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (
                    ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler
                )):
                    func_complexity += 1
                elif isinstance(child, ast.BoolOp):
                    func_complexity += len(child.values) - 1
            if func_complexity > max_func_complexity:
                max_func_complexity = func_complexity

    return max_func_complexity if has_functions else 1


def _estimate_non_python_complexity(text: str) -> int:
    '''
    정규식 키워드를 활용해 Python 외 언어 파일의 순환 복잡도를 추정합니다.
    '''
    pattern = r"\b(?:if|for|while|catch|switch)\b"
    matches = re.findall(pattern, text)
    ## 단순 제어 흐름 분기 개수를 기반으로 복잡도 추산
    estimated = 1 + (len(matches) // 3)
    return min(25, estimated)


# ──────────────────────────────────────────────
# calculate_code_complexity
# ──────────────────────────────────────────────
def calculate_code_complexity(file_paths: list[Path]) -> dict:
    '''
    파일 리스트의 AST/키워드 분석을 통해 평균/최대 복잡도 및 대형 파일 통계를 냅니다.
    '''
    total_complexity = 0
    max_complexity = 1
    measured_count = 0
    oversized_files: list[str] = []

    for path in file_paths:
        try:
            raw_bytes = path.read_bytes()[:160_000]
            if b"\x00" in raw_bytes:
                continue
            text = raw_bytes.decode("utf-8", errors="replace")
        except OSError:
            continue

        ## 대형 파일 검증
        line_count = text.count("\n") + (1 if text else 0)
        if line_count > 700:
            oversized_files.append(path.name)

        if path.suffix.lower() == ".py":
            complexity = _get_python_complexity(text)
        else:
            complexity = _estimate_non_python_complexity(text)

        total_complexity += complexity
        measured_count += 1
        if complexity > max_complexity:
            max_complexity = complexity

    avg_complexity = (
        total_complexity / max(measured_count, 1)
    )
    total_files = len(file_paths)
    oversized_ratio = (
        len(oversized_files) / max(total_files, 1)
    )

    return {
        "average_complexity": round(avg_complexity, 2),
        "max_complexity": max_complexity,
        "oversized_files": sorted(oversized_files),
        "oversized_ratio": round(oversized_ratio, 4),
    }


# ──────────────────────────────────────────────
# calculate_module_coupling
# ──────────────────────────────────────────────
def calculate_module_coupling(dependencies: dict[str, list[str]]) -> dict:
    '''
    파일 간 의존성 관계 정보를 스캔하여 결합 강도 계수 및 순환 의존 여부를 추출합니다.
    '''
    total_nodes = len(dependencies)
    if total_nodes <= 1:
        return {
            "coupling_coefficient": 0.0,
            "has_circular_dependency": False
        }

    total_edges = sum(len(targets) for targets in dependencies.values())
    max_possible_edges = total_nodes * (total_nodes - 1)

    ## 결합도 계수 (0 ~ 1 사이 실수)
    coupling_coefficient = total_edges / max_possible_edges

    ## DFS 순환 의존성(Cycle) 탐색
    visited = {}  # 0: unvisited, 1: visiting, 2: visited
    for node in dependencies:
        visited[node] = 0

    has_cycle = False

    def dfs(u):
        nonlocal has_cycle
        if has_cycle:
            return
        visited[u] = 1  # visiting
        for v in dependencies.get(u, []):
            if v not in visited:
                continue
            if visited[v] == 1:
                has_cycle = True
                return
            elif visited[v] == 0:
                dfs(v)
        visited[u] = 2  # visited

    for node in dependencies:
        if visited[node] == 0:
            dfs(node)
            if has_cycle:
                break

    return {
        "coupling_coefficient": round(coupling_coefficient, 4),
        "has_circular_dependency": has_cycle,
    }
