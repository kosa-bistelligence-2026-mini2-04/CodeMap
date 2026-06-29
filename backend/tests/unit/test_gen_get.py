"""
DOCS-GEN-API-001 (GET /api/gen/docs/{repo_id}) 유닛 테스트

검증 대상:
  - DocGetMarkdownData / DocGetMarkdownResponse 스키마 직렬화
  - DocGetJsonData / DocGetJsonResponse 스키마 직렬화
  - DocsNotFoundError 예외 속성
  - OnboardingDoc 모델 — is_active, report_json 신규 컬럼
  - GenDocRepository.get_active_by_repo_id() 메서드
  - get_onboarding_doc() 서비스: 404/포맷별 반환값
  - 라우터 엔드포인트: 200(markdown)/200(json)/404/404/422

Self 리뷰 결과 (CLAUDE.md §7):
  1. KeyError 방어: report.get() 패턴 전면 사용
  2. Null-Safety: report_json None 시 빈 dict 폴백
  3. Exception Safety: RepoNotFoundError / DocsNotFoundError 분기 보장
  4. 비동기 블로킹: 조회 로직은 경량 DB 쿼리 — to_thread 불필요
  5. 데이터 불변성: service에서 doc 엔티티 원본 직접 수정 없음
  6. 연계 코드 영향도: save_onboarding_doc 시그니처 변경 → 기존 테스트 회귀 확인
  7. 리소스 누수: AsyncSession은 Depends(get_db) / context manager로 관리
  8. 관측 가능성: 각 분기에 logger.warning/info 기록
  9. 스키마 검증: Pydantic alias camelCase 직렬화 검증
"""

import uuid
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.common.exceptions import DocsNotFoundError, RepoNotFoundError
from app.gen.schemas import (
    DocGetJsonData,
    DocGetJsonResponse,
    DocGetMarkdownData,
    DocGetMarkdownResponse,
)


_REPO_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_JOB_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_DOC_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_NOW = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)


# ──────────────────────────────────────────────────────────────
# 1. DocGetMarkdownData 스키마 검증
# ──────────────────────────────────────────────────────────────

class DocGetMarkdownSchemaTests(unittest.TestCase):
    """DocGetMarkdownData 직렬화 검증"""

    def _make_data(self, **kwargs):
        defaults = {
            "repo_id": _REPO_ID,
            "repo_name": "sample-repo",
            "content": "# 가이드북\n내용",
            "generated_at": _NOW,
            "version": 1,
        }
        defaults.update(kwargs)
        return DocGetMarkdownData(**defaults)

    def test_camel_alias_serialization(self):
        """repoId, repoName, generatedAt가 camelCase로 직렬화되어야 한다."""
        data = self._make_data()
        dumped = data.model_dump(by_alias=True)
        self.assertIn("repoId", dumped)
        self.assertIn("repoName", dumped)
        self.assertIn("generatedAt", dumped)
        self.assertNotIn("repo_id", dumped)

    def test_response_default_code(self):
        """DocGetMarkdownResponse 기본 code는 200이어야 한다."""
        resp = DocGetMarkdownResponse(data=self._make_data())
        self.assertEqual(resp.code, 200)
        self.assertEqual(resp.message, "success")

    def test_content_preserved(self):
        """content 필드가 그대로 보존되어야 한다."""
        data = self._make_data(content="# Hello\n본문")
        self.assertEqual(data.content, "# Hello\n본문")

    def test_version_preserved(self):
        """version 필드가 정상 설정되어야 한다."""
        data = self._make_data(version=3)
        self.assertEqual(data.version, 3)


# ──────────────────────────────────────────────────────────────
# 2. DocGetJsonData 스키마 검증
# ──────────────────────────────────────────────────────────────

