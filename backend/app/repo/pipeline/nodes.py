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

import asyncio
import logging
import os
from datetime import datetime, timezone
from uuid import UUID

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.repo.event_manager import event_manager
from app.repo.repository import AnalysisJobRepository
from app.repo.schemas import JobStatus, PipelineStage, ProgressEvent
from app.repo.pipeline.state import PipelineState

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
    """SSE/WebSocket 구독자에게 진행 이벤트를 발행한다."""
    event = ProgressEvent(
        stage=stage,
        status=status,
        progress=progress,
        message=message,
        timestamp=datetime.now(timezone.utc),
    )
    await event_manager.publish(job_id, event)


# ──────────────────────────────────────────────────────────────
# 공통 헬퍼: DB 분석 작업 상태 업데이트
# ──────────────────────────────────────────────────────────────

async def _update_db(job_id: str, **kwargs) -> None:
    """
    분석 작업 상태를 DB에 업데이트한다.

    백그라운드 Task이므로 별도 세션을 직접 생성한다.
    clone_path는 DB에 저장하지 않으므로 kwargs에 포함하지 않는다.
    """
    async with async_session_factory() as session:
        repo = AnalysisJobRepository(session)
        await repo.update_job_status(job_id=UUID(job_id), **kwargs)
        await session.commit()


# ──────────────────────────────────────────────────────────────
# [Sec05 - create_react_agent] LangChain ReAct Agent 생성 헬퍼
# kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
# ──────────────────────────────────────────────────────────────

