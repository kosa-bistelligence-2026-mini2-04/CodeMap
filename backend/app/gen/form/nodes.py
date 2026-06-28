"""
문서 생성 파이프라인 LangGraph 노드 구현

DOCS-GEN 내부 파이프라인(순서 1~6)의 각 노드 함수를 정의한다.
실행 순서: B-205 → B-201 → B-203 → B-206 → B-202 → B-204

각 노드는 GenFormState를 입력받아 갱신할 dict를 반환한다.
OPENAI_API_KEY 미설정 또는 LLM 호출 실패 시 휴리스틱 폴백으로 처리한다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.infra.config import get_settings
from app.gen.form.state import GenFormState

logger = logging.getLogger(__name__)
settings = get_settings()

## LLM 호출 한도
_LLM_TIMEOUT_SECONDS = 30
_LLM_MAX_RETRIES = 1


# ──────────────────────────────────────────────
# 공통 헬퍼: README 파일 읽기
# ──────────────────────────────────────────────
def _read_readme(clone_path: str | None) -> str:
    '''저장소 루트의 README를 찾아 최대 4000자까지 발췌한다.'''
    if not clone_path:
        return ""
    root = Path(clone_path)
    for name in (
        "README.md", "readme.md", "README.rst", "README.txt", "README"
    ):
        candidate = root / name
        if candidate.is_file():
            try:
                return candidate.read_text(
                    encoding="utf-8", errors="replace"
                )[:4000]
            except OSError:
                return ""
    return ""


# ──────────────────────────────────────────────
# 공통 헬퍼: 설정/라우터 파일 수집
# ──────────────────────────────────────────────
def _collect_config_files(clone_path: str | None) -> str:
    '''
    package.json, requirements.txt, pyproject.toml 등 설정 파일과
    라우터 파일의 일부를 수집하여 컨텍스트 문자열로 반환한다.
    '''
    if not clone_path:
        return ""
    root = Path(clone_path)
    target_names = {
        "package.json", "requirements.txt", "pyproject.toml",
        "setup.py", "Cargo.toml", "go.mod", "pom.xml",
    }
    collected: list[str] = []
    for name in target_names:
        candidate = root / name
        if candidate.is_file():
            try:
                content = candidate.read_text(
                    encoding="utf-8", errors="replace"
                )[:1000]
                collected.append(f"## {name}\n{content}")
            except OSError:
                continue
    return "\n\n".join(collected)[:3000]


# ──────────────────────────────────────────────
# 공통 헬퍼: 분석 리포트 컨텍스트 압축
# ──────────────────────────────────────────────
def _repo_context(
    report: dict[str, Any], readme: str, extra: str = ""
) -> str:
    '''분석 리포트와 README를 LLM 프롬프트용 컨텍스트 문자열로 압축한다.'''
    stats = report.get("stats", {})
    languages = ", ".join(
        f"{item['name']}({item['lines']}줄)"
        for item in report.get("languages", [])[:6]
    )
    parts = [
        f"저장소 이름: {report.get('repository', {}).get('name', '미상')}",
        f"주 언어: {stats.get('primary_language', '미상')}",
        f"기술 스택: {', '.join(report.get('stack', [])) or '미탐지'}",
        f"언어 분포: {languages or '미상'}",
        (
            f"규모: 파일 {stats.get('files', 0)}개"
            f" · {stats.get('lines', 0)}줄"
            f" · 테스트 {stats.get('tests', 0)}개"
        ),
        f"진입점: {', '.join(report.get('entrypoints', [])[:12]) or '미탐지'}",
    ]
    if readme:
        parts.append(f"\nREADME 발췌:\n{readme}")
    if extra:
        parts.append(f"\n추가 컨텍스트:\n{extra}")
    return "\n".join(parts)


# ──────────────────────────────────────────────
# 공통 헬퍼: LLM JSON 호출
# ──────────────────────────────────────────────
async def _llm_json(
    system: str, user: str, model: str | None = None
) -> dict | None:
    '''OPENAI_API_KEY가 있으면 LLM을 호출해 JSON dict를 반환, 실패/미설정 시 None.'''
    if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.get_secret_value():
        return None
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=model or settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
            timeout=_LLM_TIMEOUT_SECONDS,
            max_retries=_LLM_MAX_RETRIES,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        response = await llm.ainvoke([("system", system), ("user", user)])
        content = str(response.content).strip()
        content = re.sub(r"^```(?:json)?\s*\n?", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\n?```$", "", content)
        result = json.loads(content)
        return result if isinstance(result, dict) else None
    except Exception as exc:
        logger.warning(
            "LLM 문서 생성 호출 실패, 휴리스틱으로 대체합니다: %s", exc
        )
        return None


# ──────────────────────────────────────────────────────────────
# Pydantic 출력 스키마 정의
# ──────────────────────────────────────────────────────────────
class _ProjectIntroOutput(BaseModel):
    title: str = ""
    description: str = ""
    purpose: str = ""
    key_features: list[str] = []


class _DocSummaryOutput(BaseModel):
    purpose: str = ""
    key_features: list[str] = []
    tech_context: str = ""
    architecture_hint: str = ""


class _FolderSummaryOutput(BaseModel):
    folders: list[dict[str, str]] = []


class _FlowExplainOutput(BaseModel):
    flow_overview: str = ""
    entry_to_db: list[str] = []
    key_call_chain: str = ""


class _OnboardingGuideOutput(BaseModel):
    reading_order: list[str] = []
    risk_files: list[dict[str, str]] = []
    first_tasks: list[str] = []


# ──────────────────────────────────────────────────────────────
# 노드 1: README 기반 프로젝트 소개 생성 (DOCS-GEN-B-205)
#
# README를 파싱하여 구조화된 프로젝트 소개 섹션 생성.
# 폴백: README 원문 요약 또는 리포트 메타데이터 기반 기본 소개.
# ──────────────────────────────────────────────────────────────
async def readme_intro_node(state: GenFormState) -> dict:
    '''
    DOCS-GEN-B-205 구현 노드

    README를 파싱해 프로젝트 소개(title, description, purpose, key_features)를 생성한다.
    '''
    _t0 = time.perf_counter()
    repo_id = state["repo_id"]
    try:
        readme = await asyncio.to_thread(
            _read_readme, state.get("clone_path")
        )
        report = dict(state.get("analysis_report") or {})
        context = _repo_context(report, readme)

        generated = await _llm_json(
            "당신은 오픈소스 프로젝트 소개 문서를 작성하는 시니어 엔지니어입니다. "
            "제공된 저장소 분석 데이터와 README 발췌만 근거로 한국어로 작성하세요. "
            "데이터에 없는 내용을 지어내지 말고, 다음 키를 가진 JSON만 반환하세요: "
            "title(프로젝트 제목, 문자열), "
            "description(한 줄 설명, 문자열), "
            "purpose(존재 이유 및 해결 문제, 2~3문장 문자열), "
            "key_features(핵심 기능 목록, 문자열 배열 3~5개).",
            context,
            state.get("llm_model"),
        )

        intro_obj: _ProjectIntroOutput | None = None
        if generated:
            try:
                intro_obj = _ProjectIntroOutput.model_validate(generated)
            except ValidationError as exc:
                logger.warning(
                    "readme_intro LLM 출력 스키마 불일치, 휴리스틱 대체: %s", exc
                )

        if intro_obj:
            project_intro = (
                f"# {intro_obj.title}\n\n"
                f"{intro_obj.description}\n\n"
                f"## 목적\n{intro_obj.purpose}\n\n"
                f"## 핵심 기능\n"
                + "\n".join(f"- {f}" for f in intro_obj.key_features)
            )
        else:
            repo_name = report.get("repository", {}).get("name", repo_id)
            stack = ", ".join(report.get("stack", [])[:5]) or "미탐지"
            project_intro = (
                f"# {repo_name}\n\n"
                f"기술 스택: {stack}\n\n"
                + (readme[:500] if readme else "README 없음")
            )

        elapsed = time.perf_counter() - _t0
        logger.info(
            "[DOCS-GEN-B-205] repo=%s | README 기반 프로젝트 소개 생성 완료"
            " (%.3f초)", repo_id, elapsed,
        )
        return {
            "project_intro": project_intro,
            "timings": {**state.get("timings", {}), "b205_readme_intro": elapsed},
        }
    except Exception as exc:
        elapsed = time.perf_counter() - _t0
        logger.exception(
            "[DOCS-GEN-B-205] repo=%s | README 소개 생성 실패 (%.3f초): %s",
            repo_id, elapsed, exc,
        )
        return {
            "status": "failed",
            "error": f"B-205 실패: {exc}",
            "timings": {**state.get("timings", {}), "b205_failed": elapsed},
        }


# ──────────────────────────────────────────────────────────────
# 노드 2: 문서 요약 agent 구현 (DOCS-GEN-B-201)
#
# README, config, route 파일 기반 프로젝트 설명 생성.
# GPT-4o-mini 사용 (비용 최적화).
# ──────────────────────────────────────────────────────────────
async def doc_summary_node(state: GenFormState) -> dict:
    '''
    DOCS-GEN-B-201 구현 노드

    README, package.json/requirements.txt, 라우터 파일을 기반으로
    프로젝트 목적·핵심 기능·기술 컨텍스트를 요약한다.
    '''
    _t0 = time.perf_counter()
    repo_id = state["repo_id"]
    try:
        readme = await asyncio.to_thread(
            _read_readme, state.get("clone_path")
        )
        config_context = await asyncio.to_thread(
            _collect_config_files, state.get("clone_path")
        )
        report = dict(state.get("analysis_report") or {})
        project_intro = state.get("project_intro") or ""
        context = _repo_context(report, readme, extra=config_context)

        generated = await _llm_json(
            "당신은 코드베이스 기술 문서를 작성하는 시니어 엔지니어입니다. "
            "제공된 저장소 분석 데이터, README 발췌, 설정 파일 내용만 근거로 "
            "한국어 기술 문서를 작성하세요. "
            "다음 키를 가진 JSON만 반환하세요: "
            "purpose(프로젝트 목적, 2~3문장 문자열), "
            "key_features(핵심 기능, 문자열 배열 3~6개), "
            "tech_context(기술 스택과 아키텍처 배경, 2~3문장 문자열), "
            "architecture_hint(폴더 구조나 레이어 힌트, 1~2문장 문자열).",
            context,
            state.get("llm_model"),
        )

        doc: _DocSummaryOutput | None = None
        if generated:
            try:
                doc = _DocSummaryOutput.model_validate(generated)
            except ValidationError as exc:
                logger.warning(
                    "doc_summary LLM 출력 스키마 불일치, 휴리스틱 대체: %s", exc
                )

        if doc:
            doc_summary: dict[str, Any] = {
                "purpose": doc.purpose,
                "key_features": doc.key_features,
                "tech_context": doc.tech_context,
                "architecture_hint": doc.architecture_hint,
                "generated_by": settings.OPENAI_MODEL,
            }
        else:
            stack = report.get("stack", [])
            doc_summary = {
                "purpose": project_intro[:300] if project_intro else "목적 미탐지",
                "key_features": report.get("key_strengths", [])[:5],
                "tech_context": f"기술 스택: {', '.join(stack[:8]) or '미탐지'}",
                "architecture_hint": "",
                "generated_by": "heuristic",
            }

        elapsed = time.perf_counter() - _t0
        logger.info(
            "[DOCS-GEN-B-201] repo=%s | 문서 요약 agent 완료 (%.3f초)",
            repo_id, elapsed,
        )
        return {
            "doc_summary": doc_summary,
            "timings": {**state.get("timings", {}), "b201_doc_summary": elapsed},
        }
    except Exception as exc:
        elapsed = time.perf_counter() - _t0
        logger.exception(
            "[DOCS-GEN-B-201] repo=%s | 문서 요약 실패 (%.3f초): %s",
            repo_id, elapsed, exc,
        )
        return {
            "status": "failed",
            "error": f"B-201 실패: {exc}",
            "timings": {**state.get("timings", {}), "b201_failed": elapsed},
        }


# ──────────────────────────────────────────────────────────────
# 노드 3: 폴더 단위 요약 (DOCS-GEN-B-203)
#
# Bottom-up 방식으로 파일 요약 → 폴더 요약 → 마스터 요약 상향식 통합.
# Tree-Based RAG 방식, 각 폴더별 책임 영역 설명 자동 생성.
# ──────────────────────────────────────────────────────────────
async def folder_summary_node(state: GenFormState) -> dict:
    '''
    DOCS-GEN-B-203 구현 노드

    분석 리포트의 파일 트리를 기반으로 폴더별 책임 영역 요약을 생성한다.
    Bottom-up 방식으로 최대 8개 주요 폴더를 요약한다.
    '''
    _t0 = time.perf_counter()
    repo_id = state["repo_id"]
    try:
        report = dict(state.get("analysis_report") or {})
        readme = await asyncio.to_thread(
            _read_readme, state.get("clone_path")
        )

        ## 폴더 목록 추출 (분석 리포트의 file_tree 또는 entrypoints에서 유추)
        entrypoints = report.get("entrypoints", [])
        folder_set: set[str] = set()
        for ep in entrypoints:
            parts = ep.replace("\\", "/").split("/")
            if len(parts) > 1:
                folder_set.add(parts[0])
        folders = sorted(folder_set)[:10]

        context = _repo_context(report, readme)
        folder_list_str = "\n".join(f"- {f}" for f in folders) or "폴더 정보 없음"

        generated = await _llm_json(
            "당신은 코드베이스 아키텍처 문서를 작성하는 시니어 엔지니어입니다. "
            "제공된 저장소 분석 데이터를 근거로 각 주요 폴더의 책임 영역을 "
            "한국어로 설명하세요. "
            "다음 키를 가진 JSON만 반환하세요: "
            "folders(객체 배열, 각 {name: 폴더명, summary: 1~2문장 책임 설명}).",
            f"{context}\n\n주요 폴더 목록:\n{folder_list_str}",
            state.get("llm_model"),
        )

        folder_summaries: dict[str, str] = {}
        if generated:
            try:
                validated = _FolderSummaryOutput.model_validate(generated)
                for item in validated.folders:
                    name = item.get("name", "")
                    summary = item.get("summary", "")
                    if name and summary:
                        folder_summaries[name] = summary
            except ValidationError as exc:
                logger.warning(
                    "folder_summary LLM 출력 스키마 불일치, 휴리스틱 대체: %s", exc
                )

        ## 폴백: 폴더명만 기록
        if not folder_summaries:
            folder_summaries = {f: f"{f}/ 디렉토리" for f in folders}

        elapsed = time.perf_counter() - _t0
        logger.info(
            "[DOCS-GEN-B-203] repo=%s | 폴더 단위 요약 완료"
            " (%d개 폴더, %.3f초)", repo_id, len(folder_summaries), elapsed,
        )
        return {
            "folder_summaries": folder_summaries,
            "timings": {
                **state.get("timings", {}), "b203_folder_summary": elapsed
            },
        }
    except Exception as exc:
        elapsed = time.perf_counter() - _t0
        logger.exception(
            "[DOCS-GEN-B-203] repo=%s | 폴더 요약 실패 (%.3f초): %s",
            repo_id, elapsed, exc,
        )
        return {
            "status": "failed",
            "error": f"B-203 실패: {exc}",
            "timings": {**state.get("timings", {}), "b203_failed": elapsed},
        }


# ──────────────────────────────────────────────────────────────
# 노드 4: 핵심 실행 플로우 설명 (DOCS-GEN-B-206)
#
# 사용자 요청이 시스템 내부에서 어떻게 처리되는지
# end-to-end 플로우를 문서화.
# ──────────────────────────────────────────────────────────────
async def flow_explain_node(state: GenFormState) -> dict:
    '''
    DOCS-GEN-B-206 구현 노드

    진입점(entrypoint)부터 DB까지의 데이터 흐름을 추적하고
    주요 함수 호출 체인을 문서화한다.
    '''
    _t0 = time.perf_counter()
    repo_id = state["repo_id"]
    try:
        report = dict(state.get("analysis_report") or {})
        doc_summary = state.get("doc_summary") or {}
        readme = await asyncio.to_thread(
            _read_readme, state.get("clone_path")
        )
        entrypoints = report.get("entrypoints", [])
        context = _repo_context(report, readme)

        entry_list = "\n".join(
            f"- {ep}" for ep in entrypoints[:10]
        ) or "진입점 미탐지"
        purpose = doc_summary.get("purpose", "")
        arch_hint = doc_summary.get("architecture_hint", "")
        extra = (
            f"프로젝트 목적: {purpose}\n"
            f"아키텍처 힌트: {arch_hint}\n"
            f"진입점 목록:\n{entry_list}"
        )

        generated = await _llm_json(
            "당신은 시스템 아키텍처를 분석하는 시니어 엔지니어입니다. "
            "제공된 저장소 데이터를 근거로 사용자 요청의 end-to-end 처리 흐름을 "
            "한국어로 설명하세요. "
            "다음 키를 가진 JSON만 반환하세요: "
            "flow_overview(요청 처리 흐름 개요, 2~3문장 문자열), "
            "entry_to_db(진입점 → 서비스 → DB까지 단계별 설명, 문자열 배열 3~6개), "
            "key_call_chain(핵심 함수 호출 체인 한 줄 요약, 문자열).",
            f"{context}\n\n{extra}",
            state.get("llm_model"),
        )

        flow_obj: _FlowExplainOutput | None = None
        if generated:
            try:
                flow_obj = _FlowExplainOutput.model_validate(generated)
            except ValidationError as exc:
                logger.warning(
                    "flow_explain LLM 출력 스키마 불일치, 휴리스틱 대체: %s", exc
                )

        if flow_obj:
            steps = "\n".join(
                f"{i+1}. {s}" for i, s in enumerate(flow_obj.entry_to_db)
            )
            flow_explanation = (
                f"## 핵심 실행 플로우\n\n"
                f"{flow_obj.flow_overview}\n\n"
                f"### 요청 처리 단계\n{steps}\n\n"
                f"### 주요 호출 체인\n{flow_obj.key_call_chain}"
            )
        else:
            entry_str = ", ".join(entrypoints[:5]) or "미탐지"
            flow_explanation = (
                f"## 핵심 실행 플로우\n\n"
                f"진입점: {entry_str}\n\n"
                f"상세 플로우 분석을 위해 LLM API 키 설정이 필요합니다."
            )

        elapsed = time.perf_counter() - _t0
        logger.info(
            "[DOCS-GEN-B-206] repo=%s | 핵심 실행 플로우 설명 완료 (%.3f초)",
            repo_id, elapsed,
        )
        return {
            "flow_explanation": flow_explanation,
            "timings": {
                **state.get("timings", {}), "b206_flow_explain": elapsed
            },
        }
    except Exception as exc:
        elapsed = time.perf_counter() - _t0
        logger.exception(
            "[DOCS-GEN-B-206] repo=%s | 실행 플로우 설명 실패 (%.3f초): %s",
            repo_id, elapsed, exc,
        )
        return {
            "status": "failed",
            "error": f"B-206 실패: {exc}",
            "timings": {**state.get("timings", {}), "b206_failed": elapsed},
        }


# ──────────────────────────────────────────────────────────────
# 노드 5: 온보딩 guide agent 구현 (DOCS-GEN-B-202)
#
# 읽을 순서, 수정 시작점, 위험 파일, 추천 task 생성.
# 선행 조건: B-203(폴더 요약), B-206(플로우 설명) 완료.
# ──────────────────────────────────────────────────────────────
async def onboarding_guide_node(state: GenFormState) -> dict:
    '''
    DOCS-GEN-B-202 구현 노드

    신규 개발자가 코드베이스를 이해하는 최적 경로(읽기 순서, 위험 파일,
    첫 기여 추천 task)를 안내하는 온보딩 가이드를 자동 생성한다.
    '''
    _t0 = time.perf_counter()
    repo_id = state["repo_id"]
    try:
        report = dict(state.get("analysis_report") or {})
        folder_summaries = state.get("folder_summaries") or {}
        flow_explanation = state.get("flow_explanation") or ""
        readme = await asyncio.to_thread(
            _read_readme, state.get("clone_path")
        )
        entrypoints = report.get("entrypoints", [])

        context = _repo_context(report, readme)
        folder_ctx = "\n".join(
            f"- {path}: {summary}"
            for path, summary in folder_summaries.items()
        )
        extra = (
            f"폴더 요약:\n{folder_ctx}\n\n"
            f"실행 플로우:\n{flow_explanation[:500]}"
        )

        generated = await _llm_json(
            "당신은 신입 개발자 온보딩 가이드를 만드는 시니어 엔지니어입니다. "
            "제공된 데이터만 근거로 처음 합류한 개발자를 위한 실질적인 가이드를 "
            "한국어로 작성하세요. 데이터에 없는 파일을 지어내지 마세요. "
            "다음 키를 가진 JSON만 반환하세요: "
            "reading_order(처음 읽을 파일/폴더 경로 목록, 문자열 배열 5~8개), "
            "risk_files(주의 파일 목록, 객체 배열"
            " 각 {file: 경로, reason: 주의 이유}, 최대 5개), "
            "first_tasks(첫 기여 추천 작업, 문자열 배열 2~4개).",
            f"{context}\n\n{extra}",
            state.get("llm_model"),
        )

        guide_obj: _OnboardingGuideOutput | None = None
        if generated:
            try:
                guide_obj = _OnboardingGuideOutput.model_validate(generated)
            except ValidationError as exc:
                logger.warning(
                    "onboarding_guide LLM 출력 스키마 불일치, 휴리스틱 대체: %s",
                    exc,
                )

        if guide_obj and guide_obj.reading_order:
            onboarding_guide: dict[str, Any] = {
                "reading_order": guide_obj.reading_order,
                "risk_files": guide_obj.risk_files,
                "first_tasks": guide_obj.first_tasks,
                "generated_by": settings.OPENAI_MODEL,
            }
        else:
            onboarding_guide = {
                "reading_order": entrypoints[:8],
                "risk_files": [],
                "first_tasks": [],
                "generated_by": "heuristic",
            }

        elapsed = time.perf_counter() - _t0
        logger.info(
            "[DOCS-GEN-B-202] repo=%s | 온보딩 가이드 생성 완료 (%.3f초)",
            repo_id, elapsed,
        )
        return {
            "onboarding_guide": onboarding_guide,
            "timings": {
                **state.get("timings", {}), "b202_onboarding_guide": elapsed
            },
        }
    except Exception as exc:
        elapsed = time.perf_counter() - _t0
        logger.exception(
            "[DOCS-GEN-B-202] repo=%s | 온보딩 가이드 생성 실패 (%.3f초): %s",
            repo_id, elapsed, exc,
        )
        return {
            "status": "failed",
            "error": f"B-202 실패: {exc}",
            "timings": {**state.get("timings", {}), "b202_failed": elapsed},
        }


# ──────────────────────────────────────────────────────────────
# 노드 6: 프로젝트 마스터 리포트 생성 (DOCS-GEN-B-204)
#
# 파일 요약, 폴더 요약, 아키텍처 분석, 온보딩 가이드를
# 하나의 마스터 리포트로 통합.
# 필드: summary, stack, file_map, recommendations, heatmap, durations, guide
# ──────────────────────────────────────────────────────────────
async def master_report_node(state: GenFormState) -> dict:
    '''
    DOCS-GEN-B-204 구현 노드

    이전 모든 노드(B-205, B-201, B-203, B-206, B-202)의 결과를
    하나의 마스터 리포트로 통합하여 반환한다.
    '''
    _t0 = time.perf_counter()
    repo_id = state["repo_id"]
    try:
        report = dict(state.get("analysis_report") or {})
        doc_summary = state.get("doc_summary") or {}
        folder_summaries = state.get("folder_summaries") or {}
        onboarding_guide = state.get("onboarding_guide") or {}
        project_intro = state.get("project_intro") or ""
        flow_explanation = state.get("flow_explanation") or ""
        timings = dict(state.get("timings") or {})

        stats = report.get("stats", {})

        ## summary 섹션: 프로젝트 전체 요약
        summary = {
            "project_intro": project_intro,
            "purpose": doc_summary.get("purpose", ""),
            "key_features": doc_summary.get("key_features", []),
            "tech_context": doc_summary.get("tech_context", ""),
            "architecture_hint": doc_summary.get("architecture_hint", ""),
            "flow_explanation": flow_explanation,
            "stats": stats,
        }

        ## stack 섹션: 기술 스택 정보
        stack = {
            "technologies": report.get("stack", []),
            "primary_language": stats.get("primary_language", ""),
            "languages": report.get("languages", []),
            "frameworks": doc_summary.get("tech_context", ""),
        }

        ## file_map 섹션: 폴더별 역할 맵
        file_map = {
            "folder_summaries": folder_summaries,
            "entrypoints": report.get("entrypoints", []),
            "total_files": stats.get("files", 0),
            "total_lines": stats.get("lines", 0),
        }

        ## recommendations 섹션: 온보딩 권장 사항
        recommendations = {
            "reading_order": onboarding_guide.get("reading_order", []),
            "first_tasks": onboarding_guide.get("first_tasks", []),
        }

        ## heatmap 섹션: 위험 파일 및 주의 영역
        heatmap = {
            "risk_files": onboarding_guide.get("risk_files", []),
            "key_risks": report.get("key_risks", []),
        }

        ## durations 섹션: 파이프라인 단계별 소요시간
        elapsed_now = time.perf_counter() - _t0
        timings["b204_master_report"] = elapsed_now
        total = sum(timings.values())
        durations = {
            **{k: round(v, 3) for k, v in timings.items()},
            "total": round(total, 3),
        }

        ## guide 섹션: 최종 온보딩 가이드 (B-202 결과 전달)
        guide = {
            "reading_order": onboarding_guide.get("reading_order", []),
            "risk_files": onboarding_guide.get("risk_files", []),
            "first_tasks": onboarding_guide.get("first_tasks", []),
            "generated_by": onboarding_guide.get("generated_by", "heuristic"),
        }

        master_report: dict[str, Any] = {
            "repo_id": repo_id,
            "summary": summary,
            "stack": stack,
            "file_map": file_map,
            "recommendations": recommendations,
            "heatmap": heatmap,
            "durations": durations,
            "guide": guide,
        }

        summary_line = " | ".join(
            f"{k}={v:.3f}초" for k, v in timings.items()
        )
        logger.info(
            "[DOCS-GEN-B-204] repo=%s | 마스터 리포트 생성 완료"
            " → %s | 합계=%.3f초", repo_id, summary_line, total,
        )
        return {
            "master_report": master_report,
            "status": "completed",
            "timings": timings,
        }
    except Exception as exc:
        elapsed = time.perf_counter() - _t0
        logger.exception(
            "[DOCS-GEN-B-204] repo=%s | 마스터 리포트 생성 실패 (%.3f초): %s",
            repo_id, elapsed, exc,
        )
        return {
            "status": "failed",
            "error": f"B-204 실패: {exc}",
            "timings": {**state.get("timings", {}), "b204_failed": elapsed},
        }
