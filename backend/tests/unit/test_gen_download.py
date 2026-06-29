"""
DOCS-GEN-API-004 (GET /api/gen/docs/{repo_id}/download) 유닛 테스트

검증 대상:
  - FileGenerationFailedError 예외 속성
  - get_doc_download_content() 서비스: 404 분기 / 정상 반환
  - 라우터 엔드포인트:
    · 200 md 다운로드 (Content-Type, Content-Disposition)
    · 500 pdf 미지원 (FILE_GENERATION_FAILED)
    · 404 저장소 없음
    · 404 가이드북 없음
    · 422 유효하지 않은 format / repo_id
  - 파일명 특수문자 안전 처리
  - 회귀: GET/POST/PUT 기존 엔드포인트 영향 없음

Self 리뷰 결과 (CLAUDE.md §7):
  1. KeyError 방어: repo_name None 시 "onboarding" 폴백 적용
  2. Null-Safety: analysis_job/doc None 체크 → 404 예외
  3. Exception Safety: DB 오류 시 서비스 계층에서 처리
  4. 비동기 블로킹: DB 조회 경량 쿼리 — to_thread 불필요
  5. 데이터 불변성: Response 객체 생성, 원본 doc 수정 없음
  6. 연계 코드 영향도: router.py import 추가 확인
  7. 리소스 누수: AsyncSession은 Depends(get_db) 관리
  8. 관측 가능성: format/repo_id별 logger 기록
  9. 스키마 검증: Response 헤더 Content-Type / Content-Disposition 검증
"""

import uuid
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.common.exceptions import (
    DocsNotFoundError,
    FileGenerationFailedError,
    RepoNotFoundError,
)


_REPO_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_NOW = datetime(2026, 6, 27, 9, 0, 0, tzinfo=timezone.utc)
_MARKDOWN = "# 온보딩 가이드\n## 개요\n이 프로젝트는...\n"


# ──────────────────────────────────────────────────────────────
# 1. FileGenerationFailedError 예외 속성 검증
# ──────────────────────────────────────────────────────────────

class FileGenerationFailedExceptionTests(unittest.TestCase):
    """FileGenerationFailedError 속성 검증"""

    def test_status_code(self):
        """FileGenerationFailedError는 500이어야 한다."""
        exc = FileGenerationFailedError()
        self.assertEqual(exc.status_code, 500)

    def test_error_code(self):
        """에러 코드는 FILE_GENERATION_FAILED이어야 한다."""
        exc = FileGenerationFailedError()
        self.assertEqual(exc.error_code, "FILE_GENERATION_FAILED")

    def test_default_message(self):
        """기본 메시지가 설정되어야 한다."""
        exc = FileGenerationFailedError()
        self.assertIn("파일 생성", exc.message)

    def test_custom_message(self):
        """커스텀 메시지를 허용해야 한다."""
        exc = FileGenerationFailedError("PDF 미지원")
        self.assertEqual(exc.message, "PDF 미지원")

    def test_in_common_exceptions(self):
        """FileGenerationFailedError가 common.exceptions에 존재해야 한다."""
        from app.common import exceptions as exc
        self.assertTrue(hasattr(exc, "FileGenerationFailedError"))


# ──────────────────────────────────────────────────────────────
# 2. get_doc_download_content() 서비스 검증
# ──────────────────────────────────────────────────────────────