def _build_agent(system_prompt: str, tools: list | None = None):
    """
    LangChain ReAct Agent를 생성한다.

    # [Sec05 - create_react_agent]
    # kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
    # OPENAI_API_KEY 미설정 시 None을 반환하며,
    # 각 노드에서 시뮬레이션 모드로 폴백한다.
    """
    if not settings.OPENAI_API_KEY:
        return None

    # [Sec05 - ChatOpenAI] 모델 초기화
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )

    # [Sec05 - create_react_agent] Agent 생성
    # [Sec08 - RAG Agent] tools에 pgvector 검색 Tool을 연결할 예정
    # TODO: 각 도메인 서비스(RAG-PARSE, DOCS-GEN) 구현 완료 후 tools 주입
    return create_react_agent(
        llm,
        tools=tools or [],
        state_modifier=system_prompt,
    )


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
    """
    Git Clone 노드

    # [Sec09 - 노드 패턴]
    # kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/nodes/ 참고
    # PipelineState → 처리 → dict 반환으로 상태를 갱신하는 노드 함수 구조 적용

    clone_path는 job_id + CLONE_BASE_DIR로 항상 결정된다.
    DB에 저장하지 않고 os.path.exists()로 이미 Clone된 경우를 감지하여 건너뛴다.
    """
    job_id = state["job_id"]
    logger.info(f"[clone_node] 시작 (job_id={job_id})")

    # clone_path는 항상 이 위치로 결정된다 (DB 저장 불필요)
    clone_path = os.path.join(settings.CLONE_BASE_DIR, job_id, "repo")

    # 이미 Clone된 경우 (수동 재시작 등): 디렉토리가 존재하면 건너뜀
    if os.path.exists(clone_path):
        logger.info(
            f"[clone_node] Clone 디렉토리 존재 — Clone 단계 건너뜀 "
            f"(path={clone_path})"
        )
        return {
            "clone_path": clone_path,
            "current_stage": PipelineStage.CLONE.value,
            "progress": 20,
            "status": JobStatus.IN_PROGRESS.value,
            "error": None,
        }

    await _publish(
        job_id, PipelineStage.CLONE, JobStatus.IN_PROGRESS, 5, "저장소 복제 준비 중..."
    )

    try:
        os.makedirs(clone_path, exist_ok=True)

        await _publish(
            job_id, PipelineStage.CLONE, JobStatus.IN_PROGRESS, 10, "저장소 복제 중..."
        )

        # TODO: 아래 subprocess 코드로 교체 (실제 git clone)
        # process = await asyncio.create_subprocess_exec(
        #     "git", "clone",
        #     "--branch", state["branch"],
        #     "--depth", "1",
        #     state["repo_url"], clone_path,
        #     stdout=asyncio.subprocess.PIPE,
        #     stderr=asyncio.subprocess.PIPE,
        # )
        # stdout, stderr = await process.communicate()
        # if process.returncode != 0:
        #     raise RuntimeError(stderr.decode())
        await asyncio.sleep(2)  # 시뮬레이션

        await _publish(
            job_id, PipelineStage.CLONE, JobStatus.IN_PROGRESS, 20, "저장소 복제 완료"
        )
        await _update_db(
            job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.CLONE.value,
            progress=20,
            message="저장소 복제 완료",
        )

        return {
            "clone_path": clone_path,
            "current_stage": PipelineStage.CLONE.value,
            "progress": 20,
            "status": JobStatus.IN_PROGRESS.value,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"[clone_node] 오류 (job_id={job_id}): {exc}")
        await _publish(
            job_id, PipelineStage.CLONE, JobStatus.FAILED, 0, f"Clone 실패: {exc}"
        )
        await _update_db(
            job_id,
            status=JobStatus.FAILED.value,
            message=f"Clone 실패: {exc}",
        )
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
    """
    코드 구조 분석 노드

    # [Sec05 - create_react_agent]
    # kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
    # Agent가 저장소의 파일 트리, 기술 스택, 엔트리포인트를 분석한다.

    # [Sec08 - RAG Agent]
    # kosa-langchain-practice/langchain/api/sec08_rag/agent_rag.py 참고
    # RAG-PARSE 도메인 구현 완료 후 pgvector Tool을 Agent에 연결할 예정
    """
    job_id = state["job_id"]
    logger.info(f"[code_map_node] 시작 (job_id={job_id})")

    await _publish(
        job_id, PipelineStage.CODE_MAP, JobStatus.IN_PROGRESS, 21, "코드 구조 분석 중..."
    )

    try:
        # [Sec05 - create_react_agent] 코드 분석 Agent 생성
        # [Sec08 - RAG Agent] 향후 pgvector 검색 Tool 주입 예정
        # TODO: RAG-PARSE-B-210 구현 완료 후 실제 파일 분석 Tool 연동
        agent = _build_agent(
            system_prompt=(
                "당신은 코드 구조 분석 전문가입니다. "
                "저장소의 파일 트리, 기술 스택, 엔트리포인트, 의존성을 분석합니다."
            ),
        )

        if agent:
            # [Sec05 - ainvoke()] Agent 실행
            # [Sec09 - messages] 이전 노드 메시지 컨텍스트 포함
            result = await agent.ainvoke({
                "messages": state.get("messages", []) + [{
                    "role": "user",
                    "content": (
                        f"저장소 '{state['repo_name']}' ({state['repo_url']})의 "
                        f"코드 구조를 분석해주세요. "
                        f"clone 경로: {state.get('clone_path')}"
                    ),
                }],
            })
            new_messages = result.get("messages", [])
        else:
            # OPENAI_API_KEY 미설정 시 시뮬레이션 모드
            logger.warning(
                "[code_map_node] OPENAI_API_KEY 미설정 — 시뮬레이션 모드 실행"
            )
            await asyncio.sleep(2)
            new_messages = []

        await _publish(
            job_id, PipelineStage.CODE_MAP, JobStatus.IN_PROGRESS, 50, "코드 구조 분석 완료"
        )
        await _update_db(
            job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.CODE_MAP.value,
            progress=50,
            message="코드 구조 분석 완료",
        )

        return {
            "current_stage": PipelineStage.CODE_MAP.value,
            "progress": 50,
            "messages": new_messages,
        }

    except Exception as exc:
        logger.error(f"[code_map_node] 오류 (job_id={job_id}): {exc}")
        await _publish(
            job_id, PipelineStage.CODE_MAP, JobStatus.FAILED, 21, f"코드 분석 실패: {exc}"
        )
        await _update_db(
            job_id, status=JobStatus.FAILED.value, message=f"코드 분석 실패: {exc}"
        )
        return {"status": JobStatus.FAILED.value, "error": str(exc)}


