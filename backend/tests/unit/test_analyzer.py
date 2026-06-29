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
        self.assertIn("duplicate_code_ratio", report["health_metrics"])

    def test_health_score_does_not_penalize_missing_tests(self):
        (self.root / "tests" / "main.test.ts").unlink()
        (self.root / "src" / "main.ts").write_text(
            "export function boot() { return 'ready' }\n",
            encoding="utf-8",
        )

        report = scan_repository(str(self.root), "sample")

        self.assertEqual(report["stats"]["tests"], 0)
        self.assertEqual(report["health_metrics"]["test_ratio"], 0.0)
        self.assertEqual(report["health_score"], 100)
        self.assertNotIn("테스트", " ".join(report["key_risks"]))
        self.assertFalse(
            any("테스트" in item["title"] for item in report["recommendations"])
        )

    def test_duplicate_code_ratio_affects_health_score(self):
        duplicated = "\n".join(
            f"const duplicatedValue{i} = calculateSharedThing(inputValue{i});"
            for i in range(12)
        )
        (self.root / "src" / "alpha.ts").write_text(duplicated, encoding="utf-8")
        (self.root / "src" / "beta.ts").write_text(duplicated, encoding="utf-8")

        report = scan_repository(str(self.root), "sample")

        self.assertGreaterEqual(report["health_metrics"]["duplicate_code_ratio"], 0.08)
        self.assertLess(report["health_score"], 99)
        self.assertTrue(any("반복" in risk for risk in report["key_risks"]))
        self.assertTrue(
            any(item["title"] == "반복 코드 공통화" for item in report["recommendations"])
        )

    def test_search_returns_file_and_line_reference(self):
        results = search_repository(str(self.root), "ready telemetry", limit=3)
        self.assertTrue(results)
        self.assertEqual(results[0]["file"], "src/main.ts")
        self.assertGreaterEqual(results[0]["line"], 1)


if __name__ == "__main__":
    unittest.main()
