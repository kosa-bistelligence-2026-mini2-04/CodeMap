"""
DOCS-GEN-API-003 (PUT /api/gen/docs/{repo_id}) 유닛 테스트

검증 대상:
  - DocRebuildRequest / DocRebuildData / DocRebuildResponse 스키마 직렬화
  - GenDocRepository.soft_delete_active_docs() 메서드
  - rebuild_onboarding_doc() 서비스: 404 분기 / 소프트 삭제 / 버전 계산 / 큐잉
  - 라우터 엔드포인트: 202/404(repo)/404(docs)/422
  - 회귀: 기존 API-001/002 엔드포인트에 영향 없음

Self 리뷰 결과 (CLAUDE.md §7):
  1. KeyError 방어: report_json/analysis_job 속성 접근 전 None 체크
  2. Null-Safety: active_doc None → DocsNotFoundError 분기 보장
  3. Exception Safety: soft_delete 실패 시 rollback + DatabaseSaveFailedError
  4. 비동기 블로킹: soft_delete는 DB update 쿼리 — CPU bound 없음
  5. 데이터 불변성: soft_delete는 UPDATE SQL, 파이썬 객체 직접 변경 없음
  6. 연계 코드 영향도: repository.py import 변경(update 추가) — 기존 메서드 무영향 확인
  7. 리소스 누수: rollback 후 예외 re-raise로 session 누수 없음
  8. 관측 가능성: 각 분기 logger.warning/info 기록
  9. 스키마 검증: previousVersion / newVersion camelCase alias 직렬화 확인
"""

import uuid
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

from fastapi.testclient import TestClient

from app.common.exceptions import DocsNotFoundError, RepoNotFoundError
from app.gen.schemas import DocRebuildData, DocRebuildRequest, DocRebuildResponse


_REPO_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_JOB_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_DOC_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_NOW = datetime(2026, 6, 27, 9, 0, 0, tzinfo=timezone.utc)


# ──────────────────────────────────────────────────────────────
# 1. DocRebuildRequest 스키마 검증
# ──────────────────────────────────────────────────────────────

class DocRebuildRequestSchemaTests(unittest.TestCase):
    """DocRebuildRequest 기본값 및 선택 필드 검증"""

    def test_default_model(self):
        """model 필드 기본값은 'gpt-4o-mini'이어야 한다."""
        req = DocRebuildRequest()
        self.assertEqual(req.model, "gpt-4o-mini")

    def test_default_reason_is_none(self):
        """reason 필드 기본값은 None이어야 한다."""
        req = DocRebuildRequest()
        self.assertIsNone(req.reason)

    def test_custom_model_and_reason(self):
        """model과 reason을 직접 지정할 수 있어야 한다."""
        req = DocRebuildRequest(model="gpt-4o", reason="코드 변경 반영")
        self.assertEqual(req.model, "gpt-4o")
        self.assertEqual(req.reason, "코드 변경 반영")


# ──────────────────────────────────────────────────────────────
# 2. DocRebuildData / DocRebuildResponse 스키마 검증
# ──────────────────────────────────────────────────────────────

class DocRebuildResponseSchemaTests(unittest.TestCase):
    """DocRebuildData camelCase 직렬화 및 DocRebuildResponse 검증"""

    def _make_data(self, **kwargs):
        defaults = {
            "job_id": _JOB_ID,
            "repo_id": _REPO_ID,
            "previous_version": 1,
            "new_version": 2,
        }
        defaults.update(kwargs)
        return DocRebuildData(**defaults)

    def test_camel_alias_serialization(self):
        """jobId, repoId, previousVersion, newVersion이 camelCase로 직렬화되어야 한다."""
        data = self._make_data()
        dumped = data.model_dump(by_alias=True)
        self.assertIn("jobId", dumped)
        self.assertIn("repoId", dumped)
        self.assertIn("previousVersion", dumped)
        self.assertIn("newVersion", dumped)
        self.assertNotIn("previous_version", dumped)
        self.assertNotIn("new_version", dumped)

    def test_version_values(self):
        """previous_version과 new_version 값이 정확히 설정되어야 한다."""
        data = self._make_data(previous_version=3, new_version=4)
        self.assertEqual(data.previous_version, 3)
        self.assertEqual(data.new_version, 4)

    def test_response_default_code_202(self):
        """DocRebuildResponse 기본 code는 202이어야 한다."""
        resp = DocRebuildResponse(data=self._make_data())
        self.assertEqual(resp.code, 202)
        self.assertEqual(resp.message, "accepted")


