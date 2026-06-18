import unittest

try:
    from app.embed import models as embed_models
except ImportError:
    embed_models = None


MODELS_READY = (
    embed_models is not None
    and hasattr(embed_models, "CodeNode")
    and hasattr(embed_models, "Dependency")
)


@unittest.skipUnless(MODELS_READY, "code_nodes/dependencies 모델이 아직 구현되지 않음")
class EmbedModelContractTests(unittest.TestCase):
    def test_code_node_has_documented_storage_columns(self):
        columns = embed_models.CodeNode.__table__.columns
        for name in (
            "id",
            "job_id",
            "path",
            "type",
            "depth",
            "content",
            "summary",
            "embedding",
            "file_metadata",
        ):
            self.assertIn(name, columns)
        self.assertNotIn("metadata", columns)

    def test_embedding_column_uses_1536_dimensions(self):
        embedding_type = embed_models.CodeNode.__table__.columns["embedding"].type
        dimension = getattr(embedding_type, "dim", getattr(embedding_type, "dimensions", None))
        self.assertEqual(dimension, 1536)

    def test_dependency_uses_source_and_target_as_composite_key(self):
        primary_keys = {column.name for column in embed_models.Dependency.__table__.primary_key.columns}
        self.assertEqual(primary_keys, {"source_id", "target_id"})
