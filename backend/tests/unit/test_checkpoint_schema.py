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

    def test_init_sql_contains_lru_last_accessed_at(self):
        repo_root = Path(__file__).resolve().parents[3]
        init_sql = (repo_root / "database/init.sql").read_text(encoding="utf-8")

        # 테이블 컬럼 명세 확인
        self.assertIn("last_accessed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP", init_sql)
        # 멱등성 마이그레이션 구문 확인
        self.assertIn("ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS last_accessed_at", init_sql)
        # 인덱스 존재 여부 확인
        self.assertIn("CREATE INDEX IF NOT EXISTS idx_analysis_jobs_last_accessed_at ON analysis_jobs (last_accessed_at)", init_sql)


if __name__ == "__main__":
    unittest.main()
