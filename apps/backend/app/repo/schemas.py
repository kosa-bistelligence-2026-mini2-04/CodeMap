from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiResponse(BaseModel):
    code: int
    message: str
    data: Any


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: str | None = None


class ApiErrorResponse(BaseModel):
    error: ErrorBody


class RepoValidateRequest(BaseModel):
    repo_url: str = Field(..., alias="repoUrl")

    model_config = ConfigDict(populate_by_name=True)


class RepoValidateData(BaseModel):
    valid: bool
    repo_name: str = Field(..., alias="repoName")
    owner: str
    default_branch: str = Field(..., alias="defaultBranch")
    is_private: bool = Field(False, alias="isPrivate")

    model_config = ConfigDict(populate_by_name=True)
