"""RAG-PARSE B-204/B-205/B-206: 설정 파일 탐색 + 실행 방법·기술 스택 추론.

- B-204 tag_config_files: package.json/requirements.txt/Dockerfile 등 설정 파일을
  식별해 metadata["is_config"]=True로 태깅한다.
- B-205 extract_run_commands: 설정 파일을 기반으로 설치·실행 명령을 추론한다.
- B-206 detect_tech_stack: 의존성 매니페스트에서 프레임워크·런타임·DB를 추론한다.
명세: docs/03_Specifications/02_RAG/spec/RAG_PARSE_SPEC.md (B-204, B-205, B-206)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.parse.schemas import ParsedFile

# 설정/매니페스트 파일 이름 (소문자 비교 — Dockerfile/Makefile 등 대문자 대응).
_CONFIG_FILE_NAMES = {
    # JS/TS
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "pnpm-workspace.yaml", "tsconfig.json",
    "next.config.js", "next.config.mjs", "next.config.ts",
    "vite.config.ts", "vite.config.js",
    # Python
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "pipfile", "pipfile.lock", "poetry.lock", "tox.ini",
    # 컨테이너 / 오케스트레이션
    "dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore",
    # 환경 변수 예시 (실제 .env는 민감파일이라 directory 단계에서 content 제외)
    ".env.example", ".env.sample", ".env.template",
    # 기타 언어 / 빌드
    "go.mod", "go.sum", "cargo.toml", "cargo.lock",
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "gemfile", "gemfile.lock", "composer.json", "makefile", "cmakelists.txt",
}


def _is_config_file(path: str) -> bool:
    """파일 경로가 설정/매니페스트 파일이면 True (이름 기준, 대소문자 무시)."""
    name = Path(path).name.lower()
    if name in _CONFIG_FILE_NAMES:
        return True
    # requirements*.txt 변형(requirements-dev.txt 등)도 포함
    if name.startswith("requirements") and name.endswith(".txt"):
        return True
    return False


async def tag_config_files(files: list[ParsedFile]) -> list[ParsedFile]:
    """설정 파일을 식별해 metadata['is_config']=True로 태깅한다 (RAG-PARSE-B-204).

    순수 문자열 로직이라 I/O는 없지만, PARSE 파이프라인 단계 일관성과 테스트
    계약(await tag_config_files(...))을 위해 async로 유지한다(find_entry_points와 정합).
    입력을 in-place로 변경하지 않고 새 객체(model_copy)를 반환한다.
    """
    result: list[ParsedFile] = []
    for node in files:
        if node.file_type == "FILE" and _is_config_file(node.path):
            metadata = {**(node.metadata or {}), "is_config": True}
            result.append(node.model_copy(update={"metadata": metadata}))
        else:
            result.append(node)
    return result


# ── B-205: 실행 방법 추론 ───────────────────────────────────────────────
# lockfile → Node 패키지 매니저 (없으면 npm 기본)
_PM_BY_LOCKFILE = {
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "package-lock.json": "npm",
}


def _detect_node_pm(names: set[str]) -> str:
    """lockfile 기준 Node 패키지 매니저 추론 (없으면 npm)."""
    for lockfile, pm in _PM_BY_LOCKFILE.items():
        if lockfile in names:
            return pm
    return "npm"


def _node_run(pm: str, script: str) -> str:
    """패키지 매니저별 스크립트 실행 명령 ('npm run dev' vs 'pnpm dev' 등)."""
    if pm == "npm":
        return "npm start" if script == "start" else f"npm run {script}"
    return f"{pm} {script}"


def _package_scripts(node: ParsedFile) -> dict:
    """package.json content에서 scripts 객체 추출 (파싱 실패 시 빈 dict)."""
    try:
        data = json.loads(node.content or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    scripts = data.get("scripts") if isinstance(data, dict) else None
    return scripts if isinstance(scripts, dict) else {}


async def extract_run_commands(files: list[ParsedFile]) -> list[str]:
    """설정 파일 기반으로 설치·실행 명령을 추론한다 (RAG-PARSE-B-205).

    package.json(+lockfile)·requirements.txt·pyproject.toml·Dockerfile 등을 보고
    'npm install'/'npm run dev'/'pip install -r requirements.txt' 같은 명령을 만든다.
    순수 로직이라 I/O는 없지만 파이프라인 단계 일관성·테스트 계약을 위해 async로 유지한다.
    """
    file_nodes = {
        Path(f.path).name.lower(): f for f in files if f.file_type == "FILE"
    }
    names = set(file_nodes)
    commands: list[str] = []

    # Node/JS — package.json + lockfile로 매니저 추론, scripts에서 실행 명령
    if "package.json" in names:
        pm = _detect_node_pm(names)
        commands.append(f"{pm} install")
        scripts = _package_scripts(file_nodes["package.json"])
        for script in ("dev", "start"):
            if script in scripts:
                commands.append(_node_run(pm, script))
                break

    # Python — 의존성 설치
    if "requirements.txt" in names:
        commands.append("pip install -r requirements.txt")
    elif "pyproject.toml" in names:
        commands.append("pip install .")
    if "pipfile" in names:
        commands.append("pipenv install")

    # 컨테이너 — compose 우선, 없으면 Dockerfile 빌드
    if "docker-compose.yml" in names or "docker-compose.yaml" in names:
        commands.append("docker compose up")
    elif "dockerfile" in names:
        commands.append("docker build -t app .")

    return commands


# ── B-206: 기술 스택 추론 ───────────────────────────────────────────────
# Node 의존성(package.json) → 기술명
_NODE_DEP_TO_TECH = {
    "next": "Next.js", "react": "React", "vue": "Vue", "@angular/core": "Angular",
    "svelte": "Svelte", "nuxt": "Nuxt", "express": "Express",
    "@nestjs/core": "NestJS", "typescript": "TypeScript", "vite": "Vite",
    "tailwindcss": "Tailwind CSS", "prisma": "Prisma",
}
# Python 의존성(requirements.txt/pyproject.toml) → 기술명. DB 드라이버도 포함.
_PY_DEP_TO_TECH = {
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "starlette": "Starlette", "uvicorn": "Uvicorn", "gunicorn": "Gunicorn",
    "sqlalchemy": "SQLAlchemy", "pydantic": "Pydantic", "langchain": "LangChain",
    "pandas": "pandas", "numpy": "NumPy", "torch": "PyTorch", "tensorflow": "TensorFlow",
    # DB 드라이버 → DB
    "asyncpg": "PostgreSQL", "psycopg": "PostgreSQL", "psycopg2": "PostgreSQL",
    "pymysql": "MySQL", "mysqlclient": "MySQL", "pymongo": "MongoDB", "redis": "Redis",
}


def _requirements_packages(content: str | None) -> set[str]:
    """requirements.txt content에서 패키지명 집합 추출 (버전/주석/옵션 제거)."""
    pkgs: set[str] = set()
    for raw in (content or "").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-")):
            continue
        # fastapi==0.115.0 / sqlalchemy>=2.0 / pkg[extra]==1.0 → 이름만
        name = re.split(r"[=<>!~;\[\] ]", line, maxsplit=1)[0].strip().lower()
        if name:
            pkgs.add(name)
    return pkgs


def _package_deps(node: ParsedFile) -> set[str]:
    """package.json content에서 dependencies+devDependencies 키 집합 추출."""
    try:
        data = json.loads(node.content or "{}")
    except (json.JSONDecodeError, TypeError):
        return set()
    deps: set[str] = set()
    if isinstance(data, dict):
        for key in ("dependencies", "devDependencies"):
            section = data.get(key)
            if isinstance(section, dict):
                deps.update(k.lower() for k in section)
    return deps


async def detect_tech_stack(files: list[ParsedFile]) -> list[str]:
    """의존성 매니페스트에서 프레임워크·런타임·DB를 추론한다 (RAG-PARSE-B-206).

    package.json(dependencies/devDependencies)·requirements.txt·pyproject.toml의
    의존성 이름을 알려진 기술명으로 매핑한다. 정렬된 중복 없는 목록을 반환한다.
    순수 로직이라 async만 유지(I/O 없음) — find_entry_points와 정합.
    """
    file_nodes = {
        Path(f.path).name.lower(): f for f in files if f.file_type == "FILE"
    }
    stack: set[str] = set()

    # Node — package.json 의존성
    if "package.json" in file_nodes:
        for dep in _package_deps(file_nodes["package.json"]):
            tech = _NODE_DEP_TO_TECH.get(dep)
            if tech:
                stack.add(tech)

    # Python — requirements.txt / pyproject.toml
    if "requirements.txt" in file_nodes:
        for pkg in _requirements_packages(file_nodes["requirements.txt"].content):
            tech = _PY_DEP_TO_TECH.get(pkg)
            if tech:
                stack.add(tech)
    if "pyproject.toml" in file_nodes:
        content = (file_nodes["pyproject.toml"].content or "").lower()
        for pkg, tech in _PY_DEP_TO_TECH.items():
            if re.search(rf"(^|[\"'\s]){re.escape(pkg)}([\"'\s=<>~]|$)", content):
                stack.add(tech)

    return sorted(stack)
