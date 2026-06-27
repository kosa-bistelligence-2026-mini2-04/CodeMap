"""
DOCS-GEN API 요청/응답 스키마 (DOCS-GEN-API-002, 005)

DOCS_API_SPEC.md 기준 Request/Response DTO를 정의한다.
"""

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
