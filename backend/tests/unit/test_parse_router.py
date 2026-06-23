import unittest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.repo.models import AnalysisJob


class ParseRouterTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.job_id = uuid4()
        self.mock_job = AnalysisJob(
            id=self.job_id,
            repo_name="test-repo",
            owner="test-owner",
            branch="main",
            status="COMPLETED",
            report_json={
                "files": [
                    {
                        "path": "backend/app/main.py",
                        "file_type": "FILE",
                        "content": "from fastapi import FastAPI\napp = FastAPI()\n",
                        "metadata": {},
                    },
                    {
                        "path": "backend/requirements.txt",
                        "file_type": "FILE",
                        "content": "fastapi==0.115.0\nsqlalchemy==2.0.0\nasyncpg==0.30.0\n",
                        "metadata": {"is_config": True},
                    },
                    {
                        "path": "frontend/package.json",
                        "file_type": "FILE",
                        "content": '{"dependencies": {"next": "16.0.0", "react": "19.0.0"}}',
                        "metadata": {"is_config": True},
                    },
                    {
                        "path": "frontend/src/app.ts",
                        "file_type": "FILE",
                        "content": "const app = 1;\nconsole.log(app);\n",
                        "metadata": {},
                    },
                    {
                        "path": "README.md",
                        "file_type": "FILE",
                        "content": "# Test repo\nBackend and frontend sample.\n",
                        "metadata": {},
                    },
                    {
                        "path": "Dockerfile",
                        "file_type": "FILE",
                        "content": "FROM python:3.12-slim\n",
                        "metadata": {"is_config": True},
                    },
                    {
                        "path": "docker-compose.yml",
                        "file_type": "FILE",
                        "content": "services:\n  db:\n    image: postgres:16\n",
                        "metadata": {"is_config": True},
                    },
                ],
                "tech_stack": ["Python", "FastAPI"],
                "tech_stack_details": [
                    {
                        "name": "FastAPI",
                        "version": "0.115.0",
                        "category": "framework",
                        "source": "backend/requirements.txt",
                    },
                    {
                        "name": "Next.js",
                        "version": "16.0.0",
                        "category": "framework",
                        "source": "frontend/package.json",
                    },
                    {
                        "name": "Python",
                        "version": "3.12",
                        "category": "language",
                        "source": "Dockerfile",
                    },
                    {
                        "name": "PostgreSQL",
                        "version": "16",
                        "category": "database",
                        "source": "docker-compose.yml",
                    },
                ],
                "language_composition": [
                    {"language": "Config", "lines": 8, "percentage": 57.1},
                    {"language": "Python", "lines": 2, "percentage": 14.3},
                    {"language": "TypeScript", "lines": 2, "percentage": 14.3},
                    {"language": "Markdown", "lines": 2, "percentage": 14.3},
                ],
                "run_commands": ["pip install -r requirements.txt", "uvicorn app.main:app"],
                "run_command_details": {
                    "install": "pip install -r requirements.txt",
                    "run": "uvicorn app.main:app",
                    "build": None,
                },
                "entry_points": ["backend/app/main.py"],
                "entry_point_details": [
                    {"path": "backend/app/main.py", "type": "backend", "reason": "FastAPI app"}
                ],
                "readme_summary": "Test repo",
                "master_summary": "테스트 저장소 요약",
                "folder_summaries": [
                    {"path": "backend/app", "summary": "FastAPI 앱 폴더"}
                ],
                "file_summaries": [
                    {"path": "backend/app/main.py", "summary": "FastAPI 진입점"}
                ],
                "file_map": [
                    {
                        "path": "backend/app/main.py",
                        "language": "Python",
                        "chunk_count": 1,
                        "imports": [],
                        "imported_by": [],
                        "risk_score": 10,
                    }
                ],
                "heatmap": [{"path": "backend/app/main.py", "score": 10}],
            }
        )

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_analysis_success(self, mock_repo_class):
        mock_repo_instance = mock_repo_class.return_value
        mock_repo_instance.get_job_by_id = AsyncMock(return_value=self.mock_job)
        
        response = self.client.get(f"/api/parse/analysis/{self.job_id}")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["code"], 200)
        self.assertEqual(data["data"]["repoName"], "test-repo")
        self.assertEqual(data["data"]["techStack"], ["Python", "FastAPI"])
        self.assertEqual(data["data"]["runCommands"]["install"], "pip install -r requirements.txt")
        self.assertIn("└── requirements.txt", data["data"]["directoryTree"])
        self.assertEqual(len(data["data"]["files"]), 7)
        self.assertEqual(data["data"]["files"][0]["path"], "backend/app/main.py")

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_stack_returns_object_mapping(self, mock_repo_class):
        mock_repo_instance = mock_repo_class.return_value
        mock_repo_instance.get_job_by_id = AsyncMock(return_value=self.mock_job)

        response = self.client.get(f"/api/parse/analysis/{self.job_id}/stack")
        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]
        by_name = {item["name"]: item for item in data["techStack"]}
        self.assertEqual(by_name["FastAPI"]["version"], "0.115.0")
        self.assertEqual(by_name["FastAPI"]["category"], "framework")
        self.assertEqual(by_name["FastAPI"]["source"], "backend/requirements.txt")
        self.assertEqual(by_name["Next.js"]["version"], "16.0.0")
        self.assertEqual(by_name["Python"]["version"], "3.12")
        self.assertEqual(by_name["PostgreSQL"]["version"], "16")
        languages = {item["language"]: item for item in data["languageComposition"]}
        self.assertEqual(languages["Config"]["lines"], 8)
        self.assertEqual(languages["Python"]["lines"], 2)
        self.assertEqual(languages["TypeScript"]["lines"], 2)
        self.assertEqual(languages["Markdown"]["lines"], 2)
        self.assertGreater(languages["Config"]["percentage"], 0)
        self.assertEqual(data["runCommands"]["install"], "pip install -r requirements.txt")
        self.assertEqual(data["runCommands"]["run"], "uvicorn app.main:app")
        self.assertIsNone(data["runCommands"]["build"])

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_analysis_not_found(self, mock_repo_class):
        mock_repo_instance = mock_repo_class.return_value
        mock_repo_instance.get_job_by_id = AsyncMock(return_value=None)
        
        response = self.client.get(f"/api/parse/analysis/{uuid4()}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "REPOSITORY_NOT_FOUND")

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_analysis_no_result(self, mock_repo_class):
        self.mock_job.report_json = None
        mock_repo_instance = mock_repo_class.return_value
        mock_repo_instance.get_job_by_id = AsyncMock(return_value=self.mock_job)
        
        response = self.client.get(f"/api/parse/analysis/{self.job_id}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "PARSE_RESULT_NOT_FOUND")

    @patch("app.parse.router.AnalysisJobRepository")
    def test_config_files_missing_path_does_not_raise(self, mock_repo_class):
        """path 키가 없는 is_config=True 항목이 있어도 500 오류 없이 configFiles에서 제외되는지 검증."""
        mock_job = AnalysisJob(
            id=self.job_id,
            repo_name="test-repo",
            owner="test-owner",
            branch="main",
            status="COMPLETED",
            report_json={
                "files": [
                    {"path": "backend/app/main.py", "metadata": {}},
                    {"path": "backend/requirements.txt", "metadata": {"is_config": True}},
                    # path 키가 없지만 is_config=True인 항목 — KeyError 유발 케이스
                    {"metadata": {"is_config": True}},
                ],
                "tech_stack": ["Python", "FastAPI"],
                "run_commands": ["pip install -r requirements.txt", "uvicorn app.main:app"],
                "entry_points": ["backend/app/main.py"],
                "readme_summary": "Test repo",
            }
        )
        mock_repo_instance = mock_repo_class.return_value
        mock_repo_instance.get_job_by_id = AsyncMock(return_value=mock_job)

        response = self.client.get(f"/api/parse/analysis/{self.job_id}")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        config_files = data["data"]["configFiles"]
        # path가 있는 is_config 항목만 포함되어야 함
        self.assertEqual(config_files, ["backend/requirements.txt"])
        # path 없는 항목은 configFiles에 포함되지 않아야 함
        self.assertNotIn(None, config_files)

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_analysis_accepts_legacy_analyzer_report_shape(self, mock_repo_class):
        """기존 repo.analyzer report_json(stack/entrypoints)도 PARSE API에서 읽을 수 있어야 한다."""
        mock_job = AnalysisJob(
            id=self.job_id,
            repo_name="legacy-repo",
            owner="test-owner",
            branch="main",
            status="COMPLETED",
            report_json={
                "repository": {"name": "legacy-repo"},
                "stack": ["FastAPI", "Next.js"],
                "entrypoints": ["backend/app/main.py"],
                "run_commands": {"install": "pnpm install", "run": "pnpm dev", "build": "pnpm build"},
                "executive_summary": "기존 analyzer report",
                "files": [
                    {"path": "backend/app/main.py", "language": "Python"},
                    {"path": "frontend/package.json", "metadata": {"is_config": True}},
                ],
            },
        )
        mock_repo_instance = mock_repo_class.return_value
        mock_repo_instance.get_job_by_id = AsyncMock(return_value=mock_job)

        response = self.client.get(f"/api/parse/analysis/{self.job_id}")
        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]
        self.assertEqual(data["techStack"], ["FastAPI", "Next.js"])
        self.assertEqual(data["entryPoints"], ["backend/app/main.py"])
        self.assertEqual(data["runCommands"]["build"], "pnpm build")
        self.assertEqual(data["readmeSummary"], "기존 analyzer report")
        self.assertEqual(data["configFiles"], ["frontend/package.json"])

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_readme_endpoint(self, mock_repo_class):
        mock_repo_class.return_value.get_job_by_id = AsyncMock(return_value=self.mock_job)

        response = self.client.get(f"/api/parse/analysis/{self.job_id}/readme")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["repoId"], str(self.job_id))
        self.assertEqual(data["projectPurpose"], "Test repo")
        self.assertEqual(data["rawReadme"], "")

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_tree_endpoint(self, mock_repo_class):
        mock_repo_class.return_value.get_job_by_id = AsyncMock(return_value=self.mock_job)

        response = self.client.get(f"/api/parse/analysis/{self.job_id}/tree")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["entryPoints"][0]["path"], "backend/app/main.py")
        self.assertIn("backend/requirements.txt", data["configFiles"])
        self.assertIn("frontend/package.json", data["configFiles"])
        self.assertIn("Dockerfile", data["configFiles"])
        self.assertIn("docker-compose.yml", data["configFiles"])
        self.assertEqual(data["totalFiles"], 7)

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_stack_endpoint(self, mock_repo_class):
        mock_repo_class.return_value.get_job_by_id = AsyncMock(return_value=self.mock_job)

        response = self.client.get(f"/api/parse/analysis/{self.job_id}/stack")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        by_name = {item["name"]: item for item in data["techStack"]}
        self.assertEqual(by_name["FastAPI"]["name"], "FastAPI")
        self.assertEqual(data["runCommands"]["run"], "uvicorn app.main:app")

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_codemap_endpoint(self, mock_repo_class):
        mock_repo_class.return_value.get_job_by_id = AsyncMock(return_value=self.mock_job)

        response = self.client.get(f"/api/parse/analysis/{self.job_id}/codemap")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["fileMap"][0]["chunkCount"], 1)
        self.assertEqual(data["fileMap"][0]["riskScore"], 10)
        self.assertEqual(data["heatmap"][0]["score"], 10)

    @patch("app.parse.router.AnalysisJobRepository")
    def test_get_parse_summary_endpoint(self, mock_repo_class):
        mock_repo_class.return_value.get_job_by_id = AsyncMock(return_value=self.mock_job)

        response = self.client.get(f"/api/parse/analysis/{self.job_id}/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["projectSummary"], "테스트 저장소 요약")
        self.assertEqual(data["folderSummaries"][0]["path"], "backend/app")
        self.assertEqual(data["fileSummaries"][0]["summary"], "FastAPI 진입점")


if __name__ == "__main__":
    unittest.main()
