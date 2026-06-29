import tempfile
import unittest
from pathlib import Path
from app.tool.ast_quality_tool import calculate_ast_quality

class ASTQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ast_quality_empty_dir(self):
        """빈 디렉터리에서의 품질 점수는 기본값(80, 80)을 반환해야 한다."""
        metrics = calculate_ast_quality(str(self.tmp_path))
        self.assertEqual(metrics["complexity"], 80)
        self.assertEqual(metrics["modularity"], 80)

    def test_ast_quality_valid_python(self):
        """정상 파이썬 코드에서의 품질 점수를 측정한다."""
        py_file = self.tmp_path / "valid.py"
        py_file.write_text(
            "import os\n"
            "import sys\n"
            "def foo():\n"
            "    if True:\n"
            "        pass\n",
            encoding="utf-8"
        )
        
        metrics = calculate_ast_quality(str(self.tmp_path))
        self.assertIn("complexity", metrics)
        self.assertIn("modularity", metrics)
        self.assertEqual(metrics["complexity"], 90)
        self.assertEqual(metrics["modularity"], 96)

    def test_ast_quality_syntax_error(self):
        """문법 오류가 있는 파이썬 파일은 예외처리하고 나머지 점수에 반영하지 않는다."""
        py_file = self.tmp_path / "error.py"
        py_file.write_text("def foo( :::", encoding="utf-8")
        
        metrics = calculate_ast_quality(str(self.tmp_path))
        self.assertEqual(metrics["complexity"], 80)
        self.assertEqual(metrics["modularity"], 80)

    def test_ast_quality_exclude_dirs(self):
        """venv 등 제외 대상 폴더에 있는 파이썬 코드는 분석 대상에서 제외한다."""
        venv_dir = self.tmp_path / "venv"
        venv_dir.mkdir()
        py_file = venv_dir / "lib.py"
        py_file.write_text(
            "import os\n"
            "def excluded():\n"
            "    if True: pass\n", 
            encoding="utf-8"
        )
        
        metrics = calculate_ast_quality(str(self.tmp_path))
        self.assertEqual(metrics["complexity"], 80)
        self.assertEqual(metrics["modularity"], 80)

if __name__ == "__main__":
    unittest.main()