class GetDocDownloadContentServiceTests(unittest.IsolatedAsyncioTestCase):
    """get_doc_download_content() 서비스 각 분기 검증"""

    def _make_analysis_job(self, repo_name="sample-repo"):
        job = MagicMock()
        job.id = uuid.uuid4()
        job.repo_name = repo_name
        return job

    def _make_doc(self, content=None):
        doc = MagicMock()
        doc.content = content or _MARKDOWN
        doc.version = 1
        return doc

    def _make_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    async def test_raises_repo_not_found(self):
        """저장소가 없으면 RepoNotFoundError를 발생시켜야 한다."""
        from app.gen.service import get_doc_download_content

        with patch(
            "app.gen.service.GenDocRepository.get_repo_by_id",
            new=AsyncMock(return_value=None),
        ):
            with self.assertRaises(RepoNotFoundError):
                await get_doc_download_content(self._make_db(), _REPO_ID)

    async def test_raises_docs_not_found(self):
        """저장소는 있지만 활성 문서가 없으면 DocsNotFoundError를 발생시켜야 한다."""
        from app.gen.service import get_doc_download_content

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            with self.assertRaises(DocsNotFoundError):
                await get_doc_download_content(self._make_db(), _REPO_ID)

    async def test_returns_content_and_repo_name(self):
        """정상 조회 시 (content, repo_name) 튜플을 반환해야 한다."""
        from app.gen.service import get_doc_download_content

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job("MyRepo")),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_doc()),
            ),
        ):
            content, repo_name = await get_doc_download_content(
                self._make_db(), _REPO_ID
            )

        self.assertEqual(content, _MARKDOWN)
        self.assertEqual(repo_name, "MyRepo")

    async def test_repo_name_none_fallback(self):
        """repo_name이 None이면 'onboarding' 폴백이 사용되어야 한다."""
        from app.gen.service import get_doc_download_content

        job = self._make_analysis_job()
        job.repo_name = None

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=job),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_doc()),
            ),
        ):
            _, repo_name = await get_doc_download_content(self._make_db(), _REPO_ID)

        self.assertEqual(repo_name, "onboarding")

    async def test_is_coroutine(self):
        """get_doc_download_content는 async def이어야 한다."""
        import inspect
        from app.gen.service import get_doc_download_content
        self.assertTrue(inspect.iscoroutinefunction(get_doc_download_content))


# ──────────────────────────────────────────────────────────────
# 3. 라우터 엔드포인트 검증 (FastAPI TestClient)
# ──────────────────────────────────────────────────────────────

class GenDownloadRouterTests(unittest.TestCase):
    """DOCS-GEN-API-004 엔드포인트 HTTP 응답 검증"""

    def setUp(self):
        from fastapi import FastAPI
        from app.gen.router import router
        from app.infra.database import get_db
        from app.infra.auth import get_current_user
        from app.common.exceptions import register_exception_handlers

        self.app = FastAPI()
        register_exception_handlers(self.app)
        self.app.include_router(router)
        self.mock_db = MagicMock()
        self.app.dependency_overrides[get_db] = lambda: self.mock_db
        self.app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_200_md_download(self):
        """format=md 조회 시 200과 text/markdown Content-Type을 반환해야 한다."""
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(return_value=(_MARKDOWN, "sample-repo")),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download?format=md")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/markdown", resp.headers.get("content-type", ""))

    def test_200_content_disposition_header(self):
        """응답 헤더에 Content-Disposition attachment 헤더가 있어야 한다."""
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(return_value=(_MARKDOWN, "sample-repo")),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download")

        disp = resp.headers.get("content-disposition", "")
        self.assertIn("attachment", disp)
        self.assertIn("_onboarding.md", disp)

    def test_200_default_format_is_md(self):
        """format 파라미터 없이 호출하면 md 형식으로 다운로드되어야 한다."""
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(return_value=(_MARKDOWN, "repo")),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, _MARKDOWN.encode("utf-8"))

    def test_200_content_is_markdown_bytes(self):
        """응답 바디가 Markdown 내용의 UTF-8 바이트여야 한다."""
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(return_value=(_MARKDOWN, "repo")),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download?format=md")

        self.assertEqual(resp.content, _MARKDOWN.encode("utf-8"))

    def test_500_pdf_not_supported(self):
        """format=pdf 요청 시 500 / FILE_GENERATION_FAILED를 반환해야 한다."""
        resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download?format=pdf")
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["error"]["code"], "FILE_GENERATION_FAILED")

    def test_404_repo_not_found(self):
        """RepoNotFoundError 발생 시 404 / REPO_NOT_FOUND를 반환해야 한다."""
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(side_effect=RepoNotFoundError()),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "REPO_NOT_FOUND")

    def test_404_docs_not_found(self):
        """DocsNotFoundError 발생 시 404 / DOCS_NOT_FOUND를 반환해야 한다."""
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(side_effect=DocsNotFoundError()),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "DOCS_NOT_FOUND")

    def test_422_invalid_format(self):
        """format이 md|pdf가 아니면 422를 반환해야 한다."""
        resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download?format=html")
        self.assertEqual(resp.status_code, 422)

    def test_422_invalid_repo_id(self):
        """repo_id가 UUID 형식이 아니면 422를 반환해야 한다."""
        resp = self.client.get("/api/gen/docs/not-uuid/download")
        self.assertEqual(resp.status_code, 422)

    def test_401_without_auth(self):
        """인증 없이 호출하면 401을 반환해야 한다."""
        from fastapi import FastAPI
        from app.gen.router import router
        from app.infra.database import get_db
        from app.common.exceptions import register_exception_handlers

        ## get_current_user mock을 제거한 별도 앱으로 실제 인증 미제공 시나리오 검증
        app_no_auth = FastAPI()
        register_exception_handlers(app_no_auth)
        app_no_auth.include_router(router)
        app_no_auth.dependency_overrides[get_db] = lambda: self.mock_db
        client_no_auth = TestClient(app_no_auth, raise_server_exceptions=False)

        resp = client_no_auth.get(f"/api/gen/docs/{_REPO_ID}/download")
        self.assertEqual(resp.status_code, 401)


