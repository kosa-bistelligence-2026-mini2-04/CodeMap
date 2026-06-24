"""RAG-PARSE B-202 directory 보안/견고성 회귀 테스트 (이슈 #53).

1. 민감파일 이름 대소문자 우회 차단 (.ENV 등)
2. cp949/EUC-KR 소스 무음 드롭 방지 (인코딩 폴백)
3. 파일 수 상한 (rglob 무제한 → OOM/장시간 방지)
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.parse import directory as dir_module


class DirectoryHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def test_sensitive_file_name_is_case_insensitive(self):
        # .ENV(대문자)도 민감파일로 차단되어 content를 읽지 않아야 한다.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ENV").write_text("SECRET=abc123\n", encoding="utf-8")
            (root / "main.py").write_text("x = 1\n", encoding="utf-8")
            files = await dir_module.analyze_directory(str(root))
        by_path = {f.path: f for f in files}
        self.assertIsNone(by_path[".ENV"].content)         # 비밀 미노출
        self.assertIsNotNone(by_path["main.py"].content)   # 일반 파일은 정상

    async def test_cp949_korean_source_not_silently_dropped(self):
        # cp949로 저장된 한국어 소스가 None으로 드롭되지 않고 디코딩되어야 한다.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ko.py").write_bytes("# 한국어 주석\nx = 1\n".encode("cp949"))
            files = await dir_module.analyze_directory(str(root))
        by_path = {f.path: f for f in files}
        self.assertIsNotNone(by_path["ko.py"].content)
        self.assertIn("한국어", by_path["ko.py"].content)

    async def test_file_count_cap_truncates(self):
        # _MAX_FILES 초과 파일은 FILE 노드에서 제외된다 (상한 동작).
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(5):
                (root / f"f{i}.py").write_text(f"x = {i}\n", encoding="utf-8")
            with patch.object(dir_module, "_MAX_FILES", 2):
                files = await dir_module.analyze_directory(str(root))
        file_nodes = [f for f in files if f.file_type == "FILE"]
        self.assertEqual(len(file_nodes), 2)
