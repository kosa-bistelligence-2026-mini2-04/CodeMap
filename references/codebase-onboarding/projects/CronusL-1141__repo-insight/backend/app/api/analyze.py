from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.models.api_schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["analyze"])


@router.post("/api/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_analysis(payload: AnalyzeRequest) -> AnalyzeResponse:
    """Submit a repository for analysis. Returns a job_id immediately; analysis runs async."""
    job_id = str(uuid.uuid4())
    return AnalyzeResponse(
        job_id=job_id,
        status="queued",
        created_at=datetime.now(timezone.utc),
        ws_url=f"/ws/progress/{job_id}",
    )