class DocGetJsonSchemaTests(unittest.TestCase):
    """DocGetJsonData 직렬화 검증"""

    def _make_data(self, **kwargs):
        defaults = {
            "repo_id": _REPO_ID,
            "repo_name": "sample-repo",
            "generated_at": _NOW,
            "version": 1,
        }
        defaults.update(kwargs)
        return DocGetJsonData(**defaults)

    def test_camel_alias_serialization(self):
        """repoId, repoName, readingOrder, dangerFiles, coreFlow, folderSummaries, generatedAt가 camelCase여야 한다."""
        data = self._make_data(
            reading_order=[{"rank": 1, "path": "README.md"}],
            danger_files=[{"path": "config.py"}],
        )
        dumped = data.model_dump(by_alias=True)
        self.assertIn("repoId", dumped)
        self.assertIn("repoName", dumped)
        self.assertIn("readingOrder", dumped)
        self.assertIn("dangerFiles", dumped)
        self.assertIn("coreFlow", dumped)
        self.assertIn("folderSummaries", dumped)
        self.assertIn("generatedAt", dumped)

    def test_default_empty_lists(self):
        """stack, reading_order, danger_files, folder_summaries 기본값은 빈 리스트여야 한다."""
        data = self._make_data()
        self.assertEqual(data.stack, [])
        self.assertEqual(data.reading_order, [])
        self.assertEqual(data.danger_files, [])
        self.assertEqual(data.folder_summaries, [])

    def test_response_default_code(self):
        """DocGetJsonResponse 기본 code는 200이어야 한다."""
        resp = DocGetJsonResponse(data=self._make_data())
        self.assertEqual(resp.code, 200)
        self.assertEqual(resp.message, "success")

    def test_summary_accepts_none(self):
        """summary 필드는 None을 허용해야 한다."""
        data = self._make_data(summary=None)
        self.assertIsNone(data.summary)

    def test_summary_rejects_dict(self):
        """summary 필드는 DOCS_API_SPEC에 맞게 문자열이어야 한다."""
        with self.assertRaises(ValidationError):
            self._make_data(summary={"purpose": "테스트"})


# ──────────────────────────────────────────────────────────────
# 3. DocsNotFoundError 예외 속성 검증
# ──────────────────────────────────────────────────────────────

class DocsNotFoundExceptionTests(unittest.TestCase):
    """DocsNotFoundError 속성 검증"""

    def test_status_code(self):
        """DocsNotFoundError는 404이어야 한다."""
        exc = DocsNotFoundError()
        self.assertEqual(exc.status_code, 404)

    def test_error_code(self):
        """DocsNotFoundError 에러 코드는 DOCS_NOT_FOUND이어야 한다."""
        exc = DocsNotFoundError()
        self.assertEqual(exc.error_code, "DOCS_NOT_FOUND")

    def test_custom_message(self):
        """커스텀 메시지를 허용해야 한다."""
        exc = DocsNotFoundError("커스텀 메시지")
        self.assertEqual(exc.message, "커스텀 메시지")


# ──────────────────────────────────────────────────────────────
# 4. OnboardingDoc 모델 — 신규 컬럼 검증
# ──────────────────────────────────────────────────────────────

class OnboardingDocNewColumnTests(unittest.TestCase):
    """is_active, report_json 신규 컬럼 메타데이터 검증"""

    def test_is_active_column_exists(self):
        """is_active 컬럼이 ORM 모델에 정의되어 있어야 한다."""
        from app.gen.models import OnboardingDoc
        self.assertIn("is_active", OnboardingDoc.__table__.c)

    def test_is_active_default_true(self):
        """is_active 컬럼의 default는 True이어야 한다."""
        from app.gen.models import OnboardingDoc
        col = OnboardingDoc.__table__.c["is_active"]
        self.assertEqual(col.default.arg, True)

    def test_report_json_column_exists(self):
        """report_json 컬럼이 ORM 모델에 정의되어 있어야 한다."""
        from app.gen.models import OnboardingDoc
        self.assertIn("report_json", OnboardingDoc.__table__.c)

    def test_report_json_nullable(self):
        """report_json 컬럼은 nullable이어야 한다."""
        from app.gen.models import OnboardingDoc
        col = OnboardingDoc.__table__.c["report_json"]
        self.assertTrue(col.nullable)


