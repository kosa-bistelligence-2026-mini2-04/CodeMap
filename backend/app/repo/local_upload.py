"""Validation and extraction helpers for browser-selected local repositories."""

import re
import shutil
from pathlib import Path, PurePosixPath

from fastapi import UploadFile

from app.common.exceptions import CodeMapException, FileLimitExceededError


MAX_LOCAL_FILE_COUNT = 900
MAX_LOCAL_FILE_BYTES = 5 * 1024 * 1024
MAX_LOCAL_UPLOAD_BYTES = 50 * 1024 * 1024
UPLOAD_MARKER = ".codemap-upload"

IGNORED_DIRECTORIES = {
    ".git",
    ".next",
    ".nuxt",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "target",
    "venv",
}

IGNORED_FILENAMES = {
    ".env",
    ".env.development",
    ".env.local",
    ".env.production",
    ".env.test",
    ".npmrc",
    ".pypirc",
}

_UNSAFE_PATH_CHARS = re.compile(r'[\0-\x1f\x7f<>:"|?*]')


def _sanitize_upload_segment(segment: str) -> str:
    """Normalize one path segment so invalid chars in directories cannot crash writes."""
    sanitized = _UNSAFE_PATH_CHARS.sub("_", segment)
    if not sanitized or sanitized in {".", ".."}:
        raise CodeMapException(400, "INVALID_LOCAL_PATH", "안전하지 않은 폴더 경로가 포함되어 있습니다.")
    return sanitized


def normalize_upload_path(raw_path: str, folder_name: str) -> Path | None:
    """Return a safe repository-relative path, or None for ignored content."""
    raw_path = re.sub(r'^[a-zA-Z]:[/\\\\]*', '', raw_path)
    normalized = raw_path.replace("\\", "/").strip("/")
    parts = list(PurePosixPath(normalized).parts)
    if parts and parts[0] == folder_name:
        parts = parts[1:]

    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise CodeMapException(400, "INVALID_LOCAL_PATH", "안전하지 않은 폴더 경로가 포함되어 있습니다.")
    if any(part in IGNORED_DIRECTORIES for part in parts[:-1]):
        return None

    parts = [_sanitize_upload_segment(part) for part in parts]
    filename = parts[-1]

    if filename in IGNORED_FILENAMES or (filename.startswith(".env.") and filename != ".env.example"):
        return None
    return Path(*parts)


async def save_local_upload(
    files: list[UploadFile],
    relative_paths: list[str],
    folder_name: str,
    destination: Path,
) -> tuple[int, int]:
    """Validate and stream an uploaded directory into an isolated workspace."""
    if not files or len(files) != len(relative_paths):
        raise CodeMapException(400, "INVALID_LOCAL_UPLOAD", "업로드 파일과 경로 정보가 올바르지 않습니다.")
    if len(files) > MAX_LOCAL_FILE_COUNT:
        raise FileLimitExceededError(f"로컬 폴더는 최대 {MAX_LOCAL_FILE_COUNT:,}개 파일까지 분석할 수 있습니다.")

    destination = destination.resolve()
    shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True, exist_ok=True)
    written_paths: set[Path] = set()
    file_count = 0
    total_bytes = 0

    try:
        for upload, raw_path in zip(files, relative_paths, strict=True):
            relative_path = normalize_upload_path(raw_path, folder_name)
            if relative_path is None:
                continue
            if relative_path in written_paths:
                raise CodeMapException(400, "DUPLICATE_LOCAL_PATH", "중복된 파일 경로가 포함되어 있습니다.")

            current = destination / relative_path
            while current != destination:
                if current.is_symlink():
                    raise CodeMapException(400, "SYMLINK_NOT_ALLOWED", "심볼릭 링크는 업로드할 수 없습니다.")
                current = current.parent

            target = (destination / relative_path).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise CodeMapException(400, "INVALID_LOCAL_PATH", "작업 폴더 밖의 경로는 업로드할 수 없습니다.") from exc

            target.parent.mkdir(parents=True, exist_ok=True)
            file_bytes = 0
            with target.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    file_bytes += len(chunk)
                    total_bytes += len(chunk)
                    if file_bytes > MAX_LOCAL_FILE_BYTES:
                        raise FileLimitExceededError(f"파일 하나의 크기는 최대 {MAX_LOCAL_FILE_BYTES // 1024 // 1024}MB입니다.")
                    if total_bytes > MAX_LOCAL_UPLOAD_BYTES:
                        raise FileLimitExceededError(f"로컬 폴더 업로드는 최대 {MAX_LOCAL_UPLOAD_BYTES // 1024 // 1024}MB입니다.")
                    output.write(chunk)

            written_paths.add(relative_path)
            file_count += 1

        if file_count == 0:
            raise CodeMapException(400, "EMPTY_LOCAL_UPLOAD", "분석할 수 있는 파일이 없습니다.")

        (destination / UPLOAD_MARKER).write_text(
            f"files={file_count}\nbytes={total_bytes}\n",
            encoding="utf-8",
        )
        return file_count, total_bytes
    except Exception:
        shutil.rmtree(destination.parent, ignore_errors=True)
        raise
    finally:
        for upload in files:
            await upload.close()
