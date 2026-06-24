"""RAG 인덱싱(_run_parse_and_embed)의 rag_index.status 판정 회귀 테스트.

핵심 계약: status는 upsert된 row 수(saved_chunks)가 아니라 실제 non-null 임베딩
존재 여부(embed_ready)로 정해져야 한다. 임베딩 배치가 실패해 row만 저장된
경우(saved_chunks>0, 벡터 0)에도 status가 'ready'가 되면 안 된다.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.repo.schemas import JobStatus
from app.repo.service import AnalysisService


class _AsyncCtx:
    """async with용 더미 세션 컨텍스트."""

    def __init__(self):
        self.session = AsyncMock()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc):
        return False


def _fake_parse_result(job_id):
    from app.parse.schemas import ParseResult

    return ParseResult(
        job_id=job_id, repo_name="sample", owner="example", branch="main", files=[]
    )


class RagIndexStatusTests(unittest.IsolatedAsyncioTestCase):
    async def _run(self, *, has_vectors: bool, saved_chunks: int) -> dict:
        from app.parse.schemas import EmbedResult

        job_id = uuid4()
        fake_job = SimpleNamespace(
            status=JobStatus.COMPLETED.value,
            owner="example",
            repo_name="sample",
            branch="main",
            force_refresh=False,
            report_json={},
        )
        repo_instance = MagicMock()
        repo_instance.get_job_by_id = AsyncMock(return_value=fake_job)
        repo_instance.update_job_status = AsyncMock()

        fake_settings = SimpleNamespace(
            CLONE_BASE_DIR="/tmp/codemap",
            OPENAI_API_KEY=SimpleNamespace(get_secret_value=lambda: "sk-test"),
        )

        with (
            patch("app.infra.database.async_session_factory", side_effect=lambda: _AsyncCtx()),
            patch("app.repo.service.AnalysisJobRepository", return_value=repo_instance),
            patch("app.repo.service.os.path.isdir", return_value=True),
            patch("app.repo.service.get_settings", return_value=fake_settings),
            patch(
                "app.parse.service.run_parse_pipeline",
                AsyncMock(return_value=_fake_parse_result(job_id)),
            ),
            patch(
                "app.embed.service.run_embed_pipeline",
                AsyncMock(return_value=EmbedResult(job_id=job_id, saved_chunks=saved_chunks)),
            ),
            patch("app.embed.service.embed_ready", AsyncMock(return_value=has_vectors)),
        ):
            service = AnalysisService(db=AsyncMock())
            await service._run_parse_and_embed(str(job_id))

        return repo_instance.update_job_status.await_args.kwargs["report_json"]["rag_index"]

    async def test_status_empty_when_rows_saved_but_no_embeddings(self):
        # row는 저장됐지만(saved_chunks=5) 실제 임베딩이 없으면(embed_ready=False) → status != ready
        rag_index = await self._run(has_vectors=False, saved_chunks=5)
        self.assertEqual(rag_index["chunks"], 5)
        self.assertEqual(rag_index["status"], "empty")

    async def test_status_ready_when_embeddings_present(self):
        rag_index = await self._run(has_vectors=True, saved_chunks=5)
        self.assertEqual(rag_index["status"], "ready")