# ──────────────────────────────────────────────────────────────
# 3. GenDocRepository.soft_delete_active_docs() 검증
# ──────────────────────────────────────────────────────────────

class SoftDeleteActiveDocsTests(unittest.IsolatedAsyncioTestCase):
    """soft_delete_active_docs() DB UPDATE 동작 검증"""

    def _make_db(self, rowcount=1):
        db = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = rowcount
        db.execute = AsyncMock(return_value=mock_result)
        return db

    async def test_returns_deleted_count(self):
        """삭제된 레코드 수를 반환해야 한다."""
        from app.gen.repository import GenDocRepository

        db = self._make_db(rowcount=2)
        repo = GenDocRepository(db)
        count = await repo.soft_delete_active_docs(_REPO_ID)
        self.assertEqual(count, 2)

    async def test_returns_zero_when_none_active(self):
        """활성 문서가 없을 때 0을 반환해야 한다."""
        from app.gen.repository import GenDocRepository

        db = self._make_db(rowcount=0)
        repo = GenDocRepository(db)
        count = await repo.soft_delete_active_docs(_REPO_ID)
        self.assertEqual(count, 0)

    async def test_calls_db_execute(self):
        """db.execute()가 한 번 호출되어야 한다."""
        from app.gen.repository import GenDocRepository

        db = self._make_db()
        repo = GenDocRepository(db)
        await repo.soft_delete_active_docs(_REPO_ID)
        db.execute.assert_called_once()

    async def test_is_coroutine(self):
        """soft_delete_active_docs는 async def이어야 한다."""
        import inspect
        from app.gen.repository import GenDocRepository
        self.assertTrue(
            inspect.iscoroutinefunction(GenDocRepository.soft_delete_active_docs)
        )


# ──────────────────────────────────────────────────────────────
# 4. rebuild_onboarding_doc() 서비스 검증
# ──────────────────────────────────────────────────────────────

