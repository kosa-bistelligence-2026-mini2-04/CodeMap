"""
Pure reference-building helpers — 외부 의존성 없음, 단위 테스트 직접 가능.

router.py, service.py가 공통으로 사용하며, 테스트는 이 모듈을 직접 임포트한다.
"""

from __future__ import annotations


# ──────────────────────────────────────────────
# build_reference
# ──────────────────────────────────────────────

def build_reference(
    path: str,
    line_start: int | None,
    snippet: str,
    *,
    max_snippet: int = 240,
) -> dict:
    """단일 reference dict 생성. line 없으면 lineLabel 추가."""
    ref: dict = {
        "file": str(path),
        "line": line_start,
        "snippet": str(snippet)[:max_snippet],
    }
    if line_start is None:
        ref["lineLabel"] = "라인 미확인"
    return ref


# ──────────────────────────────────────────────
# references_from_worker_results
# ──────────────────────────────────────────────

def references_from_worker_results(worker_results: list[dict]) -> list[dict]:
    """
    worker_results 목록을 reference 목록으로 변환한다.

    - path 없는 항목 건너뜀
    - (file, lineStart) 기준 중복 제거
    - lineStart None → line: null + lineLabel: "라인 미확인"
    """
    references: list[dict] = []
    seen: set[tuple[str, int | None]] = set()
    for result in worker_results:
        file_path = result.get("path")
        if not file_path:
            continue
        line_start: int | None = result.get("lineStart")
        key = (str(file_path), line_start)
        if key in seen:
            continue
        seen.add(key)
        references.append(
            build_reference(str(file_path), line_start, result.get("snippet", ""), max_snippet=240)
        )
    return references