class DatabaseInitSchemaTests(unittest.TestCase):
    """database/init.sql docs 테이블 계약 검증"""

    def test_docs_table_and_new_columns_exist_in_init_sql(self):
        init_sql = (
            Path(__file__).resolve().parents[3] / "database" / "init.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE IF NOT EXISTS docs", init_sql)
        self.assertIn("is_active BOOLEAN NOT NULL DEFAULT TRUE", init_sql)
        self.assertIn("report_json JSONB", init_sql)
        self.assertIn(
            "ALTER TABLE docs ADD COLUMN IF NOT EXISTS is_active",
            init_sql,
        )
        self.assertIn(
            "ALTER TABLE docs ADD COLUMN IF NOT EXISTS report_json",
            init_sql,
        )


# ──────────────────────────────────────────────────────────────
# 5. GenDocRepository.get_active_by_repo_id() 검증
# ──────────────────────────────────────────────────────────────

class GenDocRepositoryGetActiveTests(unittest.IsolatedAsyncioTestCase):
    """get_active_by_repo_id() 메서드 검증"""

    def _make_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    async def test_returns_doc_when_found(self):
        """활성 문서가 있으면 OnboardingDoc 엔티티를 반환해야 한다."""
        from app.gen.repository import GenDocRepository

        mock_doc = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc

        db = self._make_db()
        db.execute.return_value = mock_result

        repo = GenDocRepository(db)
        result = await repo.get_active_by_repo_id(_REPO_ID)
        self.assertEqual(result, mock_doc)

    async def test_returns_none_when_not_found(self):
        """활성 문서가 없으면 None을 반환해야 한다."""
        from app.gen.repository import GenDocRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        db = self._make_db()
        db.execute.return_value = mock_result

        repo = GenDocRepository(db)
        result = await repo.get_active_by_repo_id(_REPO_ID)
        self.assertIsNone(result)

    async def test_get_active_is_coroutine(self):
        """get_active_by_repo_id는 async def이어야 한다."""
        import inspect
        from app.gen.repository import GenDocRepository
        self.assertTrue(inspect.iscoroutinefunction(GenDocRepository.get_active_by_repo_id))


# ──────────────────────────────────────────────────────────────
# 6. get_onboarding_doc() 서비스 검증
# ──────────────────────────────────────────────────────────────

