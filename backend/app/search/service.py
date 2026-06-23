import os
import itertools
from uuid import UUID
from typing import Union, Optional

from app.core.config import get_settings
from app.core.exceptions import (
    TargetFileNotFoundError,
    InvalidPathError,
    FileTooLargeError,
    FileReadFailedError,
)
from app.search.schemas import (
    DirectoryItem,
    DirectoryReadData,
    FileReadData,
)

settings = get_settings()

EXCLUDE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist", ".idea", ".vscode"}
MAX_FILE_SIZE = 5 * 1024 * 1024


def read_file_or_directory(repo_id: UUID, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Union[DirectoryReadData, FileReadData]:
    """
    저장소 내 특정 파일이나 디렉토리를 조회한다.
    - Symlink를 통한 디렉토리 탈출 방어
    - 파일 조회 시 용량 제한(5MB)
    - itertools.islice를 활용한 특정 라인 범위 스트리밍 추출
    """
    base_dir = os.path.realpath(os.path.join(settings.CLONE_BASE_DIR, str(repo_id), "repo"))
    if not os.path.exists(base_dir):
        raise TargetFileNotFoundError("저장소 디렉토리를 찾을 수 없습니다.")

    target_path = os.path.realpath(os.path.join(base_dir, path.lstrip('/\\')))
    
    # Path Traversal & Symlink 방어
    if os.path.commonpath([base_dir, target_path]) != base_dir:
        raise InvalidPathError("허용되지 않은 경로 접근입니다.")
        
    if not os.path.exists(target_path):
        raise TargetFileNotFoundError("대상 파일 또는 디렉토리를 찾을 수 없습니다.")

    if os.path.isdir(target_path):
        items = []
        try:
            for item in os.listdir(target_path):
                if item in EXCLUDE_DIRS:
                    continue
                    
                item_path = os.path.join(target_path, item)
                is_dir = os.path.isdir(item_path)
                
                size = None
                if not is_dir:
                    try:
                        size = os.path.getsize(item_path)
                    except OSError:
                        pass
                        
                rel_path = os.path.relpath(item_path, base_dir).replace("\\", "/")
                items.append(DirectoryItem(
                    name=item,
                    path=rel_path,
                    type="directory" if is_dir else "file",
                    size=size
                ))
        except OSError:
            raise FileReadFailedError("디렉토리를 읽는 중 오류가 발생했습니다.")
            
        rel_target_path = os.path.relpath(target_path, base_dir).replace("\\", "/")
        if rel_target_path == ".":
            rel_target_path = ""
            
        return DirectoryReadData(
            path=rel_target_path,
            items=items
        )

    else:
        # 파일 조회
        try:
            file_size = os.path.getsize(target_path)
        except OSError:
            raise FileReadFailedError("파일 크기를 확인할 수 없습니다.")
            
        if file_size > MAX_FILE_SIZE:
            raise FileTooLargeError(f"파일 크기가 {MAX_FILE_SIZE} bytes를 초과합니다.")

        content_lines = []
        total_lines = 0
        try:
            with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
                for _ in f:
                    total_lines += 1
                
                f.seek(0)
                
                if start_line is not None and end_line is not None:
                    s_idx = max(0, start_line - 1)
                    e_idx = max(s_idx, end_line)
                    
                    for line in itertools.islice(f, s_idx, e_idx):
                        content_lines.append(line.rstrip('\n\r'))
                else:
                    for line in f:
                        content_lines.append(line.rstrip('\n\r'))
        except Exception:
            raise FileReadFailedError("파일을 읽거나 파싱하는 중 오류가 발생했습니다.")
            
        rel_target_path = os.path.relpath(target_path, base_dir).replace("\\", "/")
        
        return FileReadData(
            path=rel_target_path,
            size=file_size,
            totalLines=total_lines,
            content="\n".join(content_lines),
            startLine=start_line,
            endLine=end_line
        )
