"""
G1-A 파일 원문 + 심볼 조회 API 단위 테스트

검증 대상:
  - 권한 제어: private job 소유자 → 200, 비소유자/익명 → 404
  - 미존재 path → 404
  - 심볼 매핑: chunk_type→kind, symbol None인 청크 skip, start_line/end_line 없는 청크 skip
  - lineCount 계산

fake DB 세션 패턴은 tests/unit/test_team_access.py 참고.
"""

import types
import unittest
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.parse.schemas import FileContentResponse


# ──────────────────────────────────────────────
# Fake 인프라 헬퍼
# ──────────────────────────────────────────────
def _job(user_id=None, team_id=None, is_private=True):
    return types.SimpleNamespace(user_id=user_id, team_id=team_id, is_private=is_private)


def _node(type_="FILE", content=None, language=None, file_metadata=None, chunk_index=0):
    return types.SimpleNamespace(
        type=type_,
        content=content,
        language=language,
        file_metadata=file_metadata or {},
        chunk_index=chunk_index,
    )


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._value if isinstance(self._value, list) else []


class FakeSession:
    """execute() 호출 순서에 따라 미리 지정한 결과를 순차 반환하는 가짜 세션."""

    def __init__(self, results: list[Any]):
        self._results = list(results)
        self._call_index = 0

    async def execute(self, *_args, **_kwargs):
        result = self._results[self._call_index]
        self._call_index += 1
        return result


# ──────────────────────────────────────────────
# 테스트: 접근 제어
# ──────────────────────────────────────────────
class TestFileContentAccessControl(unittest.IsolatedAsyncioTestCase):

    async def _call_endpoint(
        self,
        job,
        current_user_dict,
        file_node,
        chunk_nodes,
        *,
        can_access,
    ):
        """엔드포인트 핵심 로직을 직접 호출하는 헬퍼 (라우터 의존성 우회)."""
        from app.parse.router import get_file_content

        repo_id = uuid4()
        path = "src/main.py"

        db = FakeSession([
            FakeScalarResult(file_node),
            FakeScalarResult(chunk_nodes),
        ])

        with patch("app.parse.router.AnalysisJobRepository") as MockRepo:
            MockRepo.return_value.get_job_by_id = AsyncMock(return_value=job)
            with patch(
                "app.parse.router.can_access_job",
                new=AsyncMock(return_value=can_access),
            ):
                return await get_file_content(
                    repo_id=repo_id,
                    path=path,
                    current_user=current_user_dict,
                    db=db,
                )

    async def test_owner_gets_200(self):
        owner = uuid4()
        job = _job(user_id=owner)
        file_node = _node(content="def foo():\n    pass\n", language="python")
        result = await self._call_endpoint(
            job=job,
            current_user_dict={"sub": str(owner)},
            file_node=file_node,
            chunk_nodes=[],
            can_access=True,
        )
        self.assertIsInstance(result, FileContentResponse)
        self.assertEqual(result.lineCount, 3)

    async def test_non_owner_gets_404(self):
        from app.common.exceptions import JobNotFoundError
        owner = uuid4()
        job = _job(user_id=owner)
        with self.assertRaises(JobNotFoundError):
            await self._call_endpoint(
                job=job,
                current_user_dict={"sub": str(uuid4())},  ## 다른 사람
                file_node=_node(content="x = 1\n", language="python"),
                chunk_nodes=[],
                can_access=False,
            )

    async def test_anonymous_gets_404(self):
        from app.common.exceptions import JobNotFoundError
        owner = uuid4()
        job = _job(user_id=owner)
        with self.assertRaises(JobNotFoundError):
            await self._call_endpoint(
                job=job,
                current_user_dict=None,
                file_node=_node(content="x = 1\n", language="python"),
                chunk_nodes=[],
                can_access=False,
            )

    async def test_missing_job_gets_404(self):
        from app.common.exceptions import JobNotFoundError
        with self.assertRaises(JobNotFoundError):
            await self._call_endpoint(
                job=None,
                current_user_dict={"sub": str(uuid4())},
                file_node=None,
                chunk_nodes=[],
                can_access=False,
            )