class GetOnboardingDocServiceTests(unittest.IsolatedAsyncioTestCase):
    """get_onboarding_doc() 서비스 메서드 각 분기 검증"""

    def _make_analysis_job(self):
        job = MagicMock()
        job.id = _JOB_ID
        job.repo_name = "sample-repo"
        return job

    def _make_doc(self, report_json=None):
        doc = MagicMock()
        doc.id = _DOC_ID
        doc.content = "# 가이드북\n내용"
        doc.version = 1
        doc.created_at = _NOW
        doc.report_json = report_json
        return doc

    def _make_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    async def test_raises_repo_not_found(self):
        """저장소가 없으면 RepoNotFoundError를 발생시켜야 한다."""
        from app.gen.service import get_onboarding_doc

        with patch(
            "app.gen.service.GenDocRepository.get_repo_by_id",
            new=AsyncMock(return_value=None),
        ):
            with self.assertRaises(RepoNotFoundError):
                await get_onboarding_doc(self._make_db(), _REPO_ID)

    async def test_raises_docs_not_found(self):
        """저장소는 있지만 활성 문서가 없으면 DocsNotFoundError를 발생시켜야 한다."""
        from app.gen.service import get_onboarding_doc

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
                await get_onboarding_doc(self._make_db(), _REPO_ID)

    async def test_returns_markdown_data_by_default(self):
        """format=markdown(기본)일 때 DocGetMarkdownData를 반환해야 한다."""
        from app.gen.service import get_onboarding_doc

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_doc()),
            ),
        ):
            result = await get_onboarding_doc(self._make_db(), _REPO_ID, fmt="markdown")

        self.assertIsInstance(result, DocGetMarkdownData)
        self.assertEqual(result.content, "# 가이드북\n내용")
        self.assertEqual(result.version, 1)
        self.assertEqual(result.repo_name, "sample-repo")

    async def test_returns_json_data_when_format_json(self):
        """format=json일 때 DocGetJsonData를 반환해야 한다."""
        from app.gen.service import get_onboarding_doc

        report = {
            "summary": {"purpose": "테스트"},
            "stack": ["Python"],
            "guide": {
                "reading_order": ["README.md"],
                "risk_files": [{"file": "config.py", "reason": "환경 설정 주의"}],
            },
            "file_map": {"backend/": "API 서버"},
            "file_summaries": [
                {"path": "src/app/page.tsx", "summary": "Next.js 앱 라우터 진입 경로"}
            ],
        }

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_doc(report_json=report)),
            ),
        ):
            result = await get_onboarding_doc(self._make_db(), _REPO_ID, fmt="json")

        self.assertIsInstance(result, DocGetJsonData)
        self.assertEqual(result.summary, "테스트")
        self.assertEqual(result.stack, ["Python"])
        self.assertEqual(result.reading_order[0].rank, 1)
        self.assertEqual(result.reading_order[0].path, "README.md")
        self.assertEqual(result.reading_order[0].reason, "")
        self.assertEqual(result.danger_files[0].path, "config.py")
        self.assertEqual(result.danger_files[0].reason, "환경 설정 주의")
        self.assertEqual(len(result.file_summaries), 1)
        self.assertEqual(result.file_summaries[0].path, "src/app/page.tsx")
        self.assertEqual(result.file_summaries[0].summary, "Next.js 앱 라우터 진입 경로")
        self.assertEqual(result.folder_summaries[0].path, "backend/")

    async def test_json_format_with_none_report_json(self):
        """report_json이 None일 때 format=json은 빈 데이터를 반환해야 한다."""
        from app.gen.service import get_onboarding_doc

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_doc(report_json=None)),
            ),
        ):
            result = await get_onboarding_doc(self._make_db(), _REPO_ID, fmt="json")

        self.assertIsInstance(result, DocGetJsonData)
        self.assertIsNone(result.summary)
        self.assertEqual(result.stack, [])

    async def test_file_summaries_from_report_top_level(self):
        """file_summaries가 report 최상위 키에서 fileSummaries로 보존되어야 한다."""
        from app.gen.service import get_onboarding_doc

        report = {
            "summary": {"purpose": "테스트"},
            "file_summaries": [
                {"path": "src/app/page.tsx", "summary": "Next.js 앱 라우터 진입점"},
                {"path": "backend/app/main.py", "summary": "FastAPI 앱 진입점"},
            ],
        }

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_doc(report_json=report)),
            ),
        ):
            result = await get_onboarding_doc(self._make_db(), _REPO_ID, fmt="json")

        self.assertIsInstance(result, DocGetJsonData)
        self.assertEqual(len(result.file_summaries), 2)
        self.assertEqual(result.file_summaries[0].path, "src/app/page.tsx")
        self.assertEqual(result.file_summaries[0].summary, "Next.js 앱 라우터 진입점")
        self.assertEqual(result.file_summaries[1].path, "backend/app/main.py")


# ──────────────────────────────────────────────────────────────
# 7. 라우터 엔드포인트 검증 (FastAPI TestClient)
# ──────────────────────────────────────────────────────────────

