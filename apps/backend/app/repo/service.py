import json
import re
from dataclasses import dataclass
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import Depends


GITHUB_REPO_PATTERN = re.compile(
    r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$"
)


@dataclass
class RepoIdentity:
    repo_url: str
    owner: str
    repo_name: str
    default_branch: str
    is_private: bool = False


class RepoApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        detail: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class RepoService:
    async def validate_github_url(self, repo_url: str) -> RepoIdentity:
        match = GITHUB_REPO_PATTERN.match(repo_url.strip())
        if match is None:
            raise RepoApiError(
                status_code=400,
                code="INVALID_REPO_URL",
                message="GitHub URL 형식이 올바르지 않습니다.",
                detail="Expected https://github.com/{owner}/{repo}",
            )

        owner = match.group("owner")
        repo_name = match.group("repo")
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

        try:
            request = Request(api_url, headers={"User-Agent": "CodeMap"})
            with urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                raise RepoApiError(
                    status_code=404,
                    code="REPOSITORY_NOT_FOUND",
                    message="저장소가 없거나 접근할 수 없습니다.",
                    detail=str(exc),
                ) from exc
            raise RepoApiError(
                status_code=500,
                code="GITHUB_API_ERROR",
                message="GitHub API 호출 중 오류가 발생했습니다.",
                detail=str(exc),
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RepoApiError(
                status_code=500,
                code="GITHUB_API_ERROR",
                message="GitHub API 호출 중 오류가 발생했습니다.",
                detail=str(exc),
            ) from exc

        return RepoIdentity(
            repo_url=repo_url,
            owner=owner,
            repo_name=repo_name,
            default_branch=payload.get("default_branch", "main"),
            is_private=bool(payload.get("private", False)),
        )


RepoServiceDep = Annotated[RepoService, Depends(RepoService)]
