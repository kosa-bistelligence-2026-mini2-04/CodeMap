import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.common.exceptions import CodeMapException
from app.repo.local_upload import normalize_upload_path, save_local_upload


class LocalUploadPathTests(unittest.TestCase):
    def test_strips_selected_root_folder(self):
        self.assertEqual(
            normalize_upload_path("sample/src/main.py", "sample"),
            Path("src/main.py"),
        )

    def test_ignores_dependencies_and_environment_files(self):
        self.assertIsNone(normalize_upload_path("sample/node_modules/pkg/index.js", "sample"))
        self.assertIsNone(normalize_upload_path("sample/.env.local", "sample"))
        self.assertEqual(normalize_upload_path("sample/.env.example", "sample"), Path(".env.example"))

    def test_rejects_path_traversal(self):
        with self.assertRaises(CodeMapException):
            normalize_upload_path("sample/../secret.txt", "sample")

    def test_strips_windows_drive_and_unc_paths(self):
        self.assertEqual(normalize_upload_path("C:\\sample\\src\\main.py", "sample"), Path("src/main.py"))
        self.assertEqual(normalize_upload_path("\\\\sample\\src\\main.py", "sample"), Path("src/main.py"))

    def test_sanitizes_invalid_filenames(self):
        self.assertEqual(normalize_upload_path("sample/src/con<fig>:1|2?.txt", "sample"), Path("src/con_fig__1_2_.txt"))

    def test_sanitizes_invalid_directory_segments(self):
        self.assertEqual(
            normalize_upload_path("sample/src\0evil/mod<ules>/main.py", "sample"),
            Path("src_evil/mod_ules_/main.py"),
        )


from unittest.mock import patch

class LocalUploadStorageTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.repo.local_upload.shutil.rmtree")
    async def test_rejects_symlink_paths(self, mock_rmtree):
        import os
        import sys
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "job" / "repo"
            destination.mkdir(parents=True)
            
            if sys.platform == "win32":
                try:
                    test_link = Path(temp_dir) / "test_link"
                    os.symlink(temp_dir, test_link)
                    os.unlink(test_link)
                except OSError:
                    self.skipTest("Windows 환경에서 심볼릭 링크 생성을 위한 관리자 권한이 결여되어 테스트를 스킵합니다.")

            symlink_dir = destination / "src"
            os.symlink(temp_dir, symlink_dir)
            upload = UploadFile(filename="main.py", file=BytesIO(b"print('ready')\n"))
            with self.assertRaisesRegex(CodeMapException, "심볼릭 링크는 업로드할 수 없습니다"):
                await save_local_upload([upload], ["sample/src/main.py"], "sample", destination)
    async def test_reconstructs_repository_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "job" / "repo"
            upload = UploadFile(filename="main.py", file=BytesIO(b"print('ready')\n"))

            count, total_bytes = await save_local_upload(
                [upload],
                ["sample/src/main.py"],
                "sample",
                destination,
            )

            self.assertEqual(count, 1)
            self.assertEqual(total_bytes, 15)
            self.assertEqual((destination / "src/main.py").read_text(), "print('ready')\n")
            self.assertTrue((destination / ".codemap-upload").is_file())


if __name__ == "__main__":
    unittest.main()
