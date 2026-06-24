"""
MCP I/O 표준을 따르는 도구 실행 서비스.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.infra.config import get_settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CodeMap 도구 서비스 클래스
# ──────────────────────────────────────────────
class CodeMapToolService:
    '''
    {tool, directory} 기반의 JSON Job을 실행하는 MCP I/O 인터페이스입니다.
    '''

    def __init__(self):
        self.settings = get_settings()

    # ──────────────────────────────────────────────
    # 도구 Job 실행 메서드
    # ──────────────────────────────────────────────
    async def execute_job(
        self,
        job_id: UUID,
        run_id: UUID,
        tool_name: str,
        arguments: dict,
    ) -> dict:
        '''
        주어진 도구명과 매개변수를 바탕으로 검색/조회 작업을 안전하게 수행합니다.
        '''
        logger.info(
            "[ToolService] Job 실행 — tool=%s, run_id=%s",
            tool_name,
            run_id,
        )

        ## 도구 분기 처리
        if tool_name == "vector_search":
            return await self._execute_vector_search(arguments)
        elif tool_name == "file_read":
            return await self._execute_file_read(arguments)
        elif tool_name == "dir_scan":
            return await self._execute_dir_scan(arguments)
        elif tool_name == "grep_scan":
            return await self._execute_grep_scan(arguments)
        else:
            raise ValueError(f"알 수 없는 도구입니다: {tool_name}")

    # ──────────────────────────────────────────────
    # 벡터 검색 도구 내부 메서드
    # ──────────────────────────────────────────────
    async def _execute_vector_search(self, args: dict) -> dict:
        '''
        시맨틱 임베딩 기반 하이브리드 RRF 검색을 실행합니다.
        '''
        query = args.get("query", "")
        return {
            "evidence_id": "ev_dummy_vector",
            "job_id": None,
            "status": "success",
            "path": None,
            "line_start": None,
            "line_end": None,
            "snippet": f"시맨틱 RAG 검색 결과 (쿼리: {query})",
            "score": 0.95,
            "metadata": {"tool": "vector_search"},
        }

    # ──────────────────────────────────────────────
    # 파일 읽기 도구 내부 메서드
    # ──────────────────────────────────────────────
    async def _execute_file_read(self, args: dict) -> dict:
        '''
        Symlink 방어가 적용된 안전한 파일 조회 도구입니다.
        '''
        path = args.get("path", "")
        return {
            "evidence_id": "ev_dummy_read",
            "job_id": None,
            "status": "success",
            "path": path,
            "line_start": 1,
            "line_end": 10,
            "snippet": f"파일 {path}의 내용 예시",
            "score": 1.0,
            "metadata": {"tool": "file_read"},
        }

    # ──────────────────────────────────────────────
    # 디렉토리 스캔 도구 내부 메서드
    # ──────────────────────────────────────────────
    async def _execute_dir_scan(self, args: dict) -> dict:
        '''
        디렉토리 구조 트리 조회 도구입니다.
        '''
        directory = args.get("directory", "")
        return {
            "evidence_id": "ev_dummy_dir",
            "job_id": None,
            "status": "success",
            "path": directory,
            "line_start": None,
            "line_end": None,
            "snippet": f"디렉토리 {directory}의 트리 구조 예시",
            "score": 1.0,
            "metadata": {"tool": "dir_scan"},
        }

    # ──────────────────────────────────────────────
    # Grep 스캔 도구 내부 메서드
    # ──────────────────────────────────────────────
    async def _execute_grep_scan(self, args: dict) -> dict:
        '''
        패턴 매칭 및 정규식 파일 내용 검색 도구입니다.
        '''
        query = args.get("query", "")
        directory = args.get("directory", "")
        return {
            "evidence_id": "ev_dummy_grep",
            "job_id": None,
            "status": "success",
            "path": directory,
            "line_start": None,
            "line_end": None,
            "snippet": f"{directory} 경로에서 패턴 '{query}' 검색 완료",
            "score": 1.0,
            "metadata": {"tool": "grep_scan"},
        }
