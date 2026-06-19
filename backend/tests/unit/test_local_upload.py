import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.core.exceptions import CodeMapException
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


class LocalUploadStorageTests(unittest.IsolatedAsyncioTestCase):
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
