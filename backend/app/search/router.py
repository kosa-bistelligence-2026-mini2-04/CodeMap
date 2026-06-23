from fastapi import APIRouter, Query
from uuid import UUID
from typing import Union

from app.search.schemas import DirectoryReadResponse, FileReadResponse
from app.search.service import read_file_or_directory

router = APIRouter(
    prefix="/search",
    tags=["Search"]
)

@router.get("/{repo_id}/file", response_model=Union[DirectoryReadResponse, FileReadResponse], summary="파일 및 디렉토리 조회")
def read_file_endpoint(
    repo_id: UUID,
    path: str = Query(..., description="조회할 대상의 저장소 내 상대 경로"),
    startLine: int = Query(None, description="파일 조회 시 시작 라인 번호 (1-indexed)"),
    endLine: int = Query(None, description="파일 조회 시 종료 라인 번호 (1-indexed)")
):
    """
    저장소 내 특정 파일이나 디렉토리 내용을 조회한다.
    디렉토리일 경우 항목 목록을, 파일일 경우 (선택적으로 범위 내의) 텍스트를 반환한다.
    """
    data = read_file_or_directory(repo_id, path, start_line=startLine, end_line=endLine)
    if getattr(data, "type", "") == "directory":
        return DirectoryReadResponse(data=data)
    else:
        return FileReadResponse(data=data)
