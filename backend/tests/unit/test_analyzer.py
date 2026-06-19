import tempfile
import unittest
from pathlib import Path

from app.repo.analyzer import scan_repository, search_repository


class RepositoryAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "package.json").write_text('{"dependencies":{"next":"16"}}', encoding="utf-8")
        (self.root / "next.config.ts").write_text("export default {}", encoding="utf-8")
        (self.root / "src" / "main.ts").write_text(
            "export function boot() { return 'ready' }\n// TODO: add telemetry\n",
            encoding="utf-8",
        )
        (self.root / "tests" / "main.test.ts").write_text(
            "import { boot } from '../src/main'\ntest('boot', () => boot())\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_reports_grounded_repository_facts(self):
        report = scan_repository(str(self.root), "sample")
        self.assertEqual(report["repository"]["name"], "sample")
        self.assertEqual(report["stats"]["files"], 4)
        self.assertEqual(report["stats"]["tests"], 1)
        self.assertIn("Next.js", report["stack"])
        self.assertIn("src/main.ts", report["entrypoints"])

    def test_search_returns_file_and_line_reference(self):
        results = search_repository(str(self.root), "ready telemetry", limit=3)
        self.assertTrue(results)
        self.assertEqual(results[0]["file"], "src/main.ts")
        self.assertGreaterEqual(results[0]["line"], 1)


if __name__ == "__main__":
    unittest.main()