class RebuildOnboardingDocServiceTests(unittest.IsolatedAsyncioTestCase):
    """rebuild_onboarding_doc() 서비스 각 분기 검증"""

    def _make_analysis_job(self):
        job = MagicMock()
        job.id = _JOB_ID
        job.repo_name = "sample-repo"
        job.report_json = {"summary": "test"}
        return job

    def _make_active_doc(self, version=1):
        doc = MagicMock()
        doc.id = _DOC_ID
        doc.version = version
        doc.is_active = True
        return doc

    def _make_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    def _make_bg_tasks(self):
        bg = MagicMock()
        bg.add_task = MagicMock()
        return bg

    async def test_raises_repo_not_found(self):
        """저장소가 없으면 RepoNotFoundError를 발생시켜야 한다."""
        from app.gen.service import rebuild_onboarding_doc

        with patch(
            "app.gen.service.GenDocRepository.get_repo_by_id",
            new=AsyncMock(return_value=None),
        ):
            with self.assertRaises(RepoNotFoundError):
                await rebuild_onboarding_doc(
                    self._make_db(), _REPO_ID, self._make_bg_tasks()
                )

    async def test_raises_docs_not_found_when_no_active(self):
        """활성 문서가 없으면 DocsNotFoundError를 발생시켜야 한다."""
        from app.gen.service import rebuild_onboarding_doc

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
                await rebuild_onboarding_doc(
                    self._make_db(), _REPO_ID, self._make_bg_tasks()
                )

    async def test_returns_correct_versions(self):
        """(job_id, previous_version, new_version) 튜플을 올바르게 반환해야 한다."""
        from app.gen.service import rebuild_onboarding_doc

        db = self._make_db()

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_active_doc(version=3)),
            ),
            patch(
                "app.gen.service.GenDocRepository.soft_delete_active_docs",
                new=AsyncMock(return_value=1),
            ),
            patch("app.gen.background.run_doc_generation", new=MagicMock()),
        ):
            result = await rebuild_onboarding_doc(
                db, _REPO_ID, self._make_bg_tasks()
            )

        job_id, prev, new = result
        self.assertEqual(job_id, _JOB_ID)
        self.assertEqual(prev, 3)
        self.assertEqual(new, 4)

    async def test_soft_delete_called_before_queue(self):
        """soft_delete_active_docs가 반드시 호출된 뒤 background 큐잉이 이루어져야 한다."""
        from app.gen.service import rebuild_onboarding_doc

        call_order = []
        db = self._make_db()
        bg = self._make_bg_tasks()

        async def _mock_soft_delete(*args):
            ## self + repo_id 모두 수신하기 위해 *args 사용
            call_order.append("soft_delete")
            return 1

        def _mock_add_task(*args, **kwargs):
            call_order.append("bg_queue")

        bg.add_task = _mock_add_task

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_active_doc(version=1)),
            ),
            patch(
                "app.gen.service.GenDocRepository.soft_delete_active_docs",
                new=_mock_soft_delete,
            ),
            patch("app.gen.background.run_doc_generation", new=MagicMock()),
        ):
            await rebuild_onboarding_doc(db, _REPO_ID, bg)

        self.assertEqual(call_order, ["soft_delete", "bg_queue"])

    async def test_rollback_on_soft_delete_failure(self):
        """soft_delete 실패 시 db.rollback()이 호출되어야 한다."""
        from app.gen.service import rebuild_onboarding_doc
        from app.common.exceptions import DatabaseSaveFailedError

        db = self._make_db()

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_active_doc()),
            ),
            patch(
                "app.gen.service.GenDocRepository.soft_delete_active_docs",
                new=AsyncMock(side_effect=Exception("DB 오류")),
            ),
        ):
            with self.assertRaises(DatabaseSaveFailedError):
                await rebuild_onboarding_doc(db, _REPO_ID, self._make_bg_tasks())

        db.rollback.assert_called_once()

    async def test_reason_logged_when_provided(self):
        """reason이 제공되면 예외 없이 처리되어야 한다."""
        from app.gen.service import rebuild_onboarding_doc

        db = self._make_db()

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_active_doc()),
            ),
            patch(
                "app.gen.service.GenDocRepository.soft_delete_active_docs",
                new=AsyncMock(return_value=1),
            ),
            patch("app.gen.background.run_doc_generation", new=MagicMock()),
        ):
            result = await rebuild_onboarding_doc(
                db, _REPO_ID, self._make_bg_tasks(), reason="의존성 업데이트"
            )

        self.assertIsNotNone(result)

    async def test_is_coroutine(self):
        """rebuild_onboarding_doc은 async def이어야 한다."""
        import inspect
        from app.gen.service import rebuild_onboarding_doc
        self.assertTrue(inspect.iscoroutinefunction(rebuild_onboarding_doc))

    async def test_clone_path_includes_repo_suffix(self):
        """background_tasks.add_task에 전달되는 clone_path는 '/repo' suffix를 포함해야 한다.

        프로젝트 표준 클론 경로: {CLONE_BASE_DIR}/{repo_id}/repo
        '/repo' 누락 시 nodes.py의 README·설정 파일 탐색이 실패한다.
        """
        from app.gen.service import rebuild_onboarding_doc

        db = self._make_db()
        bg = MagicMock()
        captured_kwargs: dict = {}

        def _capture_add_task(fn, **kwargs):
            captured_kwargs.update(kwargs)

        bg.add_task = _capture_add_task

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_active_doc(version=1)),
            ),
            patch(
                "app.gen.service.GenDocRepository.soft_delete_active_docs",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "app.gen.service.get_settings",
                return_value=MagicMock(CLONE_BASE_DIR="/data/clones"),
            ),
            patch("app.gen.background.run_doc_generation", new=MagicMock()),
        ):
            await rebuild_onboarding_doc(db, _REPO_ID, bg)

        clone_path = captured_kwargs.get("clone_path", "")
        self.assertTrue(
            clone_path.endswith("/repo"),
            f"clone_path가 '/repo'로 끝나야 합니다. 실제: {clone_path!r}",
        )
        self.assertIn(str(_REPO_ID), clone_path)

    async def test_model_forwarded_to_run_doc_generation(self):
        """요청받은 model 파라미터가 run_doc_generation에 그대로 전달되어야 한다."""
        from app.gen.service import rebuild_onboarding_doc

        db = self._make_db()
        bg = MagicMock()
        captured_kwargs: dict = {}

        def _capture_add_task(fn, **kwargs):
            captured_kwargs.update(kwargs)

        bg.add_task = _capture_add_task

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=self._make_active_doc(version=1)),
            ),
            patch(
                "app.gen.service.GenDocRepository.soft_delete_active_docs",
                new=AsyncMock(return_value=1),
            ),
            patch(
                "app.gen.service.get_settings",
                return_value=MagicMock(CLONE_BASE_DIR="/data/clones"),
            ),
            patch("app.gen.background.run_doc_generation", new=MagicMock()),
        ):
            await rebuild_onboarding_doc(db, _REPO_ID, bg, model="gpt-4o")

        self.assertEqual(
            captured_kwargs.get("model"),
            "gpt-4o",
            "model 파라미터가 run_doc_generation에 전달되지 않았습니다.",
        )


