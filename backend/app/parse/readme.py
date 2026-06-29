"""RAG-PARSE B-201: README 분석.

저장소 루트의 README를 찾아 프로젝트 목적·핵심 기능 요약을 추출한다.
README가 없으면 모델 호출 없이 None을 반환한다.
명세: docs/03_Specifications/02_RAG/spec/RAG_PARSE_SPEC.md (B-201)

주의: 같은 'B-201'이라도 RAG-EMBED-B-201(임베딩 생성, #44)과는 다른 기능이다.
LLM 호출은 nodes._llm_json 패턴을 따르며, 키 미설정/실패 시 휴리스틱으로 폴백한다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from app.infra.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# README 후보 파일 (앞에서부터 우선). nodes._read_readme와 동일 정책.
_README_NAMES = ("README.md", "readme.md", "README.rst", "README.txt", "README", "readme")
_MAX_README_CHARS = 3000     # LLM 입력 상한 (nodes._read_readme와 동일)
_MAX_SUMMARY_CHARS = 600     # 휴리스틱 폴백 요약 길이
_LLM_TIMEOUT_SECONDS = 30
_LLM_MAX_RETRIES = 2


def _read_readme(repo_path: str) -> str | None:
    """저장소 루트에서 README를 찾아 발췌(최대 _MAX_README_CHARS)한다. 없으면 None."""
    root = Path(repo_path)
    if not root.is_dir():
        return None
    for name in _README_NAMES:
        path = root / name
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            content = content.strip()
            if content:
                return content[:_MAX_README_CHARS]
    return None


def _manifest_fallback_summary(repo_path: str) -> str | None:
    """README가 없을 때 manifest 파일만 근거로 대체 요약을 만든다."""
    root = Path(repo_path)
    if not root.is_dir():
        return None

    signals: list[str] = []

    package_json = root / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            name = data.get("name")
            scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
            raw_deps = data.get("dependencies")
            raw_dev_deps = data.get("devDependencies")
            deps: dict = raw_deps if isinstance(raw_deps, dict) else {}
            dev_deps: dict = raw_dev_deps if isinstance(raw_dev_deps, dict) else {}
            techs = sorted(set(deps.keys()) | set(dev_deps.keys()))[:8]
            bits = ["Node.js/JavaScript 설정(package.json)이 있습니다"]
            if name:
                bits.append(f"패키지명은 {name}입니다")
            if scripts:
                bits.append(f"실행 스크립트는 {', '.join(sorted(scripts)[:5])}입니다")
            if techs:
                bits.append(f"주요 의존성은 {', '.join(techs)}입니다")
            signals.append(". ".join(bits))

    requirements = sorted(root.glob("requirements*.txt"))
    if requirements:
        packages: list[str] = []
        for path in requirements[:3]:
            try:
                for raw in path.read_text(encoding="utf-8").splitlines():
                    line = raw.strip()
                    if line and not line.startswith(("#", "-")):
                        packages.append(line.split("==", 1)[0].split(">=", 1)[0].split("~=", 1)[0])
            except (OSError, UnicodeDecodeError):
                continue
        if packages:
            signals.append(
                f"Python 의존성 파일({requirements[0].name}) 기준 주요 패키지는 "
                f"{', '.join(packages[:8])}입니다"
            )
        else:
            signals.append(f"Python 의존성 파일({requirements[0].name})이 있습니다")

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        signals.append("Python 프로젝트 설정(pyproject.toml)이 있습니다")

    for name in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        if (root / name).is_file():
            signals.append(f"컨테이너 실행 설정({name})이 있습니다")

    if not signals:
        return None
    return "README가 없어 설정 파일을 기준으로 대체 요약했습니다. " + " ".join(signals)


def _heuristic_summary(readme: str) -> str:
    """LLM 미사용 시 폴백: 마크다운 잡음 제거 후 앞부분을 요약으로 사용."""
    lines: list[str] = []
    for raw in readme.splitlines():
        line = raw.strip().lstrip("#").strip()  # 헤더 마커 제거
        if line and not line.startswith(("![", "[!", "---", "===")):
            lines.append(line)
    summary = " ".join(lines)[:_MAX_SUMMARY_CHARS].strip()
    return summary or readme[:_MAX_SUMMARY_CHARS].strip()


async def _summarize_with_llm(readme: str) -> str | None:
    """OPENAI_API_KEY가 있으면 LLM으로 README를 요약, 미설정/실패 시 None."""
    if not settings.OPENAI_API_KEY.get_secret_value():
        return None
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
            timeout=_LLM_TIMEOUT_SECONDS,
            max_retries=_LLM_MAX_RETRIES,
        )
        response = await llm.ainvoke([
            (
                "system",
                "당신은 코드베이스 온보딩 문서를 작성하는 엔지니어입니다. "
                "주어진 README만 근거로 프로젝트의 목적과 핵심 기능을 한국어 3~5문장으로 "
                "요약하세요. README에 없는 내용은 지어내지 마세요.",
            ),
            ("user", readme),
        ])
        summary = str(response.content).strip()
        return summary or None
    except Exception as exc:  # LLM 오류는 분석을 막지 않고 휴리스틱으로 폴백
        logger.warning("README LLM 요약 실패, 휴리스틱으로 대체합니다: %s", exc)
        return None


async def parse_readme(repo_path: str) -> str | None:
    """저장소 README를 요약해 반환한다 (RAG-PARSE-B-201).

    README가 없으면 모델 호출 없이 None을 반환한다(테스트 계약).
    README가 있으면 LLM 요약을 시도하고, 키 미설정/실패 시 휴리스틱 요약으로 폴백한다.
    """
    readme = await asyncio.to_thread(_read_readme, repo_path)
    if not readme:
        return await asyncio.to_thread(_manifest_fallback_summary, repo_path)
    summary = await _summarize_with_llm(readme)
    return summary or _heuristic_summary(readme)
