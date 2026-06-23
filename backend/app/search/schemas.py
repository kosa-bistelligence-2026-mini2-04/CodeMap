from typing import List, Optional
from pydantic import BaseModel, Field

# ──────────────────────────────────────────────
# AGENT-SEARCH-API-002 파일/디렉토리 조회 스키마
# ──────────────────────────────────────────────
class DirectoryItem(BaseModel):
    """디렉토리 내 개별 항목(파일/폴더) 정보"""
    name: str = Field(..., description="파일 또는 폴더명")
    path: str = Field(..., description="저장소 루트 기준 상대 경로")
    type: str = Field(..., description="'file' 또는 'directory'")
    size: Optional[int] = Field(None, description="파일 크기 (바이트), 디렉토리인 경우 None")

class DirectoryReadData(BaseModel):
    """디렉토리 조회 성공 응답 데이터"""
    type: str = Field("directory", description="항상 'directory'")
    path: str = Field(..., description="조회한 디렉토리의 저장소 내 상대 경로")
    items: List[DirectoryItem] = Field(..., description="디렉토리 내 파일 및 하위 폴더 목록")

class DirectoryReadResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: DirectoryReadData

class FileReadData(BaseModel):
    """파일 조회 성공 응답 데이터"""
    type: str = Field("file", description="항상 'file'")
    path: str = Field(..., description="조회한 파일의 저장소 내 상대 경로")
    size: int = Field(..., description="파일 전체 크기 (바이트)")
    totalLines: int = Field(..., description="파일의 전체 라인 수")
    content: str = Field(..., description="요청된 구간의 파일 내용")
    startLine: Optional[int] = Field(None, description="조회 시작 라인 번호")
    endLine: Optional[int] = Field(None, description="조회 종료 라인 번호")

class FileReadResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: FileReadData