# ──────────────────────────────────────────────────────────────
# 5. 라우터 엔드포인트 검증 (FastAPI TestClient)
# ──────────────────────────────────────────────────────────────

class GenRebuildRouterTests(unittest.TestCase):
    """DOCS-GEN-API-003 엔드포인트 HTTP 응답 검증"""

    def setUp(self):
        from fastapi import FastAPI
        from app.gen.router import router
        from app.infra.database import get_db
        from app.common.exceptions import register_exception_handlers

        self.app = FastAPI()
        register_exception_handlers(self.app)
        self.app.include_router(router)
        self.mock_db = MagicMock()
        self.app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def _make_rebuild_result(self, prev=1, new=2):
        return (_JOB_ID, prev, new)

    def test_202_success(self):
        """성공 시 202와 jobId, previousVersion, newVersion을 반환해야 한다."""
        with patch(
            "app.gen.router.rebuild_onboarding_doc",
            new=AsyncMock(return_value=self._make_rebuild_result(prev=2, new=3)),
        ):
            resp = self.client.put(
                f"/api/gen/docs/{_REPO_ID}",
                json={"model": "gpt-4o-mini"},
            )

        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        self.assertEqual(body["code"], 202)
        self.assertEqual(body["message"], "accepted")
        self.assertIn("jobId", body["data"])
        self.assertIn("previousVersion", body["data"])
        self.assertIn("newVersion", body["data"])
        self.assertEqual(body["data"]["previousVersion"], 2)
        self.assertEqual(body["data"]["newVersion"], 3)

    def test_202_with_reason(self):
        """reason 필드가 포함된 요청도 202를 반환해야 한다."""
        with patch(
            "app.gen.router.rebuild_onboarding_doc",
            new=AsyncMock(return_value=self._make_rebuild_result()),
        ):
            resp = self.client.put(
                f"/api/gen/docs/{_REPO_ID}",
                json={"model": "gpt-4o", "reason": "의존성 업데이트"},
            )

        self.assertEqual(resp.status_code, 202)

    def test_202_empty_body(self):
        """요청 본문 없이 호출해도 기본값으로 202를 반환해야 한다."""
        with patch(
            "app.gen.router.rebuild_onboarding_doc",
            new=AsyncMock(return_value=self._make_rebuild_result()),
        ):
            resp = self.client.put(
                f"/api/gen/docs/{_REPO_ID}",
                json={},
            )

        self.assertEqual(resp.status_code, 202)

    def test_404_repo_not_found(self):
        """RepoNotFoundError 발생 시 404 / REPO_NOT_FOUND를 반환해야 한다."""
        with patch(
            "app.gen.router.rebuild_onboarding_doc",
            new=AsyncMock(side_effect=RepoNotFoundError()),
        ):
            resp = self.client.put(
                f"/api/gen/docs/{_REPO_ID}",
                json={},
            )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "REPO_NOT_FOUND")

    def test_404_docs_not_found(self):
        """DocsNotFoundError 발생 시 404 / DOCS_NOT_FOUND를 반환해야 한다."""
        with patch(
            "app.gen.router.rebuild_onboarding_doc",
            new=AsyncMock(side_effect=DocsNotFoundError()),
        ):
            resp = self.client.put(
                f"/api/gen/docs/{_REPO_ID}",
                json={},
            )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "DOCS_NOT_FOUND")

    def test_422_invalid_repo_id(self):
        """repo_id가 UUID 형식이 아니면 422를 반환해야 한다."""
        resp = self.client.put("/api/gen/docs/not-a-uuid", json={})
        self.assertEqual(resp.status_code, 422)


# ──────────────────────────────────────────────────────────────
# 6. 회귀 검증 — API-001/002 엔드포인트 영향 없음
# ──────────────────────────────────────────────────────────────

