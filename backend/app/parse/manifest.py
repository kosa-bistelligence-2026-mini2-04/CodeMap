"""RAG-PARSE B-204/B-205/B-206: 설정 파일 탐색 + 실행 방법·기술 스택 추론.

- B-204 tag_config_files: package.json/requirements.txt/Dockerfile 등 설정 파일을
  식별해 metadata["is_config"]=True로 태깅한다.
- B-205 extract_run_commands: 설정 파일을 기반으로 설치·실행 명령을 추론한다.
- B-206 detect_tech_stack: 의존성 매니페스트에서 프레임워크·런타임·DB를 추론한다.
명세: docs/03_Specifications/02_RAG/spec/RAG_PARSE_SPEC.md (B-204, B-205, B-206)
"""

from __future__ import annotations

import json
import logging
import re
import tomllib
from pathlib import Path

from app.infra.config import get_settings
from app.parse.schemas import ParsedFile, RunCommandSet
from app.parse.tech_catalog import (
    CATEGORY_GUIDE,
    COMPOSE_IMAGE_TO_TECH,
    DOCKER_IMAGE_TO_TECH,
    MANIFEST_TECHS,
    NODE_DEP_TO_TECH,
    PY_DB_DRIVER_PKGS,
    PY_DEP_TO_TECH,
    TECH_CATEGORY,
)

logger = logging.getLogger(__name__)
settings = get_settings()
_LLM_TIMEOUT_SECONDS = 30
_LLM_MAX_RETRIES = 2
_LLM_MAX_CANDIDATES = 40

# 설정/매니페스트 파일 이름 (소문자 비교 — Dockerfile/Makefile 등 대문자 대응).
_CONFIG_FILE_NAMES = {
    # JS/TS
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "pnpm-workspace.yaml", "tsconfig.json", "bun.lock", "bun.lockb",
    "deno.json", "deno.jsonc",
    "next.config.js", "next.config.mjs", "next.config.ts",
    "vite.config.ts", "vite.config.js",
    "eslint.config.js", "eslint.config.mjs", "prettier.config.js",
    "tailwind.config.js", "tailwind.config.ts", "postcss.config.js",
    # Python
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "pipfile", "pipfile.lock", "poetry.lock", "tox.ini", "ruff.toml",
    "uv.lock", ".python-version",
    # 컨테이너 / 오케스트레이션
    "dockerfile", "compose.yml", "compose.yaml",
    "docker-compose.yml", "docker-compose.yaml", ".dockerignore",
    "kubernetes.yml", "kubernetes.yaml", "helmfile.yaml",
    # 환경 변수 예시 (실제 .env는 민감파일이라 directory 단계에서 content 제외)
    ".env.example", ".env.sample", ".env.template",
    # 기타 언어 / 빌드
    "go.mod", "go.sum", "cargo.toml", "cargo.lock", "pubspec.yaml", "pubspec.yml",
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "analysis_options.yaml",
    "gemfile", "gemfile.lock", "composer.json", "makefile", "cmakelists.txt",
    "terraform.tf", "terragrunt.hcl",
}


def _is_config_file(path: str) -> bool:
    """파일 경로가 설정/매니페스트 파일이면 True (이름 기준, 대소문자 무시)."""
    name = Path(path).name.lower()
    if name in _CONFIG_FILE_NAMES:
        return True
    # requirements*.txt 변형(requirements-dev.txt 등)도 포함
    if name.startswith("requirements") and name.endswith(".txt"):
        return True
    if name.startswith("docker-compose.") and name.endswith((".yml", ".yaml")):
        return True
    if path.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")):
        return True
    if name.endswith((".tf", ".tfvars")):
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
    "bun.lockb": "bun",
    "bun.lock": "bun",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "package-lock.json": "npm",
}
_FASTAPI_APP_PATTERN = re.compile(r"(?m)^\s*app\s*=\s*FastAPI\s*\(")


