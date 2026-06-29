"""
DOCS-GEN API 요청/응답 스키마 (DOCS-GEN-API-001, 002, 003, 005)

DOCS_API_SPEC.md 기준 Request/Response DTO를 정의한다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ──────────────────────────────────────────────
# DOCS-GEN-API-005: Markdown DB 저장 요청/응답
# ──────────────────────────────────────────────
class DocSaveRequest(BaseModel):
    '''
    POST /api/gen/docs/{repo_id}/save 요청 본문 (DOCS-GEN-API-005)

    스펙의 camelCase 필드명(jobId)을 alias로 지원하고
    snake_case(job_id)로도 수신할 수 있도록 populate_by_name=True 설정.
    '''

    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(description="저장할 Markdown 가이드북 전문")
    version: int = Field(ge=1, description="가이드북 버전 (1 이상)")
    job_id: UUID = Field(alias="jobId", description="연결된 분석 작업 ID")


class DocSaveData(BaseModel):
    '''POST /api/gen/docs/{repo_id}/save 성공 응답 data 필드'''

    model_config = ConfigDict(populate_by_name=True)

    doc_id: UUID = Field(alias="docId", description="저장된 문서 고유 ID")
    repo_id: UUID = Field(alias="repoId", description="저장소 ID")
    version: int = Field(description="저장된 가이드북 버전")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DocSaveResponse(BaseModel):
    '''POST /api/gen/docs/{repo_id}/save 성공 응답 (201 Created)'''

    code: int = Field(default=201, description="HTTP 상태 코드")
    message: str = Field(default="created", description="처리 결과 메시지")
    data: DocSaveData


# ──────────────────────────────────────────────
# DOCS-GEN-API-002: 가이드북 생성 트리거 요청/응답
# ──────────────────────────────────────────────
class DocTriggerRequest(BaseModel):
    '''
    POST /api/gen/docs/{repo_id} 요청 본문 (DOCS-GEN-API-002)

    force=true일 때 기존 가이드북을 덮어쓰고 재생성한다.
    '''

    force: bool = Field(default=False, description="기존 가이드북 덮어쓰기 여부")
    model: str = Field(default="gpt-4o-mini", description="문서 생성에 사용할 LLM 모델")


class DocTriggerData(BaseModel):
    '''POST /api/gen/docs/{repo_id} 성공 응답 data 필드'''

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    job_id: UUID = Field(alias="jobId", description="문서 생성 작업 ID (분석 작업 ID)")
    repo_id: UUID = Field(alias="repoId", description="저장소 ID")
    status: str = Field(default="docs_queued", description="문서 생성 작업 상태")
    estimated_minutes: int = Field(
        alias="estimatedMinutes",
        default=2,
        description="예상 생성 소요 시간 (분)",
    )


class DocTriggerResponse(BaseModel):
    '''POST /api/gen/docs/{repo_id} 성공 응답 (202 Accepted)'''

    code: int = Field(default=202, description="HTTP 상태 코드")
    message: str = Field(default="accepted", description="처리 결과 메시지")
    data: DocTriggerData


# ──────────────────────────────────────────────
# DOCS-GEN-API-001: 온보딩 가이드북 조회 응답
# ──────────────────────────────────────────────
class DocGetMarkdownData(BaseModel):
    '''GET /api/gen/docs/{repo_id}?format=markdown 응답 data 필드'''

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    repo_id: UUID = Field(alias="repoId", description="저장소 ID")
    repo_name: str = Field(alias="repoName", description="저장소 이름")
    content: str = Field(description="온보딩 가이드북 Markdown 전문")
    generated_at: datetime = Field(
        alias="generatedAt", description="가이드북 생성 시각"
    )
    version: int = Field(description="가이드북 버전 번호")


class DocGetMarkdownResponse(BaseModel):
    '''GET /api/gen/docs/{repo_id}?format=markdown 성공 응답 (200 OK)'''

    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="처리 결과 메시지")
    data: DocGetMarkdownData


class DocReadingOrderItem(BaseModel):
    """DOCS_API_SPEC readingOrder item."""

    rank: int = Field(description="Reading priority, starting at 1")
    path: str = Field(description="File or folder path")
    reason: str = Field(default="", description="Reason to read this item")


class DocDangerFileItem(BaseModel):
    """DOCS_API_SPEC dangerFiles item."""

    path: str = Field(description="Risky file path")
    reason: str = Field(default="", description="Reason this file needs attention")


class DocFolderSummaryItem(BaseModel):
    """DOCS_API_SPEC folderSummaries item."""

    path: str = Field(description="Folder path")
    description: str = Field(default="", description="Folder description")


class DocGetJsonData(BaseModel):
    '''GET /api/gen/docs/{repo_id}?format=json 응답 data 필드'''

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    repo_id: UUID = Field(alias="repoId", description="저장소 ID")
    repo_name: str = Field(alias="repoName", description="저장소 이름")
    summary: str | None = Field(default=None, description="프로젝트 요약 정보")
    stack: list[str] = Field(default_factory=list, description="기술 스택 목록")
    reading_order: list[DocReadingOrderItem] = Field(
        alias="readingOrder", default_factory=list, description="추천 파일 읽기 순서"
    )
    danger_files: list[DocDangerFileItem] = Field(
        alias="dangerFiles", default_factory=list, description="주의/위험 파일 목록"
    )
    core_flow: str | None = Field(alias="coreFlow", default=None, description="핵심 실행 플로우")
    folder_summaries: list[DocFolderSummaryItem] = Field(
        alias="folderSummaries", default_factory=list, description="폴더 구조 요약"
    )
    generated_at: datetime = Field(
        alias="generatedAt", description="가이드북 생성 시각"
    )
    version: int = Field(description="가이드북 버전 번호")


class DocGetJsonResponse(BaseModel):
    '''GET /api/gen/docs/{repo_id}?format=json 성공 응답 (200 OK)'''

    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="처리 결과 메시지")
    data: DocGetJsonData


# ──────────────────────────────────────────────
# DOCS-GEN-API-003: 가이드북 재생성 요청/응답
# ──────────────────────────────────────────────
class DocRebuildRequest(BaseModel):
    '''
    PUT /api/gen/docs/{repo_id} 요청 본문 (DOCS-GEN-API-003)

    기존 가이드북을 소프트 삭제한 뒤 최신 분석 기반으로 재생성한다.
    model과 reason은 선택 파라미터다.
    '''

    model: str = Field(
        default="gpt-4o-mini",
        description="재생성에 사용할 LLM 모델",
    )
    reason: str | None = Field(
        default=None,
        description="재생성 요청 사유 (로그 기록용)",
    )


class DocRebuildData(BaseModel):
    '''PUT /api/gen/docs/{repo_id} 성공 응답 data 필드'''

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    job_id: UUID = Field(alias="jobId", description="재생성 작업 ID")
    repo_id: UUID = Field(alias="repoId", description="저장소 ID")
    previous_version: int = Field(
        alias="previousVersion", description="소프트 삭제된 기존 가이드북 버전"
    )
    new_version: int = Field(
        alias="newVersion", description="생성될 새 가이드북 버전"
    )


class DocRebuildResponse(BaseModel):
    '''PUT /api/gen/docs/{repo_id} 성공 응답 (202 Accepted)'''

    code: int = Field(default=202, description="HTTP 상태 코드")
    message: str = Field(default="accepted", description="처리 결과 메시지")
    data: DocRebuildData
