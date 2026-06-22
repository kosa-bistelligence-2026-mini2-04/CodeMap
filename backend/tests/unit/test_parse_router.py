import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.repo.models import AnalysisJob
from app.core.exceptions import ParseResultNotFoundError

client = TestClient(app)

@pytest.fixture
def mock_job():
    job_id = uuid4()
    return AnalysisJob(
        id=job_id,
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
def test_get_parse_analysis_success(mock_repo_class, mock_job):
    mock_repo_instance = mock_repo_class.return_value
    mock_repo_instance.get_job_by_id = AsyncMock(return_value=mock_job)
    
    response = client.get(f"/api/parse/analysis/{mock_job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["repoName"] == "test-repo"
    assert data["data"]["techStack"] == ["Python", "FastAPI"]
    assert data["data"]["runCommands"]["install"] == "pip install -r requirements.txt"
    assert "└── requirements.txt" in data["data"]["directoryTree"]

@patch("app.parse.router.AnalysisJobRepository")
def test_get_parse_analysis_not_found(mock_repo_class):
    mock_repo_instance = mock_repo_class.return_value
    mock_repo_instance.get_job_by_id = AsyncMock(return_value=None)
    
    response = client.get(f"/api/parse/analysis/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REPOSITORY_NOT_FOUND"

@patch("app.parse.router.AnalysisJobRepository")
def test_get_parse_analysis_no_result(mock_repo_class, mock_job):
    mock_job.report_json = None
    mock_repo_instance = mock_repo_class.return_value
    mock_repo_instance.get_job_by_id = AsyncMock(return_value=mock_job)
    
    response = client.get(f"/api/parse/analysis/{mock_job.id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PARSE_RESULT_NOT_FOUND"
