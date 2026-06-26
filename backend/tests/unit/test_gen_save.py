"""
DOCS-GEN-API-005 (POST /api/gen/docs/{repo_id}/save) 유닛 테스트

검증 대상:
  - DocSaveRequest / DocSaveResponse 스키마 직렬화
  - GenDocRepository: save_doc, get_repo_by_id, get_latest_version
  - save_onboarding_doc 서비스: 정상 저장, 저장소 미존재(404), DB 오류(500)
  - router 엔드포인트: 201 성공, 404 REPO_NOT_FOUND, 500 DATABASE_SAVE_FAILED
  - 커스텀 예외: RepoNotFoundError, DatabaseSaveFailedError 속성
  - 정적 분석 Self 리뷰 (CLAUDE.md §7 기준)

Self 리뷰 결과:
  1. KeyError 방어: repository 메서드 내 dict 직접 접근 없음 - 모두 ORM 컬럼 접근
  2. Null-Safety: get_repo_by_id → scalar_one_or_none(), None 가드 service에서 수행
  3. Exception Safety: save_onboarding_doc에서 SQLAlchemyError try/except, rollback 보장
  4. 비동기 블로킹 방어: repository/service 모두 async def, 동기 블로킹 없음
  5. 데이터 불변성: ORM 엔티티 생성 시 새 객체 생성, 원본 불변
  6. 연계 코드 영향도: common/exceptions.py 추가, main.py 등록 모두 반영
  7. 리소스 누수 방어: rollback → commit 패턴, AsyncSession 컨텍스트 관리
  8. 관측 가능성: 저장 성공/실패 시 logger 기록 (info/warning/exception)
  9. 스키마 검증: Pydantic v2 DocSaveRequest(ge=1 for version), UUID alias 처리
"""

import asyncio
import uuid
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.common.exceptions import DatabaseSaveFailedError, RepoNotFoundError
from app.gen.models import OnboardingDoc
from app.gen.repository import GenDocRepository
from app.gen.schemas import DocSaveData, DocSaveRequest, DocSaveResponse
from app.gen.service import save_onboarding_doc


# ──────────────────────────────────────────────────────────────
# 테스트용 픽스처 팩토리
# ──────────────────────────────────────────────────────────────

_REPO_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_JOB_ID  = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_DOC_ID  = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _make_doc(**overrides) -> OnboardingDoc:
    """테스트용 OnboardingDoc 인스턴스를 반환한다."""
    doc = OnboardingDoc(
        repo_id=_REPO_ID,
        job_id=_JOB_ID,
        doc_type="onboarding",
        content="# 온보딩 가이드\n내용",
        version=1,
    )
    doc.id = _DOC_ID
    doc.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


