from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.agents.reporter import Reporter
from app.models.api_schemas import ReportJsonResponse

router = APIRouter(tags=["report"])

reporter = Reporter()


async def _load_ctx(job_id: str):
    """Load ReporterInput context for the given job_id from the audit DB."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": {"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found", "detail": None}},
    )


@router.get("/api/report/{job_id}", response_model=ReportJsonResponse)
async def get_report_json(job_id: str) -> ReportJsonResponse:
    """Retrieve the completed analysis report for a given job."""
    return await reporter.render(await _load_ctx(job_id))
