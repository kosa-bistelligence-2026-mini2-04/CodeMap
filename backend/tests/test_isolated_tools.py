import tempfile
from pathlib import Path
from app.tool.dir_scan import list_repository_files
from app.tool.file_read import extract_file_static_metadata
from app.tool.grep_scan import count_todo_annotations
from app.tool.env_validation import verify_build_environment
from app.tool.ast_quality import (
    calculate_code_complexity,
    calculate_module_coupling,
)


def test_list_repository_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # 임시 파일들 생성
        (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
        (tmp_path / "README.md").write_text("doc", encoding="utf-8")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "package.json").write_text("{}", encoding="utf-8")

        files = list_repository_files(tmp_path)
        filenames = [f.name for f in files]
        assert "main.py" in filenames
        assert "README.md" in filenames
        # node_modules는 무시되어야 함
        assert "package.json" not in filenames


def test_extract_file_static_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        f1 = tmp_path / "main.py"
        f1.write_text("print('hello')\n# TODO: fix", encoding="utf-8")

        meta = extract_file_static_metadata([f1], tmp_path)
        assert len(meta) == 1
        assert meta[0]["name"] == "main.py"
        assert meta[0]["lines"] == 2
        assert meta[0]["language"] == "Python"


def test_count_todo_annotations():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        f1 = tmp_path / "main.py"
        f1.write_text("# TODO: task1\n# FIXME: task2", encoding="utf-8")

        res = count_todo_annotations([f1])
        assert res["total_todos"] == 2


def test_verify_build_environment():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        f1 = tmp_path / "requirements.txt"
        f1.write_text("fastapi", encoding="utf-8")

        res = verify_build_environment([f1], "Python", tmp_path)
        assert res["has_mandatory_manifest"] is True
        assert "Python" in res["detected_stack"]


def test_calculate_code_complexity():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        f1 = tmp_path / "main.py"
        # 복잡도 2짜리 함수
        code = "def check(x):\n    if x > 10:\n        return True\n    return False"
        f1.write_text(code, encoding="utf-8")

        res = calculate_code_complexity([f1])
        assert res["average_complexity"] == 2.0
        assert res["max_complexity"] == 2


def test_calculate_module_coupling():
    deps = {
        "main.py": ["utils.py"],
        "utils.py": ["db.py"],
        "db.py": ["main.py"]  # 순환 참조 유발
    }
    res = calculate_module_coupling(deps)
    assert res["has_circular_dependency"] is True
