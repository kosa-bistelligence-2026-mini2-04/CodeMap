import inspect
import unittest
from uuid import uuid4

try:
    from app.embed import repository as embed_repository
    from app.embed import service as embed_service
except ImportError:
    embed_repository = None
    embed_service = None


EMBED_READY = (
    embed_service is not None
    and embed_repository is not None
    and hasattr(embed_service, "generate_embeddings")
    and hasattr(embed_service, "run_embed_pipeline")
    and hasattr(embed_repository, "EmbedRepository")
    and hasattr(embed_repository.EmbedRepository, "save_to_pgvector")
)


@unittest.skipUnless(EMBED_READY, "EMBED B-201/B-301이 아직 구현되지 않음")
class EmbedFunctionContractTests(unittest.TestCase):
    def test_generate_embeddings_accepts_files(self):
        parameters = inspect.signature(embed_service.generate_embeddings).parameters
        self.assertEqual(list(parameters), ["files"])

    def test_pipeline_accepts_db_and_shared_request(self):
        parameters = inspect.signature(embed_service.run_embed_pipeline).parameters
        self.assertEqual(list(parameters), ["db", "request"])

    def test_repository_upserts_by_job_and_files(self):
        parameters = inspect.signature(
            embed_repository.EmbedRepository.save_to_pgvector
        ).parameters
        self.assertEqual(list(parameters), ["self", "job_id", "files"])


@unittest.skipUnless(
    EMBED_READY
    and hasattr(embed_service, "vector_search")
    and hasattr(embed_service, "embed_ready"),
    "EMBED 벡터 검색(vector_search/embed_ready)이 아직 구현되지 않음",
)
class EmbedSearchContractTests(unittest.IsolatedAsyncioTestCase):
    """RAG 답변용 벡터 검색 계약 (팀 orchestrator search 도구 + chat 폴백 분기)."""

    def test_vector_search_signature(self):
        parameters = inspect.signature(embed_service.vector_search).parameters
        self.assertEqual(list(parameters), ["db", "repo_id", "query", "k"])

    def test_embed_ready_signature(self):
        parameters = inspect.signature(embed_service.embed_ready).parameters
        self.assertEqual(list(parameters), ["db", "repo_id"])

    def test_repository_exposes_vector_queries(self):
        self.assertTrue(hasattr(embed_repository.EmbedRepository, "has_embeddings"))
        self.assertTrue(hasattr(embed_repository.EmbedRepository, "similarity_search"))

    async def test_vector_search_returns_empty_for_blank_query(self):
        # 빈 질의는 DB/임베딩 호출 없이 빈 목록 (호출측 폴백). db는 사용되지 않는다.
        result = await embed_service.vector_search(db=None, repo_id=uuid4(), query="   ")
        self.assertEqual(result, [])