def _detect_node_pm(names: set[str]) -> str:
    """lockfile 기준 Node 패키지 매니저 추론 (없으면 npm)."""
    for lockfile, pm in _PM_BY_LOCKFILE.items():
        if lockfile in names:
            return pm
    return "npm"


def _node_run(pm: str, script: str) -> str:
    """패키지 매니저별 스크립트 실행 명령 ('npm run dev' vs 'pnpm dev' 등)."""
    if pm == "bun":
        return f"bun run {script}"
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


def _module_path(path: str) -> str:
    return Path(path).with_suffix("").as_posix().replace("/", ".")


def _has_compose_file(names: set[str]) -> bool:
    return bool(
        {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"} & names
        or any(
            name.startswith("docker-compose.") and name.endswith((".yml", ".yaml"))
            for name in names
        )
    )


def _detect_python_run(files: list[ParsedFile]) -> str:
    for node in files:
        if node.file_type != "FILE" or not node.path.endswith(".py"):
            continue
        content = node.content or ""
        if _FASTAPI_APP_PATTERN.search(content):
            return f"uvicorn {_module_path(node.path)}:app --reload"
    for node in files:
        if node.file_type == "FILE" and Path(node.path).name in {"manage.py"}:
            return "python manage.py runserver"
    return ""


async def extract_run_command_details(files: list[ParsedFile]) -> RunCommandSet:
    """설정 파일 기반으로 설치·실행 명령을 추론한다 (RAG-PARSE-B-205).

    package.json(+lockfile)·requirements.txt·pyproject.toml·Dockerfile 등을 보고
    'npm install'/'npm run dev'/'pip install -r requirements.txt' 같은 명령을 만든다.
    순수 로직이라 I/O는 없지만 파이프라인 단계 일관성·테스트 계약을 위해 async로 유지한다.
    """
    file_nodes = {
        Path(f.path).name.lower(): f for f in files if f.file_type == "FILE"
    }
    names = set(file_nodes)
    install = ""
    run = ""
    build: str | None = None

    # Node/JS — package.json + lockfile로 매니저 추론, scripts에서 실행 명령
    if "package.json" in names:
        pm = _detect_node_pm(names)
        install = f"{pm} install"
        scripts = _package_scripts(file_nodes["package.json"])
        for script in ("dev", "start"):
            if script in scripts:
                run = _node_run(pm, script)
                break
        if "build" in scripts:
            build = _node_run(pm, "build")

    # Python — 의존성 설치
    if "requirements.txt" in names:
        install = install or "pip install -r requirements.txt"
    elif "pyproject.toml" in names:
        install = install or "pip install ."
    if "pipfile" in names:
        install = install or "pipenv install"
    run = run or _detect_python_run(files)

    # 컨테이너 — compose 우선, 없으면 Dockerfile 빌드
    if _has_compose_file(names):
        run = run or "docker compose up"
        build = build or "docker compose build"
    elif "dockerfile" in names:
        build = build or "docker build -t app ."

    return RunCommandSet(install=install, run=run, build=build)


async def extract_run_commands(files: list[ParsedFile]) -> list[str]:
    """설정 파일 기반 실행 명령을 기존 list[str] 계약으로 반환한다."""
    details = await extract_run_command_details(files)
    file_nodes = {
        Path(f.path).name.lower(): f for f in files if f.file_type == "FILE"
    }
    names = set(file_nodes)
    commands = [details.install, details.run, details.build]
    if "requirements.txt" in names:
        commands.append("pip install -r requirements.txt")
    elif "pyproject.toml" in names:
        commands.append("pip install .")
    if _has_compose_file(names):
        commands.extend(["docker compose build", "docker compose up"])
    elif "dockerfile" in names:
        commands.append("docker build -t app .")
    deduped: list[str] = []
    for command in commands:
        if command and command not in deduped:
            deduped.append(command)
    return deduped


# ── B-206: 기술 스택 추론 ───────────────────────────────────────────────


def _clean_version(raw: object) -> str | None:
    """의존성 버전 문자열에서 ^, >= 같은 범위 표기를 줄여 표시용 버전을 만든다."""
    if raw is None:
        return None
    version = str(raw).strip().strip('"').strip("'")
    if not version:
        return None
    return re.sub(r"^[\^~<>=! ]+", "", version) or None


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


def _requirements_versions(content: str | None) -> dict[str, str | None]:
    """requirements.txt에서 패키지명 -> 표시용 버전 매핑을 추출한다."""
    versions: dict[str, str | None] = {}
    for raw in (content or "").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-")):
            continue
        name = re.split(r"[=<>!~;\[\] ]", line, maxsplit=1)[0].strip().lower()
        if not name:
            continue
        match = re.search(r"(?:==|>=|<=|~=|>|<)\s*([^;\s]+)", line)
        versions[name] = _clean_version(match.group(1)) if match else None
    return versions


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


def _package_dep_versions(node: ParsedFile) -> dict[str, str | None]:
    """package.json에서 dependency 이름 -> 표시용 버전 매핑을 추출한다."""
    try:
        data = json.loads(node.content or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    versions: dict[str, str | None] = {}
    if isinstance(data, dict):
        for key in ("dependencies", "devDependencies"):
            section = data.get(key)
            if isinstance(section, dict):
                for dep, version in section.items():
                    versions[dep.lower()] = _clean_version(version)
    return versions


def _pyproject_dep_versions(content: str | None) -> dict[str, str | None]:
    """pyproject.toml에서 주요 의존성 후보를 추출한다."""
    try:
        data = tomllib.loads(content or "")
    except tomllib.TOMLDecodeError:
        return {}
    versions: dict[str, str | None] = {}

    project = data.get("project")
    if isinstance(project, dict):
        dependencies = project.get("dependencies")
        if isinstance(dependencies, list):
            for dep in dependencies:
                if not isinstance(dep, str):
                    continue
                name = re.split(r"[=<>!~;\[\] ]", dep, maxsplit=1)[0].strip().lower()
                match = re.search(r"(?:==|>=|<=|~=|>|<)\s*([^;\s]+)", dep)
                if name:
                    versions[name] = _clean_version(match.group(1)) if match else None

    poetry = data.get("tool", {}).get("poetry") if isinstance(data.get("tool"), dict) else None
    poetry_deps = poetry.get("dependencies") if isinstance(poetry, dict) else None
    if isinstance(poetry_deps, dict):
        for dep, version in poetry_deps.items():
            dep_lower = str(dep).lower()
            if dep_lower != "python":
                versions[dep_lower] = _clean_version(version)
    return versions


def _pubspec_dep_versions(content: str | None) -> dict[str, str | None]:
    """pubspec.yaml의 dependencies/dev_dependencies에서 패키지 후보를 가볍게 추출한다."""
    versions: dict[str, str | None] = {}
    in_deps = False
    for raw in (content or "").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^(dependencies|dev_dependencies):\s*$", stripped):
            in_deps = True
            continue
        if in_deps and re.match(r"^[^\s].*:\s*$", line):
            in_deps = False
        if not in_deps:
            continue
        match = re.match(r"^\s{2,}([A-Za-z0-9_+-]+):\s*([^#]*)", line)
        if match:
            name = match.group(1).lower()
            raw_version = match.group(2).strip() or None
            if name != "sdk":
                versions[name] = _clean_version(raw_version)
    return versions


def _manifest_stack_items(node: ParsedFile) -> list[dict[str, str | None]]:
    """파일명 자체로 추론 가능한 언어/런타임/빌드 스택을 반환한다."""
    name = Path(node.path).name.lower()
    items = [_stack_item(tech, version, node.path) for tech, version in MANIFEST_TECHS.get(name, ())]
    if name in {"pubspec.yaml", "pubspec.yml"} and re.search(r"(^|\n)\s*sdk:\s*flutter\b", node.content or ""):
        items.append(_stack_item("Flutter", None, node.path))
    return items


def _dockerfile_stack_items(node: ParsedFile) -> list[dict[str, str | None]]:
    """Dockerfile FROM 라인에서 런타임/인프라 기술 스택을 추출한다."""
    items: list[dict[str, str | None]] = []
    content = node.content or ""
    if re.search(r"^\s*FROM\s+", content, flags=re.IGNORECASE | re.MULTILINE):
        items.append(_stack_item("Docker", None, node.path))
    for image, tag in re.findall(
        r"^\s*FROM\s+([A-Za-z0-9._/-]+)(?::([A-Za-z0-9._-]+))?",
        content,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        image_name = image.rsplit("/", 1)[-1].lower()
        tech = DOCKER_IMAGE_TO_TECH.get(image_name)
        if tech:
            version = tag.split("-", 1)[0] if tag else None
            items.append(_stack_item(tech, _clean_version(version), node.path))
    return items


def _compose_stack_items(node: ParsedFile) -> list[dict[str, str | None]]:
    """docker-compose image 라인에서 DB/확장/인프라 기술 스택을 추출한다."""
    items = [_stack_item("Docker Compose", None, node.path)]
    for image_ref in re.findall(r"^\s*image:\s*['\"]?([^'\"\s#]+)", node.content or "", re.MULTILINE):
        image = image_ref.split("@", 1)[0]
        name, _, tag = image.partition(":")
        image_name = name.rsplit("/", 1)[-1].lower()
        version = _clean_version(tag) if tag else None
        tech = COMPOSE_IMAGE_TO_TECH.get(image_name)
        if tech:
            items.append(_stack_item(tech, version, node.path))
        if "pgvector" in image.lower():
            items.append(_stack_item("pgvector", version, node.path))
    return items


def _unknown_candidate(name: str, version: str | None, source: str, ecosystem: str) -> dict[str, str | None]:
    return {
        "name": name,
        "version": version,
        "source": source,
        "ecosystem": ecosystem,
    }


def _json_from_llm_text(text: str) -> dict | None:
    """LLM 응답에서 JSON 객체만 안전하게 추출한다."""
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _normalize_llm_stack_item(item: object) -> dict[str, str | None] | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("name") or "").strip()
    source = str(item.get("source") or "").strip()
    if not name or not source:
        return None
    category = str(item.get("category") or TECH_CATEGORY.get(name) or "library").strip()
    if category not in CATEGORY_GUIDE:
        category = TECH_CATEGORY.get(name, "library")
    return {
        "name": name,
        "version": _clean_version(item.get("version")),
        "category": category,
        "source": source,
    }


async def _classify_unknown_tech_with_llm(
    candidates: list[dict[str, str | None]],
) -> list[dict[str, str | None]]:
    """카탈로그 밖 dependency 후보를 LLM으로 분류한다. 실패하면 빈 목록으로 폴백."""
    api_key = settings.OPENAI_API_KEY.get_secret_value()
    if not api_key or not candidates:
        return []
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
            timeout=_LLM_TIMEOUT_SECONDS,
            max_retries=_LLM_MAX_RETRIES,
        )
        response = await llm.ainvoke([
            (
                "system",
                "You classify repository dependency candidates into high-level technology stack items. "
                "Use only the provided candidates as evidence. Omit tiny utility packages that are not useful "
                "for a project-level tech stack. Return strict JSON only.",
            ),
            (
                "user",
                json.dumps(
                    {
                        "categoryGuide": CATEGORY_GUIDE,
                        "candidates": candidates[:_LLM_MAX_CANDIDATES],
                        "responseShape": {
                            "items": [
                                {
                                    "name": "Technology display name",
                                    "version": "version or null",
                                    "category": "one categoryGuide key",
                                    "source": "candidate source path",
                                }
                            ]
                        },
                    },
                    ensure_ascii=False,
                ),
            ),
        ])
        data = _json_from_llm_text(str(response.content))
        if not data:
            return []
        items = data.get("items")
        if not isinstance(items, list):
            return []
        return [normalized for item in items if (normalized := _normalize_llm_stack_item(item))]
    except Exception as exc:  # LLM 오류는 기술 스택 분석 전체를 막지 않는다.
        logger.warning("기술 스택 LLM 분류 실패, 규칙 기반 결과만 사용합니다: %s", exc)
        return []


def _stack_item(name: str, version: str | None, source: str) -> dict[str, str | None]:
    return {
        "name": name,
        "version": version,
        "category": TECH_CATEGORY.get(name, "library"),
        "source": source,
    }


def _dedupe_stack_items(items: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
    """기술명 기준으로 중복을 제거하되, 버전이 있는 항목을 우선 보존한다."""
    by_name: dict[str, dict[str, str | None]] = {}
    for item in items:
        current = by_name.get(item["name"])
        if current is None or (not current.get("version") and item.get("version")):
            by_name[item["name"]] = item
    return sorted(by_name.values(), key=lambda item: (str(item["category"]), str(item["name"])))


async def detect_tech_stack_details(files: list[ParsedFile]) -> list[dict[str, str | None]]:
    """기술 스택을 API 응답용 객체(name/version/category/source)로 추론한다."""
    items: list[dict[str, str | None]] = []
    unknown_candidates: list[dict[str, str | None]] = []
    for node in files:
        if node.file_type != "FILE":
            continue
        name = Path(node.path).name.lower()
        items.extend(_manifest_stack_items(node))
        if name == "package.json":
            for dep, version in _package_dep_versions(node).items():
                dep_lower = dep.lower()
                tech = NODE_DEP_TO_TECH.get(dep_lower)
                if tech:
                    items.append(_stack_item(tech, version, node.path))
                else:
                    unknown_candidates.append(_unknown_candidate(dep, version, node.path, "node"))
        elif name.startswith("requirements") and name.endswith(".txt"):
            for pkg, version in _requirements_versions(node.content).items():
                pkg_lower = pkg.lower()
                tech = PY_DEP_TO_TECH.get(pkg_lower)
                if tech:
                    display_version = None if pkg_lower in PY_DB_DRIVER_PKGS else version
                    items.append(_stack_item(tech, display_version, node.path))
                else:
                    unknown_candidates.append(_unknown_candidate(pkg, version, node.path, "python"))
        elif name == "pyproject.toml":
            for pkg, version in _pyproject_dep_versions(node.content).items():
                pkg_lower = pkg.lower()
                tech = PY_DEP_TO_TECH.get(pkg_lower)
                if tech:
                    display_version = None if pkg_lower in PY_DB_DRIVER_PKGS else version
                    items.append(_stack_item(tech, display_version, node.path))
                else:
                    unknown_candidates.append(_unknown_candidate(pkg, version, node.path, "python"))
        elif name == "dockerfile":
            items.extend(_dockerfile_stack_items(node))
        elif name in {"docker-compose.yml", "docker-compose.yaml"}:
            items.extend(_compose_stack_items(node))
        elif name in {"pubspec.yaml", "pubspec.yml"}:
            for pkg, version in _pubspec_dep_versions(node.content).items():
                unknown_candidates.append(_unknown_candidate(pkg, version, node.path, "dart"))
    llm_items = await _classify_unknown_tech_with_llm(unknown_candidates)
    return _dedupe_stack_items([*items, *llm_items])


async def detect_tech_stack(files: list[ParsedFile]) -> list[str]:
    """의존성 매니페스트에서 프레임워크·런타임·DB를 추론한다 (RAG-PARSE-B-206).

    package.json(dependencies/devDependencies)·requirements.txt·pyproject.toml의
    의존성 이름을 알려진 기술명으로 매핑한다. 정렬된 중복 없는 목록을 반환한다.
    순수 로직이라 async만 유지(I/O 없음) — find_entry_points와 정합.
    """
    details = await detect_tech_stack_details(files)
    return sorted({str(item["name"]) for item in details})
