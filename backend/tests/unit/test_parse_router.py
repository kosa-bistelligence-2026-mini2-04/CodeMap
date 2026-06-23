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
                    {"path": "backend/app/main.py", "metadata": {}},
                    {"path": "backend/requirements.txt", "metadata": {"is_config": True}}
                ],
                "tech_stack": ["Python", "FastAPI"],
                "run_commands": ["pip install -r requirements.txt", "uvicorn app.main:app"],
                "entry_points": ["backend/app/main.py"],
                "readme_summary": "Test repo",
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
        self.assertEqual(len(data["data"]["files"]), 2)
        self.assertEqual(data["data"]["files"][0]["path"], "backend/app/main.py")

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


if __name__ == "__main__":
    unittest.main()
