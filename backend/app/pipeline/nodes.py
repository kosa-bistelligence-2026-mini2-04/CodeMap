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
    pgvector Tool을 Agent에 연결하는 패턴 참고
    현재 대화형 Agent 검색은 app.agent.tools.hybrid_search에서 별도 제공한다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ValidationError

from app.infra.config import get_settings
from app.infra.database import async_session_factory
from app.repo.analyzer import scan_repository
from app.repo.event_manager import event_manager
from app.pipeline.state import PipelineState
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
    _t0 = time.perf_counter()

    if force_refresh and os.path.exists(clone_path):
        shutil.rmtree(os.path.dirname(clone_path), ignore_errors=True)

    is_local_upload = os.path.isfile(os.path.join(clone_path, ".codemap-upload"))
    if os.path.isdir(os.path.join(clone_path, ".git")) or is_local_upload:
        await _update_db(
            job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.CLONE.value,
            progress=20,
            message="기존 저장소 스냅샷 확인",
        )
        await _publish(job_id, PipelineStage.CLONE, JobStatus.IN_PROGRESS, 20, "기존 저장소 스냅샷 확인")
        elapsed = time.perf_counter() - _t0
        logger.info("[단계별 소요시간] job=%s | 1.저장소 복제(캐시 적중)=%.3f초", job_id, elapsed)
        return {
            "clone_path": clone_path,
            "current_stage": PipelineStage.CLONE.value,
            "progress": 20,
            "status": JobStatus.IN_PROGRESS.value,
            "error": None,
            "timings": {**state.get("timings", {}), "clone": elapsed},
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

        elapsed = time.perf_counter() - _t0
        logger.info("[단계별 소요시간] job=%s | 1.저장소 복제=%.3f초", job_id, elapsed)
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
            "timings": {**state.get("timings", {}), "clone": elapsed},
        }
    except Exception as exc:
        # 실패 시점까지 소요된 시간도 timings에 누적 (리뷰어 제안 1 반영)
        # 네트워크 지연 등 실패 전 대기 시간을 "clone_failed"로 구분해 기록한다.
        elapsed = time.perf_counter() - _t0
        logger.exception("Clone failed for job %s (%.3f초 경과 후 실패)", job_id, elapsed)
        await _update_db(job_id, status=JobStatus.FAILED.value, message=f"Clone 실패: {exc}")
        await _publish(job_id, PipelineStage.CLONE, JobStatus.FAILED, 0, f"Clone 실패: {exc}")
        return {
            "status": JobStatus.FAILED.value,
            "error": str(exc),
            "timings": {**state.get("timings", {}), "clone_failed": elapsed},
        }


# ──────────────────────────────────────────────────────────────
# 노드 2: 코드 구조 분석 (Code Map)
#
# [Sec05 - create_react_agent]
# kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
# Agent를 생성하고 ainvoke()로 코드 구조를 분석한다.
#
# [Sec08 - RAG Agent]
# kosa-langchain-practice/langchain/api/sec08_rag/agent_rag.py 참고
# pgvector 기반 similarity search는 대화형 Agent Graph의 Hybrid Search worker에서 수행한다.
# ──────────────────────────────────────────────────────────────
async def code_map_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    _t0 = time.perf_counter()
    await _publish(job_id, PipelineStage.CODE_MAP, JobStatus.IN_PROGRESS, 28, "파일 구조와 기술 스택 분석 중")
    try:
        # clone_path는 PipelineState에서 Optional[str]이지만 clone_node 완료 후 항상 설정된다.
        # 타입을 str로 좁히고, 누락 시 명확히 실패시킨다.
        clone_path = state["clone_path"]
        if not clone_path:
            raise RuntimeError("clone_path가 설정되지 않았습니다.")
        report = await asyncio.to_thread(
            scan_repository,
            clone_path,
            state["repo_name"],
        )
        elapsed = time.perf_counter() - _t0
        logger.info("[단계별 소요시간] job=%s | 2.코드 구조 분석=%.3f초", job_id, elapsed)
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
            "timings": {**state.get("timings", {}), "code_map": elapsed},
        }
    except Exception as exc:
        # 실패 시점까지 소요된 시간도 timings에 누적 (리뷰어 제안 1 반영)
        elapsed = time.perf_counter() - _t0
        logger.exception("Repository scan failed for job %s (%.3f초 경과 후 실패)", job_id, elapsed)
        await _update_db(job_id, status=JobStatus.FAILED.value, message=f"코드 분석 실패: {exc}")
        await _publish(job_id, PipelineStage.CODE_MAP, JobStatus.FAILED, 21, f"코드 분석 실패: {exc}")
        return {
            "status": JobStatus.FAILED.value,
            "error": str(exc),
            "timings": {**state.get("timings", {}), "code_map_failed": elapsed},
        }


