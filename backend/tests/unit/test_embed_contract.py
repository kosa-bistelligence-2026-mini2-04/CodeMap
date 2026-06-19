import inspect
import unittest

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
