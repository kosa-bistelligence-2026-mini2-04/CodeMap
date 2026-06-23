"""RAG-PARSE B-209: 계층형 Bottom-up 요약.

파일 요약 → 폴더 요약 → 프로젝트 마스터 요약 순으로 상향식 집계한다 (Tree-Based RAG).
명세: docs/03_Specifications/02_RAG/spec/RAG_PARSE_SPEC.md (B-209)

설계: 파일/폴더 요약은 구조 휴리스틱(청크 심볼·docstring·첫 줄)으로 만들고,
프로젝트 마스터 요약만 LLM 1회(키 미설정/실패 시 휴리스틱 폴백)로 생성한다.
NOTE: 명세의 "파일별 LLM 요약"은 파일 수만큼 LLM을 호출해 비용/지연이 커서 후속으로 둔다.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from app.core.config import get_settings
from app.parse.schemas import ParsedFile

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_MASTER_INPUT_CHARS = 4000   # 마스터 LLM 입력 상한
_MAX_FILE_SUMMARY_CHARS = 160
_LLM_TIMEOUT_SECONDS = 30
_LLM_MAX_RETRIES = 2


def _file_summary(node: ParsedFile) -> str:
    """파일 1개의 휴리스틱 요약. 청크 심볼이 있으면 심볼 기반, 없으면 첫 의미 줄."""
    name = Path(node.path).name
    symbols = [c.symbol for c in (node.chunks or []) if c.symbol]
    if symbols:
        shown = ", ".join(symbols[:8])
        more = f" 외 {len(symbols) - 8}개" if len(symbols) > 8 else ""
        return f"{name}: {len(node.chunks)}개 청크 — {shown}{more}"
    first_line = next(
        (line.strip() for line in (node.content or "").splitlines() if line.strip()),
        "",
    )
    summary = f"{name}: {first_line}" if first_line else name
    return summary[:_MAX_FILE_SUMMARY_CHARS]


def _folder_of(path: str) -> str:
    """파일 경로의 상위 디렉토리(루트는 ".")."""
    parent = Path(path).parent.as_posix()
    return parent if parent not in ("", ".") else "."


async def _master_summary_with_llm(folder_text: str) -> str | None:
    """폴더 요약 묶음을 LLM으로 프로젝트 마스터 요약. 키 미설정/실패 시 None."""
    if not settings.OPENAI_API_KEY.get_secret_value():
        return None
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
            timeout=_LLM_TIMEOUT_SECONDS,
            max_retries=_LLM_MAX_RETRIES,
        )
        response = await llm.ainvoke([
            (
                "system",
                "당신은 코드베이스를 분석하는 시니어 엔지니어입니다. "
                "주어진 디렉토리별 요약만 근거로 이 프로젝트가 무엇이고 어떻게 구성됐는지 "
                "한국어 3~5문장으로 요약하세요. 근거에 없는 내용은 지어내지 마세요.",
            ),
            ("user", folder_text),
        ])
        summary = str(response.content).strip()
        return summary or None
    except Exception as exc:  # LLM 오류는 휴리스틱으로 폴백
        logger.warning("마스터 요약 LLM 실패, 휴리스틱으로 대체합니다: %s", exc)
        return None


async def build_hierarchical_summary(
    files: list[ParsedFile],
) -> tuple[list[ParsedFile], str]:
    """파일→폴더→마스터 상향식 요약 (RAG-PARSE-B-209).

    각 파일의 summary를 채운 새 ParsedFile 목록과 프로젝트 마스터 요약 문자열을 반환한다.
    입력을 in-place로 바꾸지 않고 model_copy로 새 객체를 만든다.
    """
    # 1. 파일별 요약 (content 있는 FILE만)
    summarized: list[ParsedFile] = []
    for node in files:
        if node.file_type == "FILE" and node.content:
            summarized.append(node.model_copy(update={"summary": _file_summary(node)}))
        else:
            summarized.append(node)

    # 2. 폴더별 요약 집계
    by_folder: dict[str, list[str]] = defaultdict(list)
    for node in summarized:
        if node.file_type == "FILE" and node.summary:
            by_folder[_folder_of(node.path)].append(node.summary)
    folder_summaries = {
        folder: f"[{folder}] {len(items)}개 파일 — " + " / ".join(items[:5])
        for folder, items in sorted(by_folder.items())
    }

    # 3. 프로젝트 마스터 요약 (LLM 1회 + 휴리스틱 폴백)
    folder_text = "\n".join(folder_summaries.values())[:_MAX_MASTER_INPUT_CHARS]
    master = await _master_summary_with_llm(folder_text)
    if not master:
        file_count = sum(1 for n in summarized if n.file_type == "FILE")
        master = (
            f"총 {len(folder_summaries)}개 디렉토리, {file_count}개 파일로 구성된 프로젝트. "
            + "주요 디렉토리: "
            + ", ".join(list(folder_summaries.keys())[:8])
        )

    return summarized, master