# ──────────────────────────────────────────────────────────────
# 공통 헬퍼: LLM 기반 문서 생성 (doc_gen / onboarding 공용)
#
# [Sec05 - ChatOpenAI] app/chat/service.py의 LLM 호출 패턴을 그대로 적용한다.
# OPENAI_API_KEY가 없거나 호출이 실패하면 None을 반환하고, 호출측에서
# 기존 휴리스틱 출력으로 폴백한다. (문서 생성 실패가 분석 전체를 중단시키지 않는다.)
# ──────────────────────────────────────────────────────────────
# LLM 호출이 느릴 때 분석 job이 무한정 멈추지 않도록 하는 한도 (초)
_LLM_TIMEOUT_SECONDS = 30
_LLM_MAX_RETRIES = 1


# LLM 출력 스키마 — 모델이 반환한 JSON 구조를 검증/정규화한다.
# 모양이 어긋나면 ValidationError로 떨어뜨려 호출측이 휴리스틱으로 폴백하게 한다.
class _ComponentSummary(BaseModel):
    area: str = ""
    summary: str = ""


class _DocGenOutput(BaseModel):
    architecture_overview: str = ""
    component_summaries: list[_ComponentSummary] = []
    reading_order: list[str] = []


class _OnboardingStep(BaseModel):
    title: str = ""
    detail: str = ""
    files: list[str] = []


class _RiskArea(BaseModel):
    file: str = ""
    reason: str = ""


class _OnboardingOutput(BaseModel):
    onboarding_steps: list[_OnboardingStep] = []
    first_contributions: list[str] = []
    risk_areas: list[_RiskArea] = []


def _read_readme(clone_path: str | None) -> str:
    """저장소 루트의 README를 찾아 최대 3000자까지 발췌한다."""
    if not clone_path:
        return ""
    root = Path(clone_path)
    for name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        candidate = root / name
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8", errors="replace")[:3000]
            except OSError:
                return ""
    return ""


def _repo_context(report: dict, readme: str) -> str:
    """분석 리포트와 README를 LLM 프롬프트용 컨텍스트 문자열로 압축한다."""
    stats = report.get("stats", {})
    languages = ", ".join(
        f"{item['name']}({item['lines']}줄)" for item in report.get("languages", [])[:6]
    )
    parts = [
        f"저장소 이름: {report.get('repository', {}).get('name', '미상')}",
        f"주 언어: {stats.get('primary_language', '미상')}",
        f"기술 스택: {', '.join(report.get('stack', [])) or '미탐지'}",
        f"언어 분포: {languages or '미상'}",
        f"규모: 파일 {stats.get('files', 0)}개 · {stats.get('lines', 0)}줄 · 테스트 {stats.get('tests', 0)}개",
        f"진입점: {', '.join(report.get('entrypoints', [])[:12]) or '미탐지'}",
        f"강점: {', '.join(report.get('key_strengths', [])[:5]) or '없음'}",
        f"위험 신호: {', '.join(report.get('key_risks', [])[:5]) or '없음'}",
    ]
    if readme:
        parts.append(f"\nREADME 발췌:\n{readme}")
    return "\n".join(parts)