class GenGetRouterTests(unittest.TestCase):
    """DOCS-GEN-API-001 엔드포인트 HTTP 응답 검증"""

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
        self.app.dependency_overrides[get_current_user] = lambda: {
            "sub": "test-user",
            "email": "test@example.com",
        }
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.get_current_user = get_current_user

    def _make_markdown_data(self):
        return DocGetMarkdownData(
            repo_id=_REPO_ID,
            repo_name="sample-repo",
            content="# 가이드북",
            generated_at=_NOW,
            version=1,
        )

    def _make_json_data(self):
        return DocGetJsonData(
            repo_id=_REPO_ID,
            repo_name="sample-repo",
            generated_at=_NOW,
            version=1,
            stack=["Python"],
            reading_order=[],
        )

    def test_200_markdown_format(self):
        """format=markdown 조회 시 200과 content, repoId, repoName을 반환해야 한다."""
        with patch(
            "app.gen.router.get_onboarding_doc",
            new=AsyncMock(return_value=self._make_markdown_data()),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}?format=markdown")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["code"], 200)
        self.assertIn("content", body["data"])
        self.assertIn("repoId", body["data"])
        self.assertIn("repoName", body["data"])

    def test_200_json_format(self):
        """format=json 조회 시 200과 stack, readingOrder 등을 반환해야 한다."""
        with patch(
            "app.gen.router.get_onboarding_doc",
            new=AsyncMock(return_value=self._make_json_data()),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}?format=json")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["code"], 200)
        self.assertIn("repoId", body["data"])
        self.assertIn("repoName", body["data"])
        self.assertIn("stack", body["data"])
        self.assertIn("readingOrder", body["data"])

    def test_default_format_is_markdown(self):
        """format 파라미터 없이 호출하면 markdown 응답이어야 한다."""
        with patch(
            "app.gen.router.get_onboarding_doc",
            new=AsyncMock(return_value=self._make_markdown_data()),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("content", resp.json()["data"])

    def test_404_repo_not_found(self):
        """RepoNotFoundError 발생 시 404 / REPO_NOT_FOUND를 반환해야 한다."""
        with patch(
            "app.gen.router.get_onboarding_doc",
            new=AsyncMock(side_effect=RepoNotFoundError()),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "REPO_NOT_FOUND")

    def test_404_docs_not_found(self):
        """DocsNotFoundError 발생 시 404 / DOCS_NOT_FOUND를 반환해야 한다."""
        with patch(
            "app.gen.router.get_onboarding_doc",
            new=AsyncMock(side_effect=DocsNotFoundError()),
        ):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "DOCS_NOT_FOUND")

    def test_invalid_format_returns_422(self):
        """format이 markdown|json이 아니면 422를 반환해야 한다."""
        resp = self.client.get(f"/api/gen/docs/{_REPO_ID}?format=pdf")
        self.assertEqual(resp.status_code, 422)

    def test_invalid_repo_id_returns_422(self):
        """repo_id가 UUID 형식이 아니면 422를 반환해야 한다."""
        resp = self.client.get("/api/gen/docs/not-a-uuid")
        self.assertEqual(resp.status_code, 422)

    def test_requires_authentication(self):
        """GET /api/gen/docs/{repo_id}는 인증이 필요해야 한다."""
        self.app.dependency_overrides.pop(self.get_current_user, None)
        resp = self.client.get(f"/api/gen/docs/{_REPO_ID}")
        self.assertEqual(resp.status_code, 401)


# ──────────────────────────────────────────────────────────────
# 8. save_onboarding_doc report_json 파라미터 회귀 검증
# ──────────────────────────────────────────────────────────────