class RebuildRegressionTests(unittest.TestCase):
    """PUT 엔드포인트 추가 후 GET/POST 기존 엔드포인트 회귀 확인"""

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

    def test_post_endpoint_still_exists(self):
        """POST /{repo_id} 엔드포인트가 여전히 동작해야 한다."""
        from app.common.exceptions import RepoNotFoundError

        with patch(
            "app.gen.router.validate_and_queue_doc_generation",
            new=AsyncMock(side_effect=RepoNotFoundError()),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}",
                json={"force": False},
            )

        self.assertEqual(resp.status_code, 404)

    def _collect_api_routes(self):
        """app에 등록된 모든 APIRoute를 재귀적으로 수집한다."""
        from fastapi.routing import APIRoute
        routes = []
        for r in self.app.routes:
            if isinstance(r, APIRoute):
                routes.append(r)
            elif hasattr(r, "original_router") and hasattr(r.original_router, "routes"):
                routes.extend(
                    sub for sub in r.original_router.routes if isinstance(sub, APIRoute)
                )
        return routes

    def test_put_and_post_are_distinct(self):
        """PUT과 POST 엔드포인트가 각각 독립적으로 등록되어야 한다."""
        all_routes = self._collect_api_routes()
        has_put = any(
            "PUT" in (r.methods or set()) and r.path == "/api/gen/docs/{repo_id}"
            for r in all_routes
        )
        has_post = any(
            "POST" in (r.methods or set()) and r.path == "/api/gen/docs/{repo_id}"
            for r in all_routes
        )
        self.assertTrue(has_put, "PUT 엔드포인트가 등록되어 있지 않습니다.")
        self.assertTrue(has_post, "POST 엔드포인트가 등록되어 있지 않습니다.")


# ──────────────────────────────────────────────────────────────
# 7. 정적 분석 Self 리뷰 자동화 테스트
# ──────────────────────────────────────────────────────────────

class GenRebuildStaticAnalysisTests(unittest.TestCase):
    """CLAUDE.md §7 정적 분석 Self 리뷰 자동화"""

    def test_rebuild_schemas_in_gen_schemas(self):
        """DocRebuildRequest/Data/Response가 gen.schemas에 있어야 한다."""
        from app.gen import schemas as sch
        for name in ["DocRebuildRequest", "DocRebuildData", "DocRebuildResponse"]:
            self.assertTrue(hasattr(sch, name), f"{name}이 gen.schemas에 없습니다.")

    def test_soft_delete_in_repository(self):
        """GenDocRepository에 soft_delete_active_docs가 있어야 한다."""
        from app.gen.repository import GenDocRepository
        self.assertTrue(hasattr(GenDocRepository, "soft_delete_active_docs"))

    def test_rebuild_service_exported(self):
        """service 모듈에 rebuild_onboarding_doc이 있어야 한다."""
        from app.gen import service as smod
        self.assertTrue(hasattr(smod, "rebuild_onboarding_doc"))

    def test_router_exports_rebuild_doc(self):
        """router 모듈에 rebuild_doc 핸들러가 있어야 한다."""
        from app.gen import router as rmod
        self.assertTrue(hasattr(rmod, "rebuild_doc"))

    def test_rebuild_service_is_coroutine(self):
        """rebuild_onboarding_doc은 async def이어야 한다."""
        import inspect
        from app.gen.service import rebuild_onboarding_doc
        self.assertTrue(inspect.iscoroutinefunction(rebuild_onboarding_doc))

    def test_soft_delete_is_coroutine(self):
        """soft_delete_active_docs는 async def이어야 한다."""
        import inspect
        from app.gen.repository import GenDocRepository
        self.assertTrue(
            inspect.iscoroutinefunction(GenDocRepository.soft_delete_active_docs)
        )

    def test_rebuild_request_has_model_and_reason(self):
        """DocRebuildRequest에 model과 reason 필드가 있어야 한다."""
        import inspect
        from app.gen.schemas import DocRebuildRequest
        fields = DocRebuildRequest.model_fields
        self.assertIn("model", fields)
        self.assertIn("reason", fields)

    def test_rebuild_data_has_version_fields(self):
        """DocRebuildData에 previous_version, new_version 필드가 있어야 한다."""
        from app.gen.schemas import DocRebuildData
        fields = DocRebuildData.model_fields
        self.assertIn("previous_version", fields)
        self.assertIn("new_version", fields)

    def test_soft_delete_uses_update_not_loop(self):
        """soft_delete_active_docs는 UPDATE SQL을 사용해야 한다 (루프 대신)."""
        import inspect
        from app.gen.repository import GenDocRepository
        src = inspect.getsource(GenDocRepository.soft_delete_active_docs)
        self.assertIn("update(", src)

    def test_rebuild_service_signature(self):
        """rebuild_onboarding_doc 시그니처에 model과 reason 파라미터가 있어야 한다."""
        import inspect
        from app.gen.service import rebuild_onboarding_doc
        sig = inspect.signature(rebuild_onboarding_doc)
        self.assertIn("model", sig.parameters)
        self.assertIn("reason", sig.parameters)


if __name__ == "__main__":
    unittest.main()
