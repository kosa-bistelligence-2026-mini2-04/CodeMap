import inspect
import unittest
from pathlib import Path

from app import main


class CheckpointSchemaTests(unittest.TestCase):
    def test_lifespan_does_not_run_checkpoint_setup(self):
        source = inspect.getsource(main.lifespan)

        self.assertNotIn(".setup()", source)
        self.assertIn("validate_required_schema", source)

    def test_init_sql_contains_langgraph_checkpoint_schema(self):
        repo_root = Path(__file__).resolve().parents[3]
        init_sql = (repo_root / "database/init.sql").read_text(encoding="utf-8")

        for table in [
            "checkpoint_migrations",
            "checkpoints",
            "checkpoint_blobs",
            "checkpoint_writes",
        ]:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", init_sql)
        self.assertIn("task_path TEXT NOT NULL DEFAULT ''", init_sql)
        self.assertIn("checkpoint_migrations (v)", init_sql)


if __name__ == "__main__":
    unittest.main()