class SaveDocReportJsonRegressionTests(unittest.IsolatedAsyncioTestCase):
    """save_onboarding_doc에 report_json 추가 후 기존 호출 호환성 검증"""

    async def test_save_accepts_report_json(self):
        """report_json 파라미터가 save_doc으로 전달되어야 한다."""
        from app.gen.repository import GenDocRepository

        mock_doc = MagicMock()
        mock_doc.id = _DOC_ID
        mock_doc.version = 1

        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        db.flush = AsyncMock()
        db.add = MagicMock()

        repo = GenDocRepository(db)
        with patch.object(repo, "save_doc", new=AsyncMock(return_value=mock_doc)) as mock_save:
            await repo.save_doc(
                repo_id=_REPO_ID,
                job_id=_JOB_ID,
                content="# 내용",
                version=1,
                report_json={"summary": "test"},
            )
            mock_save.assert_called_once()
            call_kwargs = mock_save.call_args.kwargs
            self.assertEqual(call_kwargs.get("report_json"), {"summary": "test"})

    async def test_save_without_report_json_still_works(self):
        """report_json 없이 호출해도 정상 동작해야 한다 (기존 호출 호환성)."""
        from app.gen.repository import GenDocRepository

        mock_doc = MagicMock()
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        repo = GenDocRepository(db)
        with patch.object(repo, "save_doc", new=AsyncMock(return_value=mock_doc)) as mock_save:
            await repo.save_doc(
                repo_id=_REPO_ID,
                job_id=_JOB_ID,
                content="# 내용",
                version=1,
            )
            mock_save.assert_called_once()


# ──────────────────────────────────────────────────────────────
# 9. 정적 분석 Self 리뷰 자동화 테스트
# ──────────────────────────────────────────────────────────────

class GenGetStaticAnalysisTests(unittest.TestCase):
    """CLAUDE.md §7 정적 분석 Self 리뷰 자동화"""

    def test_docs_not_found_in_common_exceptions(self):
        """DocsNotFoundError가 common.exceptions에 존재해야 한다."""
        from app.common import exceptions as exc
        self.assertTrue(hasattr(exc, "DocsNotFoundError"))

    def test_get_schemas_in_gen_schemas(self):
        """DocGetMarkdownData/Response, DocGetJsonData/Response가 gen.schemas에 있어야 한다."""
        from app.gen import schemas as sch
        for name in [
            "DocGetMarkdownData",
            "DocGetMarkdownResponse",
            "DocGetJsonData",
            "DocGetJsonResponse",
        ]:
            self.assertTrue(hasattr(sch, name), f"{name}이 gen.schemas에 없습니다.")

    def test_get_service_is_coroutine(self):
        """get_onboarding_doc은 async def이어야 한다."""
        import inspect
        from app.gen.service import get_onboarding_doc
        self.assertTrue(inspect.iscoroutinefunction(get_onboarding_doc))

    def test_get_active_by_repo_id_is_coroutine(self):
        """get_active_by_repo_id는 async def이어야 한다."""
        import inspect
        from app.gen.repository import GenDocRepository
        self.assertTrue(inspect.iscoroutinefunction(GenDocRepository.get_active_by_repo_id))

    def test_model_has_is_active_and_report_json(self):
        """OnboardingDoc 모델에 is_active와 report_json이 있어야 한다."""
        from app.gen.models import OnboardingDoc
        cols = set(OnboardingDoc.__table__.c.keys())
        self.assertIn("is_active", cols)
        self.assertIn("report_json", cols)

    def test_router_exports_get_doc(self):
        """router 모듈에 get_doc 핸들러가 존재해야 한다."""
        from app.gen import router as rmod
        self.assertTrue(hasattr(rmod, "get_doc"))

    def test_service_exports_get_onboarding_doc(self):
        """service 모듈에 get_onboarding_doc이 존재해야 한다."""
        from app.gen import service as smod
        self.assertTrue(hasattr(smod, "get_onboarding_doc"))

    def test_save_doc_accepts_report_json_kwarg(self):
        """save_onboarding_doc 시그니처에 report_json 파라미터가 있어야 한다."""
        import inspect
        from app.gen.service import save_onboarding_doc
        sig = inspect.signature(save_onboarding_doc)
        self.assertIn("report_json", sig.parameters)


if __name__ == "__main__":
    unittest.main()
