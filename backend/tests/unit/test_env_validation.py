import tempfile
import unittest
from pathlib import Path

from app.tool.env_validation_tool import (
    analyze_env_validation,
    calculate_env_validation,
)


class EnvValidationToolTests(unittest.TestCase):
    def test_complete_project_gets_full_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
            (root / ".env.example").write_text("API_KEY=\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / "package-lock.json").write_text("{}", encoding="utf-8")
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "ci.yml").write_text(
                "name: CI\n",
                encoding="utf-8",
            )

            self.assertEqual(
                calculate_env_validation(str(root)),
                {"security": 100, "quality": 100},
            )

    def test_path_traversal_falls_back_to_neutral_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root.parent / "outside-env-validation.txt"
            outside.write_text("token = 'secret'\n", encoding="utf-8")
            try:
                self.assertEqual(
                    calculate_env_validation(str(root), "../outside-env-validation.txt"),
                    {"security": 50, "quality": 50},
                )
            finally:
                outside.unlink(missing_ok=True)

    def test_hardcoded_secret_penalizes_security(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("API_KEY = 'abc123'\n", encoding="utf-8")

            scores = calculate_env_validation(str(root))

            self.assertLess(scores["security"], 100)
            self.assertEqual(scores["quality"], 50)

    def test_text_formatter_uses_calculated_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = analyze_env_validation(str(root))

            self.assertIn("Security Score:", result)
            self.assertIn("Quality Score:", result)


if __name__ == "__main__":
    unittest.main()
