"""
분석 파이프라인 단계별 LangGraph 노드 구현

각 노드는 PipelineState를 입력받아 처리 후 갱신할 dict를 반환한다.
clone_path는 job_id + CLONE_BASE_DIR로 항상 결정되므로 DB에 저장하지 않는다.
os.path.exists()로 이미 Clone된 경우를 감지한다.

참고한 실습 섹션:
  [Sec09 - 노드 패턴]
    kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/nodes/
    각 노드 함수의 입력/반환 구조 참고
  [Sec05 - create_react_agent]
    kosa-langchain-practice/langchain/api/sec05_create_agent/
    Agent 생성 및 ainvoke() 실행 패턴 참고
  [Sec08 - RAG Agent]
    kosa-langchain-practice/langchain/api/sec08_rag/agent_rag.py
    pgvector Tool을 Agent에 연결하는 패턴 참고 (향후 연동 예정)
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from uuid import UUID

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.repo.analyzer import scan_repository
from app.repo.event_manager import event_manager
from app.repo.pipeline.state import PipelineState
from app.repo.repository import AnalysisJobRepository
from app.repo.schemas import JobStatus, PipelineStage, ProgressEvent

logger = logging.getLogger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────────────────────
# 공통 헬퍼: SSE/WebSocket 이벤트 발행
# ──────────────────────────────────────────────────────────────
async def _publish(
    job_id: str,
    stage: PipelineStage,
    status: JobStatus,
    progress: int,
    message: str,
) -> None:
    await event_manager.publish(job_id, ProgressEvent(
        stage=stage,
        status=status,
        progress=progress,
        message=message,
        timestamp=datetime.now(timezone.utc),
    ))


# ──────────────────────────────────────────────────────────────
# 공통 헬퍼: DB 분석 작업 상태 업데이트
# ──────────────────────────────────────────────────────────────
async def _update_db(job_id: str, **kwargs) -> None:
    async with async_session_factory() as session:
        repository = AnalysisJobRepository(session)
        await repository.update_job_status(job_id=UUID(job_id), **kwargs)
        await session.commit()


# ──────────────────────────────────────────────────────────────
# 노드 1: Git Clone
#
# [Sec09 - 노드 패턴]
# kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/nodes/account_node.py
# PipelineState를 입력받아 Clone 완료 후 clone_path를 상태에 반환한다.
#
# clone_path는 job_id + CLONE_BASE_DIR로 항상 결정되므로 DB에 저장하지 않는다.
# os.path.exists()로 이미 Clone된 경우를 감지하여 단계를 건너뛴다.
# ──────────────────────────────────────────────────────────────
async def clone_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    clone_path = os.path.join(settings.CLONE_BASE_DIR, job_id, "repo")
    force_refresh = bool(state.get("force_refresh", False))

    if force_refresh and os.path.exists(clone_path):
        shutil.rmtree(os.path.dirname(clone_path), ignore_errors=True)

    is_local_upload = os.path.isfile(os.path.join(clone_path, ".codemap-upload"))
    if os.path.isdir(os.path.join(clone_path, ".git")) or is_local_upload:
        await _publish(job_id, PipelineStage.CLONE, JobStatus.IN_PROGRESS, 20, "기존 저장소 스냅샷 확인")
        return {
            "clone_path": clone_path,
            "current_stage": PipelineStage.CLONE.value,
            "progress": 20,
            "status": JobStatus.IN_PROGRESS.value,
            "error": None,
        }

    await _publish(job_id, PipelineStage.CLONE, JobStatus.IN_PROGRESS, 5, "저장소 복제 준비 중")
    try:
        shutil.rmtree(os.path.dirname(clone_path), ignore_errors=True)
        os.makedirs(os.path.dirname(clone_path), exist_ok=True)
        command = ["git", "clone", "--depth", "1"]
        if state.get("branch") and state["branch"] != "default":
            command.extend(["--branch", state["branch"]])
        command.extend([state["repo_url"], clone_path])
        # asyncio.create_subprocess_exec는 Windows의 SelectorEventLoop(uvicorn --reload)에서
        # NotImplementedError를 던진다. 어느 이벤트 루프에서도 동작하도록 스레드에서 subprocess.run을 실행한다.
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            capture_output=True,
            timeout=settings.CLONE_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="replace").strip() or "git clone failed")

        await _update_db(
            job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.CLONE.value,
            progress=20,
            message="저장소 복제 완료",
        )
        await _publish(job_id, PipelineStage.CLONE, JobStatus.IN_PROGRESS, 20, "저장소 복제 완료")
        return {
            "clone_path": clone_path,
            "current_stage": PipelineStage.CLONE.value,
            "progress": 20,
            "status": JobStatus.IN_PROGRESS.value,
            "error": None,
        }
    except Exception as exc:
        logger.exception("Clone failed for job %s", job_id)
        await _update_db(job_id, status=JobStatus.FAILED.value, message=f"Clone 실패: {exc}")
        await _publish(job_id, PipelineStage.CLONE, JobStatus.FAILED, 0, f"Clone 실패: {exc}")
        return {"status": JobStatus.FAILED.value, "error": str(exc)}


# ──────────────────────────────────────────────────────────────
# 노드 2: 코드 구조 분석 (Code Map)
#
# [Sec05 - create_react_agent]
# kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
# Agent를 생성하고 ainvoke()로 코드 구조를 분석한다.
#
# [Sec08 - RAG Agent]
# kosa-langchain-practice/langchain/api/sec08_rag/agent_rag.py 참고
# 추후 pgvector similarity_search Tool을 Agent에 연결하여 분석 정확도를 높인다.
# ──────────────────────────────────────────────────────────────
async def code_map_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    await _publish(job_id, PipelineStage.CODE_MAP, JobStatus.IN_PROGRESS, 28, "파일 구조와 기술 스택 분석 중")
    try:
        report = await asyncio.to_thread(
            scan_repository,
            state["clone_path"],
            state["repo_name"],
        )
        await _update_db(
            job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.CODE_MAP.value,
            progress=55,
            message=f"{report['stats']['files']}개 파일 구조 분석 완료",
            report_json=report,
        )
        await _publish(job_id, PipelineStage.CODE_MAP, JobStatus.IN_PROGRESS, 55, "구조 분석 완료")
        return {
            "analysis_report": report,
            "current_stage": PipelineStage.CODE_MAP.value,
            "progress": 55,
        }
    except Exception as exc:
        logger.exception("Repository scan failed for job %s", job_id)
        await _update_db(job_id, status=JobStatus.FAILED.value, message=f"코드 분석 실패: {exc}")
        await _publish(job_id, PipelineStage.CODE_MAP, JobStatus.FAILED, 21, f"코드 분석 실패: {exc}")
        return {"status": JobStatus.FAILED.value, "error": str(exc)}


# ──────────────────────────────────────────────────────────────
# 노드 3: 문서 자동 생성 (Doc Generation)
#
# [Sec05 - create_react_agent]
# kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
# 코드 분석 결과를 바탕으로 파일/폴더 단위 요약 문서를 생성한다.
# ──────────────────────────────────────────────────────────────
async def doc_gen_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    await _publish(job_id, PipelineStage.DOC_GEN, JobStatus.IN_PROGRESS, 64, "분석 근거와 읽기 순서 구성 중")
    report = dict(state.get("analysis_report") or {})
    report["reading_order"] = list(report.get("entrypoints", []))[:8]
    await _update_db(
        job_id,
        status=JobStatus.IN_PROGRESS.value,
        stage=PipelineStage.DOC_GEN.value,
        progress=72,
        message="근거 기반 분석 문서 구성 완료",
        report_json=report,
    )
    return {"analysis_report": report, "current_stage": PipelineStage.DOC_GEN.value, "progress": 72}


# ──────────────────────────────────────────────────────────────
# 노드 4: 온보딩 가이드 생성 (Onboarding)
#
# [Sec05 - create_react_agent]
# kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
# 신입 개발자를 위한 추천 읽기 순서, 수정 시작점, 위험 파일 목록을 생성한다.
# ──────────────────────────────────────────────────────────────
async def onboarding_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    await _publish(job_id, PipelineStage.ONBOARDING, JobStatus.IN_PROGRESS, 80, "온보딩 경로 생성 중")
    report = dict(state.get("analysis_report") or {})
    entrypoints = report.get("entrypoints", [])
    report["onboarding_steps"] = [
        {"title": "실행 경계 확인", "files": entrypoints[:3]},
        {"title": "핵심 기능 흐름 추적", "files": entrypoints[3:6]},
        {"title": "테스트와 배포 구성 검증", "files": entrypoints[6:9]},
    ]
    await _update_db(
        job_id,
        status=JobStatus.IN_PROGRESS.value,
        stage=PipelineStage.ONBOARDING.value,
        progress=90,
        message="온보딩 경로 생성 완료",
        report_json=report,
    )
    return {"analysis_report": report, "current_stage": PipelineStage.ONBOARDING.value, "progress": 90}


# ──────────────────────────────────────────────────────────────
# 노드 5: 최종 결과 저장 (Report)
#
# [Sec09 - gather_node]
# kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/nodes/gather_node.py
# 모든 이전 노드의 Agent 결과를 취합하여 최종 리포트를 DB에 저장한다.
# ──────────────────────────────────────────────────────────────
async def report_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    report = dict(state.get("analysis_report") or {})
    report["job_id"] = job_id
    report["status"] = "completed"
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    report["model_used"] = state.get("model", "auto")
    await _update_db(
        job_id,
        status=JobStatus.COMPLETED.value,
        stage=PipelineStage.REPORT.value,
        progress=100,
        message="실제 저장소 스냅샷 분석 완료",
        report_json=report,
    )
    await _publish(job_id, PipelineStage.REPORT, JobStatus.COMPLETED, 100, "분석 완료")
    return {
        "analysis_report": report,
        "current_stage": PipelineStage.REPORT.value,
        "progress": 100,
        "status": JobStatus.COMPLETED.value,
        "error": None,
    }
