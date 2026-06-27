"""Build and execution environment validation tool."""

from __future__ import annotations

from pathlib import Path


# ──────────────────────────────────────────────
# verify_build_environment
# ──────────────────────────────────────────────
def verify_build_environment(
    file_paths: list[Path], primary_language: str, root_path: Path
) -> dict:
    '''
    저장소의 주 언어에 대응하는 빌드 매니페스트 파일 및 인프라 구성을 검증합니다.
    '''
    stack_signals = {
        "package.json": "Node.js",
        "next.config.ts": "Next.js",
        "next.config.js": "Next.js",
        "vite.config.ts": "Vite",
        "vite.config.js": "Vite",
        "requirements.txt": "Python",
        "pyproject.toml": "Python",
        "manage.py": "Django",
        "pom.xml": "Spring/Java",
        "build.gradle": "Gradle/Java",
        "go.mod": "Go",
        "Cargo.toml": "Rust",
        "docker-compose.yml": "Docker",
        "docker-compose.yaml": "Docker",
    }

    entrypoint_names = {
        "main.py", "app.py", "manage.py", "main.ts", "main.tsx", "index.ts",
        "index.tsx", "app.tsx", "page.tsx", "server.ts", "server.js",
        "main.go", "main.rs", "pom.xml", "build.gradle",
        "docker-compose.yml", "docker-compose.yaml",
    }

    detected_stack: set[str] = set()
    entrypoints: list[str] = []
    found_manifest_files: set[str] = set()

    for path in file_paths:
        name = path.name
        if name in stack_signals:
            detected_stack.add(stack_signals[name])
            found_manifest_files.add(name)
        if name in entrypoint_names:
            try:
                rel = path.relative_to(root_path).as_posix()
                entrypoints.append(rel)
            except ValueError:
                entrypoints.append(path.name)

    ## 주요 언어별 필수 매니페스트 존재성 매핑
    mandatory_manifests: dict[str, set[str]] = {
        "Python": {"requirements.txt", "pyproject.toml", "setup.py"},
        "TypeScript": {"package.json"},
        "JavaScript": {"package.json"},
        "Go": {"go.mod"},
        "Rust": {"Cargo.toml"},
        "Java": {"pom.xml", "build.gradle"},
    }

    has_mandatory_manifest = True
    if primary_language in mandatory_manifests:
        required = mandatory_manifests[primary_language]
        if not (found_manifest_files & required):
            has_mandatory_manifest = False

    return {
        "detected_stack": sorted(list(detected_stack)),
        "entrypoints": sorted(list(set(entrypoints))),
        "has_mandatory_manifest": has_mandatory_manifest,
    }