async def _llm_json(system: str, user: str) -> dict | None:
    """OPENAI_API_KEY가 있으면 LLM을 호출해 JSON dict를 반환, 실패/미설정 시 None."""
    if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.get_secret_value():
        return None
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
            timeout=_LLM_TIMEOUT_SECONDS,
            max_retries=_LLM_MAX_RETRIES,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        response = await llm.ainvoke([("system", system), ("user", user)])
        content = str(response.content).strip()
        import re
        content = re.sub(r"^```(?:json)?\s*\n?", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\n?```$", "", content)
        result = json.loads(content)
        # 호출측이 dict.get()을 쓰므로 객체가 아니면 폴백 (모델이 배열 등을 반환한 경우 방어)
        return result if isinstance(result, dict) else None
    except Exception as exc:  # LLM 오류는 분석을 중단시키지 않고 휴리스틱으로 폴백
        logger.warning("LLM 문서 생성 실패, 휴리스틱으로 대체합니다: %s", exc)
        return None


# ──────────────────────────────────────────────────────────────
# 노드 3: 문서 자동 생성 (Doc Generation)
#
# [Sec05 - create_react_agent]
# kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
# 코드 분석 결과 + README를 근거로 LLM이 아키텍처 개요/영역별 요약/읽기 순서를 생성한다.
# OPENAI_API_KEY 미설정 또는 LLM 실패 시 진입점 기반 휴리스틱으로 폴백한다.
# ──────────────────────────────────────────────────────────────
async def doc_gen_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    _t0 = time.perf_counter()
    try:
        await _publish(job_id, PipelineStage.DOC_GEN, JobStatus.IN_PROGRESS, 64, "분석 근거와 읽기 순서 구성 중")
        report = dict(state.get("analysis_report") or {})
        entrypoints = list(report.get("entrypoints", []))

        readme = await asyncio.to_thread(_read_readme, state.get("clone_path"))
        generated = await _llm_json(
            "당신은 코드베이스 분석 문서를 작성하는 시니어 엔지니어입니다. "
            "제공된 저장소 분석 데이터와 README 발췌만 근거로 한국어 기술 문서를 작성하세요. "
            "데이터에 없는 내용을 지어내지 말고, 다음 키를 가진 JSON만 반환하세요: "
            "architecture_overview(문자열, 3~5문장), "
            "component_summaries(객체 배열, 각 {area, summary}, 3~6개), "
            "reading_order(파일 경로 문자열 배열, 처음 읽을 순서대로 최대 8개).",
            _repo_context(report, readme),
        )
        doc = None
        if generated:
            try:
                doc = _DocGenOutput.model_validate(generated)
            except ValidationError as exc:
                logger.warning("doc_gen LLM 출력 스키마 불일치, 휴리스틱으로 대체: %s", exc)
        if doc:
            report["architecture_overview"] = doc.architecture_overview
            report["component_summaries"] = [c.model_dump() for c in doc.component_summaries]
            report["reading_order"] = doc.reading_order or entrypoints[:8]
            report["doc_generated_by"] = settings.OPENAI_MODEL
            message = "AI 기반 분석 문서 생성 완료"
        else:
            report["reading_order"] = entrypoints[:8]
            report["doc_generated_by"] = "heuristic"
            message = "근거 기반 분석 문서 구성 완료(휴리스틱)"

        elapsed = time.perf_counter() - _t0
        logger.info("[단계별 소요시간] job=%s | 3.문서 자동생성(LLM)=%.3f초", job_id, elapsed)
        await _update_db(
            job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.DOC_GEN.value,
            progress=72,
            message=message,
            report_json=report,
        )
        return {
            "analysis_report": report,
            "current_stage": PipelineStage.DOC_GEN.value,
            "progress": 72,
            "status": JobStatus.IN_PROGRESS.value,
            "error": None,
            "timings": {**state.get("timings", {}), "doc_gen": elapsed},
        }
    except Exception as exc:
        elapsed = time.perf_counter() - _t0
        logger.exception("doc_gen failed for job %s (%.3f초 경과 후 실패)", job_id, elapsed)
        # clone_node / code_map_node 패턴과 동일하게 FAILED 상태를 DB·SSE에 즉시 기록한다.
        # 예외를 삼켜 그래프가 정상 반환되더라도 클라이언트가 종료 이벤트를 받을 수 있게 한다.
        await _update_db(
            job_id,
            status=JobStatus.FAILED.value,
            stage=PipelineStage.DOC_GEN.value,
            progress=state.get("progress", 64),
            message=f"문서 생성 실패: {exc}",
        )
        await _publish(job_id, PipelineStage.DOC_GEN, JobStatus.FAILED, state.get("progress", 64), f"문서 생성 실패: {exc}")
        return {
            "current_stage": PipelineStage.DOC_GEN.value,
            "progress": state.get("progress", 64),
            "status": JobStatus.FAILED.value,
            "error": str(exc),
            "timings": {**state.get("timings", {}), "doc_gen_failed": elapsed},
        }


# ──────────────────────────────────────────────────────────────
# 노드 4: 온보딩 가이드 생성 (Onboarding)
#
# [Sec05 - create_react_agent]
# kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
# LLM이 신입 개발자용 온보딩 단계/첫 기여 제안/주의 파일을 근거 기반으로 생성한다.
# OPENAI_API_KEY 미설정 또는 LLM 실패 시 진입점 기반 휴리스틱으로 폴백한다.
# ──────────────────────────────────────────────────────────────
async def onboarding_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    _t0 = time.perf_counter()
    try:
        await _publish(job_id, PipelineStage.ONBOARDING, JobStatus.IN_PROGRESS, 80, "온보딩 경로 생성 중")
        report = dict(state.get("analysis_report") or {})
        entrypoints = list(report.get("entrypoints", []))

        readme = await asyncio.to_thread(_read_readme, state.get("clone_path"))
        generated = await _llm_json(
            "당신은 신입 개발자 온보딩 가이드를 만드는 시니어 엔지니어입니다. "
            "제공된 저장소 분석 데이터와 README 발췌만 근거로, 처음 합류한 개발자가 따라갈 수 있는 "
            "실질적인 온보딩 가이드를 한국어로 작성하세요. 데이터에 없는 파일을 지어내지 마세요. "
            "다음 키를 가진 JSON만 반환하세요: "
            "onboarding_steps(객체 배열, 각 {title, detail, files:[경로]}, 3~5개), "
            "first_contributions(문자열 배열, 처음 기여로 적합한 작업 2~4개), "
            "risk_areas(객체 배열, 각 {file, reason}, 최대 4개).",
            _repo_context(report, readme),
        )
        guide = None
        if generated:
            try:
                guide = _OnboardingOutput.model_validate(generated)
            except ValidationError as exc:
                logger.warning("onboarding LLM 출력 스키마 불일치, 휴리스틱으로 대체: %s", exc)
        if guide and guide.onboarding_steps:
            report["onboarding_steps"] = [s.model_dump() for s in guide.onboarding_steps]
            report["first_contributions"] = guide.first_contributions
            report["risk_areas"] = [r.model_dump() for r in guide.risk_areas]
            report["onboarding_generated_by"] = settings.OPENAI_MODEL
            message = "AI 기반 온보딩 가이드 생성 완료"
        else:
            report["onboarding_steps"] = [
                {"title": "실행 경계 확인", "files": entrypoints[:3]},
                {"title": "핵심 기능 흐름 추적", "files": entrypoints[3:6]},
                {"title": "테스트와 배포 구성 검증", "files": entrypoints[6:9]},
            ]
            report["onboarding_generated_by"] = "heuristic"
            report.setdefault("first_contributions", [])
            report.setdefault("risk_areas", [])
            message = "온보딩 경로 생성 완료(휴리스틱)"

        elapsed = time.perf_counter() - _t0
        logger.info("[단계별 소요시간] job=%s | 4.온보딩 가이드 생성(LLM)=%.3f초", job_id, elapsed)
        await _update_db(
            job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.ONBOARDING.value,
            progress=90,
            message=message,
            report_json=report,
        )
        return {
            "analysis_report": report,
            "current_stage": PipelineStage.ONBOARDING.value,
            "progress": 90,
            "status": JobStatus.IN_PROGRESS.value,
            "error": None,
            "timings": {**state.get("timings", {}), "onboarding": elapsed},
        }
    except Exception as exc:
        elapsed = time.perf_counter() - _t0
        logger.exception("onboarding failed for job %s (%.3f초 경과 후 실패)", job_id, elapsed)
        # clone_node / code_map_node 패턴과 동일하게 FAILED 상태를 DB·SSE에 즉시 기록한다.
        await _update_db(
            job_id,
            status=JobStatus.FAILED.value,
            stage=PipelineStage.ONBOARDING.value,
            progress=state.get("progress", 80),
            message=f"온보딩 가이드 생성 실패: {exc}",
        )
        await _publish(job_id, PipelineStage.ONBOARDING, JobStatus.FAILED, state.get("progress", 80), f"온보딩 가이드 생성 실패: {exc}")
        return {
            "current_stage": PipelineStage.ONBOARDING.value,
            "progress": state.get("progress", 80),
            "status": JobStatus.FAILED.value,
            "error": str(exc),
            "timings": {**state.get("timings", {}), "onboarding_failed": elapsed},
        }


# ──────────────────────────────────────────────────────────────
# 노드 5: 최종 결과 저장 (Report)
#
# [Sec09 - gather_node]
# kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/nodes/gather_node.py
# 모든 이전 노드의 Agent 결과를 취합하여 최종 리포트를 DB에 저장한다.
# ──────────────────────────────────────────────────────────────
async def report_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    _t0 = time.perf_counter()
    report = dict(state.get("analysis_report") or {})
    report["job_id"] = job_id
    report["status"] = "completed"
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    report["model_used"] = state.get("model") or "auto"

    elapsed = time.perf_counter() - _t0
    timings = {**state.get("timings", {}), "report": elapsed}

    # ── 파이프라인 전체 타이밍 요약 로그 ──
    # 어느 단계가 느린지 한눈에 파악하기 위해 분석 완료 시점에 출력한다.
    # 예시 출력:
    #   [TIMING SUMMARY] job=abc... clone=3.21s code_map=1.05s doc_gen=18.50s
    #                    onboarding=25.00s report=0.01s total=47.77s
    total = sum(timings.values())
    summary = " | ".join(f"{k}={v:.3f}초" for k, v in timings.items())
    logger.info("[파이프라인 전체 소요시간 요약] job=%s → %s | 합계=%.3f초", job_id, summary, total)

    report["pipeline_timings"] = {k: round(v, 3) for k, v in timings.items()}
    report["pipeline_timings"]["total"] = round(total, 3)

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
        "timings": timings,
    }