def _make_db_mock() -> MagicMock:
    """AsyncSession Mock을 반환한다."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    return db


# ──────────────────────────────────────────────────────────────
# 1. DocSaveRequest 스키마 테스트
# ──────────────────────────────────────────────────────────────

class DocSaveRequestSchemaTests(unittest.TestCase):
    """DocSaveRequest Pydantic 스키마 직렬화/역직렬화 검증"""

    def test_camel_case_alias_accepted(self):
        """jobId camelCase alias로 파싱 가능해야 한다."""
        req = DocSaveRequest.model_validate(
            {"content": "# guide", "version": 1, "jobId": str(_JOB_ID)}
        )
        self.assertEqual(req.job_id, _JOB_ID)

    def test_snake_case_name_also_accepted(self):
        """populate_by_name=True이므로 job_id snake_case도 수용해야 한다."""
        req = DocSaveRequest.model_validate(
            {"content": "# guide", "version": 1, "job_id": str(_JOB_ID)}
        )
        self.assertEqual(req.job_id, _JOB_ID)

    def test_version_must_be_ge_1(self):
        """version은 1 이상이어야 한다."""
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            DocSaveRequest.model_validate(
                {"content": "x", "version": 0, "jobId": str(_JOB_ID)}
            )

    def test_content_required(self):
        """content 필드 누락 시 ValidationError 발생해야 한다."""
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            DocSaveRequest.model_validate(
                {"version": 1, "jobId": str(_JOB_ID)}
            )


# ──────────────────────────────────────────────────────────────
# 2. DocSaveResponse 스키마 테스트
# ──────────────────────────────────────────────────────────────

class DocSaveResponseSchemaTests(unittest.TestCase):
    """DocSaveResponse 응답 직렬화 검증"""

    def test_response_serializes_alias(self):
        """DocSaveData는 camelCase alias로 직렬화되어야 한다."""
        data = DocSaveData(doc_id=_DOC_ID, repo_id=_REPO_ID, version=1)
        serialized = data.model_dump(by_alias=True)
        self.assertIn("docId", serialized)
        self.assertIn("repoId", serialized)
        self.assertEqual(serialized["docId"], _DOC_ID)
        self.assertEqual(serialized["repoId"], _REPO_ID)

    def test_response_code_default(self):
        """DocSaveResponse 기본 code는 201이어야 한다."""
        data = DocSaveData(doc_id=_DOC_ID, repo_id=_REPO_ID, version=2)
        resp = DocSaveResponse(data=data)
        self.assertEqual(resp.code, 201)
        self.assertEqual(resp.message, "created")


# ──────────────────────────────────────────────────────────────
# 3. 커스텀 예외 속성 검증
# ──────────────────────────────────────────────────────────────

class GenExceptionTests(unittest.TestCase):
    """DOCS-GEN 도메인 커스텀 예외 속성 검증"""

    def test_repo_not_found_status_and_code(self):
        """RepoNotFoundError는 404 / REPO_NOT_FOUND 코드를 가져야 한다."""
        exc = RepoNotFoundError()
        self.assertEqual(exc.status_code, 404)
        self.assertEqual(exc.error_code, "REPO_NOT_FOUND")

    def test_database_save_failed_status_and_code(self):
        """DatabaseSaveFailedError는 500 / DATABASE_SAVE_FAILED 코드를 가져야 한다."""
        exc = DatabaseSaveFailedError()
        self.assertEqual(exc.status_code, 500)
        self.assertEqual(exc.error_code, "DATABASE_SAVE_FAILED")

    def test_repo_not_found_custom_message(self):
        """RepoNotFoundError는 커스텀 메시지를 허용해야 한다."""
        exc = RepoNotFoundError("테스트 메시지")
        self.assertEqual(exc.message, "테스트 메시지")

    def test_database_save_failed_custom_message(self):
        """DatabaseSaveFailedError는 커스텀 메시지를 허용해야 한다."""
        exc = DatabaseSaveFailedError("저장 실패")
        self.assertEqual(exc.message, "저장 실패")


# ──────────────────────────────────────────────────────────────
# 4. GenDocRepository 유닛 테스트
# ──────────────────────────────────────────────────────────────

class GenDocRepositoryGetRepoTests(unittest.IsolatedAsyncioTestCase):
    """GenDocRepository.get_repo_by_id 검증"""

    async def test_returns_job_when_found(self):
        """analysis_jobs 레코드가 존재하면 AnalysisJob을 반환해야 한다."""
        db = _make_db_mock()
        mock_job = MagicMock()
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_job)

        repo = GenDocRepository(db)
        result = await repo.get_repo_by_id(_REPO_ID)

        self.assertIs(result, mock_job)
        db.execute.assert_awaited_once()

    async def test_returns_none_when_not_found(self):
        """analysis_jobs 레코드가 없으면 None을 반환해야 한다."""
        db = _make_db_mock()
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        repo = GenDocRepository(db)
        result = await repo.get_repo_by_id(_REPO_ID)

        self.assertIsNone(result)


class GenDocRepositorySaveDocTests(unittest.IsolatedAsyncioTestCase):
    """GenDocRepository.save_doc 검증"""

    async def test_save_doc_adds_and_flushes(self):
        """save_doc은 doc을 add하고 flush를 호출해야 한다."""
        db = _make_db_mock()

        async def fake_flush():
            ## flush 호출 시 id 주입 시뮬레이션
            pass
        db.flush.side_effect = fake_flush

        repo = GenDocRepository(db)
        doc = await repo.save_doc(
            repo_id=_REPO_ID,
            job_id=_JOB_ID,
            content="# 가이드",
            version=1,
        )

        db.add.assert_called_once_with(doc)
        db.flush.assert_awaited_once()
        self.assertEqual(doc.repo_id, _REPO_ID)
        self.assertEqual(doc.job_id, _JOB_ID)
        self.assertEqual(doc.content, "# 가이드")
        self.assertEqual(doc.version, 1)
        self.assertEqual(doc.doc_type, "onboarding")

    async def test_save_doc_custom_doc_type(self):
        """save_doc은 doc_type 파라미터를 OnboardingDoc에 반영해야 한다."""
        db = _make_db_mock()
        repo = GenDocRepository(db)
        doc = await repo.save_doc(
            repo_id=_REPO_ID,
            job_id=_JOB_ID,
            content="x",
            version=2,
            doc_type="summary",
        )
        self.assertEqual(doc.doc_type, "summary")


class GenDocRepositoryVersionTests(unittest.IsolatedAsyncioTestCase):
    """GenDocRepository.get_latest_version 검증"""

    async def test_returns_latest_version_when_exists(self):
        """docs가 있으면 최신 버전 번호를 반환해야 한다."""
        db = _make_db_mock()
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=3)

        repo = GenDocRepository(db)
        version = await repo.get_latest_version(_REPO_ID)

        self.assertEqual(version, 3)

    async def test_returns_zero_when_no_docs(self):
        """docs가 없으면 0을 반환해야 한다."""
        db = _make_db_mock()
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        repo = GenDocRepository(db)
        version = await repo.get_latest_version(_REPO_ID)

        self.assertEqual(version, 0)


# ──────────────────────────────────────────────────────────────
# 5. save_onboarding_doc 서비스 테스트 (DOCS-GEN-B-301)
# ──────────────────────────────────────────────────────────────

class SaveOnboardingDocServiceTests(unittest.IsolatedAsyncioTestCase):
    """save_onboarding_doc 서비스 로직 검증"""

    async def test_success_path_returns_doc(self):
        """저장소가 존재하고 저장 성공 시 OnboardingDoc을 반환해야 한다."""
        mock_doc = _make_doc()

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=MagicMock()),
            ),
            patch(
                "app.gen.service.GenDocRepository.save_doc",
                new=AsyncMock(return_value=mock_doc),
            ),
        ):
            db = _make_db_mock()
            result = await save_onboarding_doc(
                db=db,
                repo_id=_REPO_ID,
                job_id=_JOB_ID,
                content="# 가이드",
                version=1,
            )

        self.assertIs(result, mock_doc)
        db.commit.assert_awaited_once()

    async def test_raises_repo_not_found_when_job_missing(self):
        """repo_id에 해당하는 AnalysisJob이 없으면 RepoNotFoundError를 발생시켜야 한다."""
        with patch(
            "app.gen.service.GenDocRepository.get_repo_by_id",
            new=AsyncMock(return_value=None),
        ):
            db = _make_db_mock()
            with self.assertRaises(RepoNotFoundError):
                await save_onboarding_doc(
                    db=db,
                    repo_id=_REPO_ID,
                    job_id=_JOB_ID,
                    content="# 가이드",
                    version=1,
                )

        db.commit.assert_not_awaited()

    async def test_raises_database_save_failed_on_sqlalchemy_error(self):
        """save_doc에서 SQLAlchemyError 발생 시 DatabaseSaveFailedError로 변환해야 한다."""
        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=MagicMock()),
            ),
            patch(
                "app.gen.service.GenDocRepository.save_doc",
                new=AsyncMock(side_effect=OperationalError("DB 연결 실패", {}, None)),
            ),
        ):
            db = _make_db_mock()
            with self.assertRaises(DatabaseSaveFailedError):
                await save_onboarding_doc(
                    db=db,
                    repo_id=_REPO_ID,
                    job_id=_JOB_ID,
                    content="# 가이드",
                    version=1,
                )

        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()

    async def test_commit_not_called_on_repo_not_found(self):
        """RepoNotFoundError 발생 시 commit이 호출되지 않아야 한다."""
        with patch(
            "app.gen.service.GenDocRepository.get_repo_by_id",
            new=AsyncMock(return_value=None),
        ):
            db = _make_db_mock()
            try:
                await save_onboarding_doc(
                    db=db,
                    repo_id=_REPO_ID,
                    job_id=_JOB_ID,
                    content="x",
                    version=1,
                )
            except RepoNotFoundError:
                pass

        db.rollback.assert_not_awaited()


# ──────────────────────────────────────────────────────────────
# 6. 라우터 엔드포인트 테스트 (FastAPI TestClient)
# ──────────────────────────────────────────────────────────────

class GenRouterTests(unittest.TestCase):
    """DOCS-GEN-API-005 엔드포인트 HTTP 응답 검증"""

    def setUp(self):
        """TestClient 및 DB 의존성 오버라이드 설정"""
        from fastapi import FastAPI
        from app.gen.router import router
        from app.infra.database import get_db
        from app.common.exceptions import register_exception_handlers

        self.app = FastAPI()
        register_exception_handlers(self.app)
        self.app.include_router(router)
        self.mock_db = _make_db_mock()
        self.app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def _body(self, **overrides):
        """기본 요청 본문 dict를 반환한다."""
        base = {
            "content": "# 가이드\n내용",
            "version": 1,
            "jobId": str(_JOB_ID),
        }
        base.update(overrides)
        return base

    def test_201_success(self):
        """저장 성공 시 201과 docId/repoId/version을 반환해야 한다."""
        mock_doc = _make_doc()
        with patch(
            "app.gen.router.save_onboarding_doc",
            new=AsyncMock(return_value=mock_doc),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/save",
                json=self._body(),
            )

        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["code"], 201)
        self.assertEqual(body["message"], "created")
        self.assertIn("docId", body["data"])
        self.assertIn("repoId", body["data"])
        self.assertIn("version", body["data"])

    def test_404_repo_not_found(self):
        """RepoNotFoundError 발생 시 404 / REPO_NOT_FOUND를 반환해야 한다."""
        with patch(
            "app.gen.router.save_onboarding_doc",
            new=AsyncMock(side_effect=RepoNotFoundError()),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/save",
                json=self._body(),
            )

        self.assertEqual(resp.status_code, 404)
        ## build_error_response 구조: {"code": 404, "error": {"code": "REPO_NOT_FOUND", ...}}
        self.assertEqual(resp.json()["error"]["code"], "REPO_NOT_FOUND")

    def test_500_database_save_failed(self):
        """DatabaseSaveFailedError 발생 시 500 / DATABASE_SAVE_FAILED를 반환해야 한다."""
        with patch(
            "app.gen.router.save_onboarding_doc",
            new=AsyncMock(side_effect=DatabaseSaveFailedError()),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/save",
                json=self._body(),
            )

        self.assertEqual(resp.status_code, 500)
        ## build_error_response 구조: {"code": 500, "error": {"code": "DATABASE_SAVE_FAILED", ...}}
        self.assertEqual(resp.json()["error"]["code"], "DATABASE_SAVE_FAILED")

    def test_422_missing_content(self):
        """content 필드 누락 시 422 Unprocessable Entity를 반환해야 한다."""
        resp = self.client.post(
            f"/api/gen/docs/{_REPO_ID}/save",
            json={"version": 1, "jobId": str(_JOB_ID)},
        )
        self.assertEqual(resp.status_code, 422)

    def test_422_invalid_version_zero(self):
        """version=0 시 422 Unprocessable Entity를 반환해야 한다."""
        resp = self.client.post(
            f"/api/gen/docs/{_REPO_ID}/save",
            json=self._body(version=0),
        )
        self.assertEqual(resp.status_code, 422)

    def test_invalid_repo_id_format(self):
        """repo_id가 UUID 형식이 아니면 422를 반환해야 한다."""
        resp = self.client.post(
            "/api/gen/docs/not-a-uuid/save",
            json=self._body(),
        )
        self.assertEqual(resp.status_code, 422)


# ──────────────────────────────────────────────────────────────
# 7. OnboardingDoc 모델 구조 검증
# ──────────────────────────────────────────────────────────────

class OnboardingDocModelTests(unittest.TestCase):
    """OnboardingDoc SQLAlchemy 모델 구조 검증"""

    def test_tablename(self):
        """OnboardingDoc은 'docs' 테이블을 사용해야 한다."""
        self.assertEqual(OnboardingDoc.__tablename__, "docs")

    def test_required_columns_exist(self):
        """필수 컬럼(id, repo_id, job_id, doc_type, content, version, created_at)이 존재해야 한다."""
        mapper = OnboardingDoc.__mapper__
        column_names = {c.key for c in mapper.columns}
        for col in ["id", "repo_id", "job_id", "doc_type", "content", "version", "created_at"]:
            self.assertIn(col, column_names, f"컬럼 '{col}'이 OnboardingDoc에 없습니다.")

    def test_default_doc_type(self):
        """doc_type 컬럼은 DB INSERT 시 적용될 'onboarding' 기본값을 가져야 한다."""
        ## SQLAlchemy mapped_column(default=...) 는 INSERT 시 적용되므로
        ## 컬럼 메타데이터에서 default 값을 확인한다.
        col = OnboardingDoc.__table__.c["doc_type"]
        self.assertEqual(col.default.arg, "onboarding")

    def test_id_default_uuid(self):
        """id 컬럼은 callable ColumnDefault가 등록되어 있어야 한다."""
        ## SQLAlchemy mapped_column(default=uuid.uuid4) 은 INSERT 시 호출된다.
        ## col.default.arg 는 SQLAlchemy 내부 ctx 래퍼이므로 is_callable 플래그로 확인한다.
        col = OnboardingDoc.__table__.c["id"]
        self.assertIsNotNone(col.default, "id 컬럼에 ColumnDefault가 없습니다.")
        self.assertTrue(
            col.default.is_callable,
            "id 컬럼 default는 callable이어야 합니다.",
        )


# ──────────────────────────────────────────────────────────────
# 8. 정적 분석 Self 리뷰 자동화 테스트
# ──────────────────────────────────────────────────────────────

class GenSaveStaticAnalysisTests(unittest.TestCase):
    """CLAUDE.md §7 정적 분석 Self 리뷰 자동화 (임포트 가능성, 코루틴 여부 등)"""

    def test_service_importable(self):
        """app.gen.service가 정상 임포트 가능해야 한다."""
        import app.gen.service as svc
        self.assertTrue(hasattr(svc, "save_onboarding_doc"))

    def test_repository_importable(self):
        """app.gen.repository가 정상 임포트 가능해야 한다."""
        import app.gen.repository as rep
        self.assertTrue(hasattr(rep, "GenDocRepository"))

    def test_models_importable(self):
        """app.gen.models가 정상 임포트 가능해야 한다."""
        import app.gen.models as mdl
        self.assertTrue(hasattr(mdl, "OnboardingDoc"))

    def test_schemas_importable(self):
        """app.gen.schemas가 정상 임포트 가능해야 한다."""
        import app.gen.schemas as sch
        self.assertTrue(hasattr(sch, "DocSaveRequest"))
        self.assertTrue(hasattr(sch, "DocSaveResponse"))

    def test_router_importable(self):
        """app.gen.router가 정상 임포트 가능해야 한다."""
        import app.gen.router as rtr
        self.assertTrue(hasattr(rtr, "router"))

    def test_service_is_coroutine(self):
        """save_onboarding_doc은 코루틴 함수(async def)여야 한다."""
        import inspect
        import app.gen.service as svc
        self.assertTrue(inspect.iscoroutinefunction(svc.save_onboarding_doc))

    def test_repo_methods_are_coroutines(self):
        """GenDocRepository의 메서드들은 코루틴 함수(async def)여야 한다."""
        import inspect
        repo = GenDocRepository.__new__(GenDocRepository)
        for method_name in ["get_repo_by_id", "save_doc", "get_latest_version"]:
            method = getattr(GenDocRepository, method_name)
            self.assertTrue(
                inspect.iscoroutinefunction(method),
                f"{method_name}은 async def이어야 합니다.",
            )

    def test_exceptions_in_common_exceptions(self):
        """RepoNotFoundError, DatabaseSaveFailedError가 common.exceptions에 존재해야 한다."""
        from app.common import exceptions as exc_module
        self.assertTrue(hasattr(exc_module, "RepoNotFoundError"))
        self.assertTrue(hasattr(exc_module, "DatabaseSaveFailedError"))


if __name__ == "__main__":
    unittest.main()