# ──────────────────────────────────────────────────────────────
# 노드 3: 문서 자동 생성 (Doc Generation)
#
# [Sec05 - create_react_agent]
# kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
# 코드 분석 결과를 바탕으로 파일/폴더 단위 요약 문서를 생성한다.
# ──────────────────────────────────────────────────────────────

async def doc_gen_node(state: PipelineState) -> dict:
    """
    문서 자동 생성 노드

    # [Sec05 - create_react_agent]
    # kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
    # [Sec09 - messages 누적] 이전 노드(code_map)의 분석 결과를 컨텍스트로 활용한다.
    # TODO: DOCS-GEN-B-201 구현 완료 후 실제 문서 생성 Tool 연동
    """
    job_id = state["job_id"]
    logger.info(f"[doc_gen_node] 시작 (job_id={job_id})")

    await _publish(
        job_id, PipelineStage.DOC_GEN, JobStatus.IN_PROGRESS, 51, "문서 자동 생성 중..."
    )

    try:
        # [Sec05 - create_react_agent] 문서 생성 Agent
        # TODO: DOCS-GEN-B-201 구현 완료 후 실제 문서 생성 Tool 연동
        agent = _build_agent(
            system_prompt=(
                "당신은 기술 문서 작성 전문가입니다. "
                "코드 분석 결과를 기반으로 파일 단위 및 폴더 단위 요약 문서를 작성합니다."
            ),
        )

        if agent:
            # [Sec09 - messages 누적] code_map_node의 분석 컨텍스트를 이어받아 실행
            result = await agent.ainvoke({
                "messages": state.get("messages", []) + [{
                    "role": "user",
                    "content": (
                        f"'{state['repo_name']}' 저장소에 대한 "
                        "파일 단위 및 폴더 단위 기술 문서를 작성해주세요."
                    ),
                }],
            })
            new_messages = result.get("messages", [])
        else:
            logger.warning(
                "[doc_gen_node] OPENAI_API_KEY 미설정 — 시뮬레이션 모드 실행"
            )
            await asyncio.sleep(2)
            new_messages = []

        await _publish(
            job_id, PipelineStage.DOC_GEN, JobStatus.IN_PROGRESS, 70, "문서 자동 생성 완료"
        )
        await _update_db(
            job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.DOC_GEN.value,
            progress=70,
            message="문서 자동 생성 완료",
        )

        return {
            "current_stage": PipelineStage.DOC_GEN.value,
            "progress": 70,
            "messages": new_messages,
        }

    except Exception as exc:
        logger.error(f"[doc_gen_node] 오류 (job_id={job_id}): {exc}")
        await _publish(
            job_id, PipelineStage.DOC_GEN, JobStatus.FAILED, 51, f"문서 생성 실패: {exc}"
        )
        await _update_db(
            job_id, status=JobStatus.FAILED.value, message=f"문서 생성 실패: {exc}"
        )
        return {"status": JobStatus.FAILED.value, "error": str(exc)}


# ──────────────────────────────────────────────────────────────
# 노드 4: 온보딩 가이드 생성 (Onboarding)
#
# [Sec05 - create_react_agent]
# kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
# 신입 개발자를 위한 추천 읽기 순서, 수정 시작점, 위험 파일 목록을 생성한다.
# ──────────────────────────────────────────────────────────────