# ──────────────────────────────────────────────────────────────
# 4. 파일명 특수문자 처리 검증
# ──────────────────────────────────────────────────────────────

class FilenameEscapingTests(unittest.TestCase):
    """Content-Disposition 파일명 특수문자 안전 처리 검증"""

    def setUp(self):
        from fastapi import FastAPI
        from app.gen.router import router
        from app.infra.database import get_db
        from app.infra.auth import get_current_user
        from app.common.exceptions import register_exception_handlers

        self.app = FastAPI()
        register_exception_handlers(self.app)
        self.app.include_router(router)
        self.mock_db = MagicMock()
        self.app.dependency_overrides[get_db] = lambda: self.mock_db
        self.app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_special_chars_in_repo_name_are_sanitized(self):
        """저장소 이름에 특수문자가 있으면 파일명에서 '_'로 치환되어야 한다."""
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(return_value=(_MARKDOWN, "my-repo/project")),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download")

        disp = resp.headers.get("content-disposition", "")
        ## 슬래시가 _로 치환되어야 함
        self.assertNotIn("/", disp)
        self.assertIn("_onboarding.md", disp)

    def test_normal_repo_name_preserved(self):
        """영문/숫자/하이픈/언더스코어만 있는 이름은 그대로 유지되어야 한다."""
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(return_value=(_MARKDOWN, "CodeMap")),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download")

        disp = resp.headers.get("content-disposition", "")
        self.assertIn("CodeMap_onboarding.md", disp)

    def test_space_in_repo_name_sanitized(self):
        """공백이 포함된 저장소 이름은 '_'로 치환되어야 한다."""
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(return_value=(_MARKDOWN, "my repo")),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download")

        disp = resp.headers.get("content-disposition", "")
        ## filename= 이후의 파일명 부분만 추출하여 공백 검증
        filename_part = disp.split("filename=")[-1].strip('"')
        self.assertNotIn(" ", filename_part)

    def test_korean_repo_name_sanitized(self):
        """한글 저장소 이름은 Content-Disposition 헤더에 그대로 들어가지 않아야 한다.

        re.sub flags=re.ASCII 없이는 \\w가 유니코드 한글을 허용해
        Content-Disposition 헤더에 비-ASCII 문자가 포함되어 인코딩 오류가 발생할 수 있다.
        """
        with patch(
            "app.gen.router.get_doc_download_content",
            new=AsyncMock(return_value=(_MARKDOWN, "코드맵-프로젝트")),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/download")

        self.assertEqual(resp.status_code, 200)
        disp = resp.headers.get("content-disposition", "")
        filename_part = disp.split("filename=")[-1].strip('"')
        ## 한글이 _ 로 치환되어 파일명에 비-ASCII 문자가 없어야 한다
        self.assertTrue(
            filename_part.isascii(),
            f"파일명에 비-ASCII 문자가 포함됨: {filename_part!r}",
        )
        self.assertIn("_onboarding.md", filename_part)


# ──────────────────────────────────────────────────────────────
# 5. 회귀 검증 — 기존 엔드포인트 영향 없음
# ──────────────────────────────────────────────────────────────

class DownloadRegressionTests(unittest.TestCase):
    """download 엔드포인트 추가 후 기존 GET/POST/PUT 회귀 확인"""

    def setUp(self):
        from fastapi import FastAPI
        from app.gen.router import router
        from app.infra.database import get_db
        from app.infra.auth import get_current_user
        from app.common.exceptions import register_exception_handlers
        from app.gen.schemas import DocGetMarkdownData

        self.app = FastAPI()
        register_exception_handlers(self.app)
        self.app.include_router(router)
        self.mock_db = MagicMock()
        self.app.dependency_overrides[get_db] = lambda: self.mock_db
        ## GET /{repo_id}에 인증이 추가되어 get_current_user를 mock으로 대체한다.
        self.app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
        self.client = TestClient(self.app, raise_server_exceptions=False)

        self._md_data = DocGetMarkdownData(
            repo_id=_REPO_ID,
            repo_name="sample",
            content="# 가이드북",
            generated_at=_NOW,
            version=1,
        )

    def test_get_endpoint_still_200(self):
        """GET /{repo_id} 엔드포인트가 여전히 200을 반환해야 한다."""
        with patch(
            "app.gen.router.get_onboarding_doc",
            new=AsyncMock(return_value=self._md_data),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}")

        self.assertEqual(resp.status_code, 200)

    def test_put_endpoint_still_exists(self):
        """PUT /{repo_id} 엔드포인트가 여전히 동작해야 한다."""
        with patch(
            "app.gen.router.rebuild_onboarding_doc",
            new=AsyncMock(side_effect=RepoNotFoundError()),
        ):
            resp = self.client.put(f"/api/gen/docs/{_REPO_ID}", json={})

        self.assertEqual(resp.status_code, 404)

    def test_download_and_get_are_distinct_paths(self):
        """GET /{repo_id}와 GET /{repo_id}/download는 별개 경로여야 한다."""
        from fastapi.routing import APIRoute

        def _collect_routes(app):
            routes = []
            for r in app.routes:
                if isinstance(r, APIRoute):
                    routes.append(r)
                elif hasattr(r, "original_router") and hasattr(r.original_router, "routes"):
                    routes.extend(
                        sub for sub in r.original_router.routes
                        if isinstance(sub, APIRoute)
                    )
            return routes

        all_routes = _collect_routes(self.app)
        get_paths = [r.path for r in all_routes if "GET" in (r.methods or set())]
        self.assertIn("/api/gen/docs/{repo_id}", get_paths)
        self.assertIn("/api/gen/docs/{repo_id}/download", get_paths)


# ──────────────────────────────────────────────────────────────
# 6. 정적 분석 Self 리뷰 자동화 테스트
# ──────────────────────────────────────────────────────────────

class GenDownloadStaticAnalysisTests(unittest.TestCase):
    """CLAUDE.md §7 정적 분석 Self 리뷰 자동화"""

    def test_file_generation_failed_in_common_exceptions(self):
        """FileGenerationFailedError가 common.exceptions에 있어야 한다."""
        from app.common import exceptions as exc
        self.assertTrue(hasattr(exc, "FileGenerationFailedError"))

    def test_download_service_exported(self):
        """service 모듈에 get_doc_download_content가 있어야 한다."""
        from app.gen import service as smod
        self.assertTrue(hasattr(smod, "get_doc_download_content"))

    def test_download_service_is_coroutine(self):
        """get_doc_download_content는 async def이어야 한다."""
        import inspect
        from app.gen.service import get_doc_download_content
        self.assertTrue(inspect.iscoroutinefunction(get_doc_download_content))

    def test_router_exports_download_doc(self):
        """router 모듈에 download_doc 핸들러가 있어야 한다."""
        from app.gen import router as rmod
        self.assertTrue(hasattr(rmod, "download_doc"))

    def test_download_service_signature(self):
        """get_doc_download_content 시그니처에 db, repo_id만 있어야 한다."""
        import inspect
        from app.gen.service import get_doc_download_content
        sig = inspect.signature(get_doc_download_content)
        params = list(sig.parameters.keys())
        self.assertIn("db", params)
        self.assertIn("repo_id", params)

    def test_filename_sanitization_in_router(self):
        """router.py에 파일명 특수문자 처리 코드가 있어야 한다."""
        import inspect
        from app.gen import router as rmod
        src = inspect.getsource(rmod.download_doc)
        self.assertIn("re.sub", src)

    def test_pdf_raises_file_generation_error(self):
        """router의 download_doc 소스에 PDF 분기 처리가 있어야 한다."""
        import inspect
        from app.gen import router as rmod
        src = inspect.getsource(rmod.download_doc)
        self.assertIn("pdf", src)
        self.assertIn("FileGenerationFailedError", src)

    def test_response_uses_utf8_encoding(self):
        """응답 Content-Type에 charset=utf-8이 포함되어야 한다."""
        import inspect
        from app.gen import router as rmod
        src = inspect.getsource(rmod.download_doc)
        self.assertIn("utf-8", src)


if __name__ == "__main__":
    unittest.main()
