import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import InvalidRepoUrlError, RepositoryNotFoundError, ValidationFailedError
from app.list.service import ListService, _should_exclude_path


# ──────────────────────────────────────────────
# TestPreValidateHelper
# ──────────────────────────────────────────────
class TestPreValidateHelper(unittest.TestCase):
    """
    _should_exclude_path 헬퍼 함수를 검증하는 단위 테스트 클래스입니다.
    """

    def test_should_exclude_path_excluded_dirs(self):
        """EXCLUDED_DIRS 내에 포함된 디렉토리를 가진 경로를 제외하는지 검사합니다."""
        self.assertTrue(_should_exclude_path("node_modules/express/index.js"))
        self.assertTrue(_should_exclude_path(".venv/lib/python3.12/site-packages/pip/main.py"))
        self.assertTrue(_should_exclude_path("src/__pycache__/utils.cpython-312.pyc"))

    def test_should_exclude_path_excluded_file_names(self):
        """EXCLUDED_FILE_NAMES 내에 포함된 파일명을 제외하는지 검사합니다."""
        self.assertTrue(_should_exclude_path("src/.env"))
        self.assertTrue(_should_exclude_path("keys/id_rsa"))

    def test_should_exclude_path_excluded_file_extensions(self):
        """EXCLUDED_FILE_EXTENSIONS 내에 포함된 확장자를 가진 파일을 제외하는지 검사합니다."""
        self.assertTrue(_should_exclude_path("certs/private.key"))
        self.assertTrue(_should_exclude_path("database/store.keystore"))

    def test_should_exclude_path_binary_extensions(self):
        """이미지, 오디오 등 바이너리 파일 확장자를 가진 파일을 제외하는지 검사합니다."""
        self.assertTrue(_should_exclude_path("images/logo.png"))
        self.assertTrue(_should_exclude_path("assets/bg.jpg"))
        self.assertTrue(_should_exclude_path("documents/guide.pdf"))
        self.assertTrue(_should_exclude_path("build/app.exe"))

    def test_should_exclude_path_allowed_paths(self):
        """허용된 파일 경로는 제외하지 않는지 검사합니다."""
        self.assertFalse(_should_exclude_path("src/main.py"))
        self.assertFalse(_should_exclude_path("README.md"))
        self.assertFalse(_should_exclude_path("backend/app/main.py"))