async def onboarding_node(state: PipelineState) -> dict:
    """
    온보딩 가이드 생성 노드

    # [Sec05 - create_react_agent]
    # kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
    # [Sec09 - messages 누적] 이전 노드들의 분석/문서 컨텍스트를 모두 활용한다.
    # TODO: DOCS-GEN-B-202 온보딩 가이드 Agent 구현 완료 후 교체
    """
    job_id = state["job_id"]
    logger.info(f"[onboarding_node] 시작 (job_id={job_id})")

    await _publish(
        job_id,
        PipelineStage.ONBOARDING,
        JobStatus.IN_PROGRESS,
        71,
        "온보딩 가이드 생성 중...",
    )

    try:
        # [Sec05 - create_react_agent] 온보딩 가이드 생성 Agent
        # TODO: DOCS-GEN-B-202 구현 완료 후 실제 온보딩 가이드 Tool 연동
        agent = _build_agent(
            system_prompt=(
                "당신은 온보딩 가이드 전문가입니다. "
                "신입 개발자가 빠르게 프로젝트에 적응할 수 있도록 "
                "추천 읽기 순서, 수정 시작점, 위험 파일 목록을 작성합니다."
            ),
        )

        if agent:
            # [Sec09 - messages 누적] code_map + doc_gen 컨텍스트를 모두 이어받아 실행
            result = await agent.ainvoke({
                "messages": state.get("messages", []) + [{
                    "role": "user",
                    "content": (
                        f"'{state['repo_name']}' 저장소의 "
                        "신입 개발자 온보딩 가이드를 작성해주세요."
                    ),
                }],
            })
            new_messages = result.get("messages", [])
        else:
            logger.warning(
                "[onboarding_node] OPENAI_API_KEY 미설정 — 시뮬레이션 모드 실행"
            )
            await asyncio.sleep(2)
            new_messages = []

        await _publish(
            job_id,
            PipelineStage.ONBOARDING,
            JobStatus.IN_PROGRESS,
            90,
            "온보딩 가이드 생성 완료",
        )
        await _update_db(
            job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.ONBOARDING.value,
            progress=90,
            message="온보딩 가이드 생성 완료",
        )

        return {
            "current_stage": PipelineStage.ONBOARDING.value,
            "progress": 90,
            "messages": new_messages,
        }

    except Exception as exc:
        logger.error(f"[onboarding_node] 오류 (job_id={job_id}): {exc}")
        await _publish(
            job_id,
            PipelineStage.ONBOARDING,
            JobStatus.FAILED,
            71,
            f"온보딩 생성 실패: {exc}",
        )
        await _update_db(
            job_id, status=JobStatus.FAILED.value, message=f"온보딩 생성 실패: {exc}"
        )
        return {"status": JobStatus.FAILED.value, "error": str(exc)}


# ──────────────────────────────────────────────────────────────
# 노드 5: 최종 결과 저장 (Report)
#
# [Sec09 - gather_node]
# kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/nodes/gather_node.py
# 모든 이전 노드의 Agent 결과를 취합하여 최종 리포트를 DB에 저장한다.
# ──────────────────────────────────────────────────────────────

async def report_node(state: PipelineState) -> dict:
    """
    최종 결과 저장 노드

    # [Sec09 - gather_node]
    # kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/nodes/gather_node.py 참고
    # 모든 Agent 결과를 취합하여 최종 프로젝트 마스터 리포트를 DB에 저장한다.
    # TODO: DOCS-GEN-B-204 프로젝트 마스터 리포트 생성 로직 연동
    """
    job_id = state["job_id"]
    logger.info(f"[report_node] 시작 (job_id={job_id})")

    await _publish(
        job_id, PipelineStage.REPORT, JobStatus.IN_PROGRESS, 91, "최종 결과 저장 중..."
    )

    try:
        # TODO: DOCS-GEN-B-204 구현 완료 후 마스터 리포트 생성 및 저장 로직 연동
        await asyncio.sleep(1)  # 시뮬레이션

        await _publish(
            job_id, PipelineStage.REPORT, JobStatus.COMPLETED, 100, "분석 완료!"
        )
        await _update_db(
            job_id,
            status=JobStatus.COMPLETED.value,
            stage=PipelineStage.REPORT.value,
            progress=100,
            message="분석 완료!",
        )

        return {
            "current_stage": PipelineStage.REPORT.value,
            "progress": 100,
            "status": JobStatus.COMPLETED.value,
            "error": None,
        }

    except Exception as exc:
        logger.error(f"[report_node] 오류 (job_id={job_id}): {exc}")
        await _publish(
            job_id, PipelineStage.REPORT, JobStatus.FAILED, 91, f"결과 저장 실패: {exc}"
        )
        await _update_db(
            job_id, status=JobStatus.FAILED.value, message=f"결과 저장 실패: {exc}"
        )
        return {"status": JobStatus.FAILED.value, "error": str(exc)}
