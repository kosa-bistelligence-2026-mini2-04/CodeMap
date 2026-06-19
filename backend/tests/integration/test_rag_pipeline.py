import unittest
from unittest.mock import AsyncMock, patch

from tests.fixtures.mock_parse_result import build_mock_parse_result

try:
    from app.embed import repository as embed_repository
    from app.embed import service as embed_service
    from app.parse import schemas as rag_schemas
except ImportError:
    embed_repository = None
    embed_service = None
    rag_schemas = None


RAG_PIPELINE_READY = (
    rag_schemas is not None
    and embed_service is not None
    and embed_repository is not None
    and hasattr(embed_service, "generate_embeddings")
    and hasattr(embed_service, "run_embed_pipeline")
    and hasattr(embed_repository, "EmbedRepository")
)


@unittest.skipUnless(RAG_PIPELINE_READY, "PARSE → EMBED 통합 구현이 아직 완료되지 않음")
class RagPipelineIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_parse_result_can_flow_into_embedding_and_storage(self):
        parsed = build_mock_parse_result()
        request = rag_schemas.EmbedRequest(job_id=parsed.job_id, files=parsed.files)
        expected = rag_schemas.EmbedResult(
            job_id=parsed.job_id,
            total_files=1,
            total_chunks=1,
            failed_paths=[],
        )
        repository_instance = AsyncMock()
        repository_instance.save_to_pgvector.return_value = expected
        with (
            patch.object(embed_service, "generate_embeddings", AsyncMock(return_value=parsed.files)),
            patch.object(embed_service, "EmbedRepository", return_value=repository_instance),
        ):
            result = await embed_service.run_embed_pipeline(db=AsyncMock(), request=request)
        self.assertEqual(result, expected)
        repository_instance.save_to_pgvector.assert_awaited_once_with(parsed.job_id, parsed.files)