# ──────────────────────────────────────────────
# TestPreValidateService
# ──────────────────────────────────────────────
class TestPreValidateService(unittest.IsolatedAsyncioTestCase):
    """
    ListService.validate_repository 메서드를 검증하는 단위 테스트 클래스입니다.
    """

    def setUp(self):
        self.db = MagicMock()
        self.service = ListService(self.db)

    @patch("httpx.AsyncClient.get")
    async def test_validate_repository_success(self, mock_get):
        """제한 조건 이내의 정상적인 레포지토리가 성공적으로 검증되는지 확인합니다."""
        # 1. GET /repos/{owner}/{repo} 응답 모킹
        mock_response_repo = MagicMock()
        mock_response_repo.status_code = 200
        mock_response_repo.json.return_value = {"default_branch": "main"}

        ## 2. GET /repos/{owner}/{repo}/git/trees/main?recursive=1 응답 모킹
        mock_response_tree = MagicMock()
        mock_response_tree.status_code = 200
        mock_response_tree.json.return_value = {
            "truncated": False,
            "tree": [
                {"path": "src/main.py", "type": "blob", "size": 1024},
                {"path": "README.md", "type": "blob", "size": 2048},
                {"path": "node_modules/express/index.js", "type": "blob", "size": 512},  ## 제외되어야 함
            ]
        }

        mock_get.side_effect = [mock_response_repo, mock_response_tree]

        res = await self.service.validate_repository(
            repo_url="https://github.com/example/target-repo",
            branch=None
        )

        self.assertEqual(res.code, 200)
        self.assertEqual(res.message, "success")
        self.assertTrue(res.data.is_valid)
        self.assertEqual(res.data.file_count, 2)  # node_modules 제외됨
        self.assertEqual(res.data.total_size_kb, 3)  # 1024 + 2048 = 3072 bytes -> 3 KB
        self.assertIsNone(res.data.warning_message)

    @patch("httpx.AsyncClient.get")
    async def test_validate_repository_file_count_warning(self, mock_get):
        """파일 수가 100개를 초과할 때 warningMessage가 올바르게 설정되는지 확인합니다."""
        ## branch를 명시하면 tree API 호출 1회만 발생하므로 mock 1개만 설정
        mock_tree = []
        for i in range(101):
            mock_tree.append({"path": f"src/file_{i}.py", "type": "blob", "size": 100})

        mock_response_tree = MagicMock()
        mock_response_tree.status_code = 200
        mock_response_tree.json.return_value = {"tree": mock_tree, "truncated": False}

        mock_get.side_effect = [mock_response_tree]

        res = await self.service.validate_repository(
            repo_url="https://github.com/example/large-repo",
            branch="main"
        )

        self.assertEqual(res.code, 200)
        self.assertFalse(res.data.is_valid)
        self.assertEqual(res.data.file_count, 101)
        self.assertIn("100개를 초과", res.data.warning_message)


    @patch("httpx.AsyncClient.get")
    async def test_validate_repository_file_size_warning(self, mock_get):
        """100KB를 초과하는 파일이 존재할 때 warningMessage가 올바르게 설정되는지 확인합니다."""
        mock_response_tree = MagicMock()
        mock_response_tree.status_code = 200
        mock_response_tree.json.return_value = {
            "truncated": False,
            "tree": [
                {"path": "src/large_file.py", "type": "blob", "size": 102401},  ## 100KB 초과
                {"path": "src/small_file.py", "type": "blob", "size": 100},
            ]
        }

        mock_get.side_effect = [mock_response_tree]

        res = await self.service.validate_repository(
            repo_url="https://github.com/example/large-repo",
            branch="main"
        )

        self.assertEqual(res.code, 200)
        self.assertFalse(res.data.is_valid)
        self.assertEqual(res.data.file_count, 2)
        self.assertIn("100KB를 초과하는 대용량 파일", res.data.warning_message)

    @patch("httpx.AsyncClient.get")
    async def test_validate_repository_truncated(self, mock_get):
        """GitHub Trees API가 truncated=true를 반환할 때 isValid=false가 내려오는지 확인합니다."""
        mock_response_tree = MagicMock()
        mock_response_tree.status_code = 200
        mock_response_tree.json.return_value = {
            "truncated": True,
            "tree": []
        }

        mock_get.side_effect = [mock_response_tree]

        res = await self.service.validate_repository(
            repo_url="https://github.com/example/huge-repo",
            branch="main"
        )

        self.assertEqual(res.code, 200)
        self.assertFalse(res.data.is_valid)
        self.assertIsNotNone(res.data.warning_message)
        self.assertTrue(res.data.is_truncated)

    async def test_validate_repository_invalid_url(self):
        """잘못된 URL 형식에 대해 InvalidRepoUrlError 예외를 발생시키는지 확인합니다."""
        with self.assertRaises(InvalidRepoUrlError):
            await self.service.validate_repository("not-a-valid-url")

    @patch("httpx.AsyncClient.get")
    async def test_validate_repository_not_found(self, mock_get):
        """존재하지 않는 저장소에 대해 RepositoryNotFoundError 예외를 발생시키는지 확인합니다."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with self.assertRaises(RepositoryNotFoundError):
            await self.service.validate_repository("https://github.com/example/nonexistent-repo")

    @patch("httpx.AsyncClient.get")
    async def test_validate_repository_empty_repo_error(self, mock_get):
        """분석 가능한 파일 수가 0개일 때 ValidationFailedError 예외를 발생시키는지 검사합니다."""
        mock_response_tree = MagicMock()
        mock_response_tree.status_code = 200
        mock_response_tree.json.return_value = {
            "truncated": False,
            "tree": [
                {"path": "node_modules/express/index.js", "type": "blob", "size": 512},  # 제외됨
            ]
        }

        mock_get.side_effect = [mock_response_tree]

        with self.assertRaises(ValidationFailedError) as context:
            await self.service.validate_repository(
                repo_url="https://github.com/example/empty-repo",
                branch="main"
            )
        self.assertIn("분석 가능한 파일이 없습니다", str(context.exception))

    @patch("httpx.AsyncClient.get")
    async def test_validate_repository_default_branch_invalid_type(self, mock_get):
        """저장소 정보 API 응답 형식이 dict가 아닐 때 ValidationFailedError 예외를 발생시키는지 검사합니다."""
        mock_response_repo = MagicMock()
        mock_response_repo.status_code = 200
        mock_response_repo.json.return_value = ["not", "a", "dict"]

        mock_get.side_effect = [mock_response_repo]

        with self.assertRaises(ValidationFailedError) as context:
            await self.service.validate_repository(
                repo_url="https://github.com/example/target-repo",
                branch=None
            )
        self.assertIn("API 응답 형식이 올바르지 않습니다", str(context.exception))

    @patch("httpx.AsyncClient.get")
    async def test_validate_repository_default_branch_missing(self, mock_get):
        """응답에 default_branch 키가 누락되었을 때 ValidationFailedError 예외를 발생시키는지 검사합니다."""
        mock_response_repo = MagicMock()
        mock_response_repo.status_code = 200
        mock_response_repo.json.return_value = {"other_key": "value"}

        mock_get.side_effect = [mock_response_repo]

        with self.assertRaises(ValidationFailedError) as context:
            await self.service.validate_repository(
                repo_url="https://github.com/example/target-repo",
                branch=None
            )
        self.assertIn("기본 브랜치(default_branch)를 찾을 수 없습니다", str(context.exception))

    @patch("httpx.AsyncClient.get")
    async def test_validate_repository_default_branch_empty(self, mock_get):
        """default_branch 값이 None이거나 빈 문자열일 때 ValidationFailedError 예외를 발생시키는지 검사합니다."""
        # 1. default_branch가 None인 경우
        mock_response_repo1 = MagicMock()
        mock_response_repo1.status_code = 200
        mock_response_repo1.json.return_value = {"default_branch": None}

        # 2. default_branch가 빈 문자열인 경우
        mock_response_repo2 = MagicMock()
        mock_response_repo2.status_code = 200
        mock_response_repo2.json.return_value = {"default_branch": ""}

        mock_get.side_effect = [mock_response_repo1, mock_response_repo2]

        with self.assertRaises(ValidationFailedError) as context:
            await self.service.validate_repository(
                repo_url="https://github.com/example/target-repo",
                branch=None
            )
        self.assertIn("기본 브랜치(default_branch)를 찾을 수 없습니다", str(context.exception))

        with self.assertRaises(ValidationFailedError) as context:
            await self.service.validate_repository(
                repo_url="https://github.com/example/target-repo",
                branch=None
            )
        self.assertIn("기본 브랜치(default_branch)를 찾을 수 없습니다", str(context.exception))


if __name__ == "__main__":
    unittest.main()