# ──────────────────────────────────────────────
# 테스트: 미존재 path
# ──────────────────────────────────────────────
class TestFileContentMissingPath(unittest.IsolatedAsyncioTestCase):

    async def test_missing_path_returns_404(self):
        from app.common.exceptions import JobNotFoundError
        from app.parse.router import get_file_content

        owner = uuid4()
        job = _job(user_id=owner)
        repo_id = uuid4()

        db = FakeSession([FakeScalarResult(None)])  ## FILE 노드 없음

        with patch("app.parse.router.AnalysisJobRepository") as MockRepo:
            MockRepo.return_value.get_job_by_id = AsyncMock(return_value=job)
            with patch("app.parse.router.can_access_job", new=AsyncMock(return_value=True)):
                with self.assertRaises(JobNotFoundError):
                    await get_file_content(
                        repo_id=repo_id,
                        path="nonexistent/file.py",
                        current_user={"sub": str(owner)},
                        db=db,
                    )


# ──────────────────────────────────────────────
# 테스트: 심볼 매핑
# ──────────────────────────────────────────────
class TestFileContentSymbolMapping(unittest.IsolatedAsyncioTestCase):

    async def _run(self, chunk_nodes_raw):
        from app.parse.router import get_file_content

        owner = uuid4()
        job = _job(user_id=owner)
        repo_id = uuid4()
        file_content = "def foo():\n    pass\n\nclass Bar:\n    pass\n"
        file_node = _node(content=file_content, language="python")

        db = FakeSession([
            FakeScalarResult(file_node),
            FakeScalarResult(chunk_nodes_raw),
        ])

        with patch("app.parse.router.AnalysisJobRepository") as MockRepo:
            MockRepo.return_value.get_job_by_id = AsyncMock(return_value=job)
            with patch("app.parse.router.can_access_job", new=AsyncMock(return_value=True)):
                return await get_file_content(
                    repo_id=repo_id,
                    path="src/main.py",
                    current_user={"sub": str(owner)},
                    db=db,
                )

    async def test_chunk_type_maps_to_kind(self):
        chunks = [
            _node(type_="CHUNK", file_metadata={
                "symbol": "foo", "chunk_type": "function",
                "start_line": 1, "end_line": 2,
            }),
            _node(type_="CHUNK", file_metadata={
                "symbol": "Bar", "chunk_type": "class",
                "start_line": 4, "end_line": 5,
            }),
        ]
        result = await self._run(chunks)
        self.assertEqual(len(result.symbols), 2)
        self.assertEqual(result.symbols[0].kind, "function")
        self.assertEqual(result.symbols[0].name, "foo")
        self.assertEqual(result.symbols[1].kind, "class")
        self.assertEqual(result.symbols[1].name, "Bar")

    async def test_symbol_none_chunk_is_skipped(self):
        chunks = [
            _node(type_="CHUNK", file_metadata={
                "symbol": None, "chunk_type": "module",
                "start_line": 1, "end_line": 5,
            }),
            _node(type_="CHUNK", file_metadata={
                "symbol": "foo", "chunk_type": "function",
                "start_line": 1, "end_line": 2,
            }),
        ]
        result = await self._run(chunks)
        self.assertEqual(len(result.symbols), 1)
        self.assertEqual(result.symbols[0].name, "foo")

    async def test_missing_line_info_chunk_is_skipped(self):
        chunks = [
            _node(type_="CHUNK", file_metadata={
                "symbol": "foo", "chunk_type": "function",
                ## start_line/end_line 없음
            }),
        ]
        result = await self._run(chunks)
        self.assertEqual(len(result.symbols), 0)

    async def test_no_chunks_returns_empty_symbols(self):
        result = await self._run([])
        self.assertEqual(result.symbols, [])

    async def test_line_count_calculation(self):
        ## "a\nb\nc\n" → 4라인 (count("\n")+1)
        chunks = []
        owner = uuid4()
        job = _job(user_id=owner)
        repo_id = uuid4()
        content = "a\nb\nc\n"
        file_node = _node(content=content, language="python")

        db = FakeSession([
            FakeScalarResult(file_node),
            FakeScalarResult([]),
        ])

        from app.parse.router import get_file_content
        with patch("app.parse.router.AnalysisJobRepository") as MockRepo:
            MockRepo.return_value.get_job_by_id = AsyncMock(return_value=job)
            with patch("app.parse.router.can_access_job", new=AsyncMock(return_value=True)):
                result = await get_file_content(
                    repo_id=repo_id,
                    path="src/main.py",
                    current_user={"sub": str(owner)},
                    db=db,
                )
        self.assertEqual(result.lineCount, 4)


if __name__ == "__main__":
    unittest.main()
