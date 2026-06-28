"""
DOCS-GEN-API-002 (POST /api/gen/docs/{repo_id}) 유닛 테스트

검증 대상:
  - DocTriggerRequest / DocTriggerResponse 스키마 직렬화
  - master_report_to_markdown 변환 유틸리티
  - background.py: is_generation_in_progress / _mark_in_progress / _mark_done
  - validate_and_queue_doc_generation 서비스: 각 검증 분기별 예외 발생
  - router 엔드포인트: 202 성공, 404/409/422/500 에러
  - 신규 커스텀 예외 속성 (DocsAlreadyExists, InProgress, AnalysisNotCompleted, GenerationFailed)

Self 리뷰 결과 (CLAUDE.md §7):
  1. KeyError 방어: report.get() 패턴 전면 사용, 직접 dict[] 접근 없음
  2. Null-Safety: guide/summary 모두 `or {}` / `or []` 폴백
  3. Exception Safety: background.py에 try/finally → _mark_done 보장
  4. 비동기 블로킹: master_report_to_markdown → asyncio.to_thread 격리
  5. 데이터 불변성: analysis_report는 dict 복사본 전달, 원본 불변
  6. 연계 코드 영향도: common/exceptions.py 추가, router/service 연결 반영
  7. 리소스 누수: background 작업은 async_session_factory()로 독립 세션 관리
  8. 관측 가능성: 각 검증 분기·백그라운드 작업 완료/실패에 logger 기록
  9. 스키마 검증: Pydantic v2 DocTriggerRequest(force default=False) 검증
"""

import uuid
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.common.exceptions import (
    AnalysisNotCompletedError,
    DocsAlreadyExistsError,
    DocsGenerationFailedError,
    DocsGenerationInProgressError,
    RepoNotFoundError,
)
from app.gen import background as bg_module
from app.gen.background import (
    _mark_done,
    _mark_in_progress,
    is_generation_in_progress,
)
from app.gen.markdown import master_report_to_markdown
from app.gen.schemas import DocTriggerData, DocTriggerRequest, DocTriggerResponse


_REPO_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_JOB_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


# ──────────────────────────────────────────────────────────────
# 1. DocTriggerRequest 스키마 검증
# ──────────────────────────────────────────────────────────────

class DocTriggerRequestSchemaTests(unittest.TestCase):
    """DocTriggerRequest Pydantic 스키마 기본값·필드 검증"""

    def test_default_force_is_false(self):
        """force 기본값은 False이어야 한다."""
        req = DocTriggerRequest()
        self.assertFalse(req.force)

    def test_default_model_is_gpt4o_mini(self):
        """model 기본값은 'gpt-4o-mini'이어야 한다."""
        req = DocTriggerRequest()
        self.assertEqual(req.model, "gpt-4o-mini")

    def test_force_true_accepted(self):
        """force=true로 파싱이 가능해야 한다."""
        req = DocTriggerRequest.model_validate({"force": True})
        self.assertTrue(req.force)

    def test_custom_model_accepted(self):
        """custom model 명 파싱이 가능해야 한다."""
        req = DocTriggerRequest.model_validate({"model": "gpt-4o"})
        self.assertEqual(req.model, "gpt-4o")


# ──────────────────────────────────────────────────────────────
# 2. DocTriggerResponse 스키마 검증
# ──────────────────────────────────────────────────────────────

class DocTriggerResponseSchemaTests(unittest.TestCase):
    """DocTriggerResponse 직렬화 검증"""

    def test_response_code_default(self):
        """DocTriggerResponse 기본 code는 202이어야 한다."""
        data = DocTriggerData(job_id=_JOB_ID, repo_id=_REPO_ID)
        resp = DocTriggerResponse(data=data)
        self.assertEqual(resp.code, 202)
        self.assertEqual(resp.message, "accepted")

    def test_data_serializes_camel_alias(self):
        """DocTriggerData는 jobId/repoId/estimatedMinutes camelCase로 직렬화되어야 한다."""
        data = DocTriggerData(job_id=_JOB_ID, repo_id=_REPO_ID, estimated_minutes=3)
        serialized = data.model_dump(by_alias=True)
        self.assertIn("jobId", serialized)
        self.assertIn("repoId", serialized)
        self.assertIn("estimatedMinutes", serialized)
        self.assertEqual(serialized["estimatedMinutes"], 3)

    def test_status_default_docs_queued(self):
        """status 기본값은 'docs_queued'이어야 한다."""
        data = DocTriggerData(job_id=_JOB_ID, repo_id=_REPO_ID)
        self.assertEqual(data.status, "docs_queued")


# ──────────────────────────────────────────────────────────────
# 3. 신규 커스텀 예외 속성 검증
# ──────────────────────────────────────────────────────────────

class GenTriggerExceptionTests(unittest.TestCase):
    """DOCS-GEN-API-002 관련 커스텀 예외 속성 검증"""

    def test_docs_already_exists(self):
        """DocsAlreadyExistsError는 409 / DOCS_ALREADY_EXISTS이어야 한다."""
        exc = DocsAlreadyExistsError()
        self.assertEqual(exc.status_code, 409)
        self.assertEqual(exc.error_code, "DOCS_ALREADY_EXISTS")

    def test_docs_generation_in_progress(self):
        """DocsGenerationInProgressError는 409 / DOCS_GENERATION_IN_PROGRESS이어야 한다."""
        exc = DocsGenerationInProgressError()
        self.assertEqual(exc.status_code, 409)
        self.assertEqual(exc.error_code, "DOCS_GENERATION_IN_PROGRESS")

    def test_analysis_not_completed(self):
        """AnalysisNotCompletedError는 422 / ANALYSIS_NOT_COMPLETED이어야 한다."""
        exc = AnalysisNotCompletedError()
        self.assertEqual(exc.status_code, 422)
        self.assertEqual(exc.error_code, "ANALYSIS_NOT_COMPLETED")

    def test_docs_generation_failed(self):
        """DocsGenerationFailedError는 500 / DOCS_GENERATION_FAILED이어야 한다."""
        exc = DocsGenerationFailedError()
        self.assertEqual(exc.status_code, 500)
        self.assertEqual(exc.error_code, "DOCS_GENERATION_FAILED")

    def test_custom_messages_accepted(self):
        """모든 예외는 커스텀 메시지를 허용해야 한다."""
        self.assertEqual(DocsAlreadyExistsError("msg").message, "msg")
        self.assertEqual(DocsGenerationInProgressError("msg").message, "msg")
        self.assertEqual(AnalysisNotCompletedError("msg").message, "msg")
        self.assertEqual(DocsGenerationFailedError("msg").message, "msg")


# ──────────────────────────────────────────────────────────────
# 4. master_report_to_markdown 유틸리티 검증
# ──────────────────────────────────────────────────────────────

class MasterReportToMarkdownTests(unittest.TestCase):
    """master_report_to_markdown 변환 함수 검증"""

    def _make_report(self) -> dict:
        return {
            "summary": {
                "purpose": "테스트 프로젝트입니다.",
                "key_features": ["기능 A", "기능 B"],
                "tech_context": "FastAPI + PostgreSQL",
            },
            "stack": ["Python 3.12", "FastAPI"],
            ## file_map은 folder_summaries 래퍼 dict 구조 (nodes.py master_report 기준)
            "file_map": {"folder_summaries": {"backend/": "API 서버 코드"}},
            "guide": {
                "reading_order": [
                    {"rank": 1, "path": "README.md", "reason": "먼저 읽어야 함"}
                ],
                "risk_files": [
                    {"path": "app/infra/config.py", "reason": "환경변수 관리"}
                ],
                "first_tasks": [
                    {"task": "테스트 작성", "difficulty": "하"}
                ],
            },
        }

    def test_title_includes_repo_name(self):
        """변환 결과 제목에 repo_name이 포함되어야 한다."""
        md = master_report_to_markdown({}, repo_name="MyProject")
        self.assertIn("MyProject", md)

    def test_default_title_when_no_repo_name(self):
        """repo_name 미전달 시 기본 제목 '프로젝트'가 사용되어야 한다."""
        md = master_report_to_markdown({})
        self.assertIn("프로젝트", md)

    def test_purpose_rendered(self):
        """purpose 필드가 Markdown에 포함되어야 한다."""
        md = master_report_to_markdown(self._make_report())
        self.assertIn("테스트 프로젝트입니다.", md)

    def test_key_features_rendered(self):
        """key_features 목록이 Markdown에 포함되어야 한다."""
        md = master_report_to_markdown(self._make_report())
        self.assertIn("기능 A", md)
        self.assertIn("기능 B", md)

    def test_stack_rendered(self):
        """기술 스택 목록이 Markdown에 포함되어야 한다."""
        md = master_report_to_markdown(self._make_report())
        self.assertIn("Python 3.12", md)
        self.assertIn("FastAPI", md)

    def test_file_map_rendered(self):
        """폴더 구조 설명이 Markdown에 포함되어야 한다."""
        md = master_report_to_markdown(self._make_report())
        self.assertIn("backend/", md)
        self.assertIn("API 서버 코드", md)

    def test_reading_order_rendered(self):
        """추천 파일 읽기 순서 표가 Markdown에 포함되어야 한다."""
        md = master_report_to_markdown(self._make_report())
        self.assertIn("README.md", md)
        self.assertIn("먼저 읽어야 함", md)

    def test_risk_files_rendered(self):
        """주의 파일 목록이 Markdown에 포함되어야 한다."""
        md = master_report_to_markdown(self._make_report())
        self.assertIn("app/infra/config.py", md)
        self.assertIn("환경변수 관리", md)

    def test_first_tasks_rendered(self):
        """첫 기여 추천 작업이 Markdown에 포함되어야 한다."""
        md = master_report_to_markdown(self._make_report())
        self.assertIn("테스트 작성", md)

    def test_empty_report_returns_header_only(self):
        """빈 report 전달 시 제목만 포함된 Markdown이 반환되어야 한다."""
        md = master_report_to_markdown({}, repo_name="Empty")
        self.assertIn("Empty", md)
        ## 빈 report면 추가 섹션 없음 — KeyError 없이 안전하게 반환되어야 함
        self.assertIsInstance(md, str)

    def test_returns_string_type(self):
        """변환 결과는 반드시 str 타입이어야 한다."""
        result = master_report_to_markdown(self._make_report(), repo_name="Test")
        self.assertIsInstance(result, str)


# ──────────────────────────────────────────────────────────────
# 5. background.py 진행 상태 추적기 검증
# ──────────────────────────────────────────────────────────────

class BackgroundProgressTrackerTests(unittest.TestCase):
    """is_generation_in_progress / _mark_in_progress / _mark_done 검증"""

    def setUp(self):
        """테스트 전 in-progress 집합을 초기화한다."""
        bg_module._DOCS_GENERATION_IN_PROGRESS.clear()

    def test_not_in_progress_by_default(self):
        """마킹하지 않은 repo는 진행 중이 아니어야 한다."""
        self.assertFalse(is_generation_in_progress(_REPO_ID))

    def test_mark_in_progress_sets_flag(self):
        """_mark_in_progress 호출 후 is_generation_in_progress는 True이어야 한다."""
        _mark_in_progress(_REPO_ID)
        self.assertTrue(is_generation_in_progress(_REPO_ID))

    def test_mark_done_clears_flag(self):
        """_mark_done 호출 후 is_generation_in_progress는 False이어야 한다."""
        _mark_in_progress(_REPO_ID)
        _mark_done(_REPO_ID)
        self.assertFalse(is_generation_in_progress(_REPO_ID))

    def test_mark_done_idempotent(self):
        """_mark_done은 마킹되지 않은 repo에 호출해도 예외가 없어야 한다."""
        other_id = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        try:
            _mark_done(other_id)
        except Exception as exc:
            self.fail(f"_mark_done이 예외를 발생시켰습니다: {exc}")

    def test_different_repos_tracked_independently(self):
        """서로 다른 repo_id는 독립적으로 추적되어야 한다."""
        other_id = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
        _mark_in_progress(_REPO_ID)
        self.assertTrue(is_generation_in_progress(_REPO_ID))
        self.assertFalse(is_generation_in_progress(other_id))


# ──────────────────────────────────────────────────────────────
# 6. validate_and_queue_doc_generation 서비스 검증
# ──────────────────────────────────────────────────────────────

class ValidateAndQueueServiceTests(unittest.IsolatedAsyncioTestCase):
    """validate_and_queue_doc_generation 서비스 각 분기별 예외 검증"""

    def setUp(self):
        ## _mark_in_progress 사이드 이펙트가 테스트 간 누적되지 않도록 초기화
        bg_module._DOCS_GENERATION_IN_PROGRESS.clear()

    def tearDown(self):
        bg_module._DOCS_GENERATION_IN_PROGRESS.clear()

    def _make_analysis_job(self, status: str = "COMPLETED") -> MagicMock:
        job = MagicMock()
        job.id = _JOB_ID
        job.repo_name = "sample-repo"
        job.status = status
        job.report_json = {"tech_stack": ["Python"]}
        return job

    def _make_db(self) -> MagicMock:
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    async def test_raises_repo_not_found_when_job_missing(self):
        """repo_id에 해당하는 AnalysisJob이 없으면 RepoNotFoundError를 발생시켜야 한다."""
        from app.gen.service import validate_and_queue_doc_generation

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            db = self._make_db()
            bg = MagicMock()
            with self.assertRaises(RepoNotFoundError):
                await validate_and_queue_doc_generation(db, _REPO_ID, False, bg)

    async def test_raises_in_progress_when_already_running(self):
        """가이드북 생성이 진행 중이면 DocsGenerationInProgressError를 발생시켜야 한다."""
        from app.gen.service import validate_and_queue_doc_generation

        bg_module._DOCS_GENERATION_IN_PROGRESS.add(str(_REPO_ID))
        try:
            with patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ):
                db = self._make_db()
                bg = MagicMock()
                with self.assertRaises(DocsGenerationInProgressError):
                    await validate_and_queue_doc_generation(db, _REPO_ID, False, bg)
        finally:
            bg_module._DOCS_GENERATION_IN_PROGRESS.discard(str(_REPO_ID))

    async def test_raises_already_exists_when_force_false(self):
        """기존 문서가 있고 force=False이면 DocsAlreadyExistsError를 발생시켜야 한다."""
        from app.gen.service import validate_and_queue_doc_generation

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_latest_version",
                new=AsyncMock(return_value=1),
            ),
        ):
            db = self._make_db()
            bg = MagicMock()
            with self.assertRaises(DocsAlreadyExistsError):
                await validate_and_queue_doc_generation(db, _REPO_ID, False, bg)

    async def test_no_already_exists_error_when_force_true(self):
        """기존 문서가 있어도 force=True이면 DocsAlreadyExistsError가 발생하지 않아야 한다."""
        from app.gen.service import validate_and_queue_doc_generation

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_latest_version",
                new=AsyncMock(return_value=1),
            ),
            patch("app.gen.service.get_settings", return_value=MagicMock(CLONE_BASE_DIR="/tmp")),
        ):
            db = self._make_db()
            bg = MagicMock()
            bg.add_task = MagicMock()
            ## DocsAlreadyExistsError 없이 정상 처리되어야 함
            job_id, version = await validate_and_queue_doc_generation(db, _REPO_ID, True, bg)
            self.assertEqual(job_id, _JOB_ID)
            self.assertEqual(version, 2)

    async def test_raises_analysis_not_completed(self):
        """AnalysisJob.status가 COMPLETED가 아니면 AnalysisNotCompletedError를 발생시켜야 한다."""
        from app.gen.service import validate_and_queue_doc_generation

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job(status="IN_PROGRESS")),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_latest_version",
                new=AsyncMock(return_value=0),
            ),
        ):
            db = self._make_db()
            bg = MagicMock()
            with self.assertRaises(AnalysisNotCompletedError):
                await validate_and_queue_doc_generation(db, _REPO_ID, False, bg)

    async def test_success_returns_job_id_and_version(self):
        """모든 검증 통과 시 (job_id, next_version) 튜플을 반환해야 한다."""
        from app.gen.service import validate_and_queue_doc_generation

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_latest_version",
                new=AsyncMock(return_value=0),
            ),
            patch("app.gen.service.get_settings", return_value=MagicMock(CLONE_BASE_DIR="/tmp")),
        ):
            db = self._make_db()
            bg = MagicMock()
            bg.add_task = MagicMock()
            job_id, version = await validate_and_queue_doc_generation(db, _REPO_ID, False, bg)

        self.assertEqual(job_id, _JOB_ID)
        self.assertEqual(version, 1)

    async def test_success_adds_background_task(self):
        """검증 통과 시 BackgroundTasks.add_task가 호출되어야 한다."""
        from app.gen.service import validate_and_queue_doc_generation

        with (
            patch(
                "app.gen.service.GenDocRepository.get_repo_by_id",
                new=AsyncMock(return_value=self._make_analysis_job()),
            ),
            patch(
                "app.gen.service.GenDocRepository.get_latest_version",
                new=AsyncMock(return_value=0),
            ),
            patch("app.gen.service.get_settings", return_value=MagicMock(CLONE_BASE_DIR="/tmp")),
        ):
            db = self._make_db()
            bg = MagicMock()
            bg.add_task = MagicMock()
            await validate_and_queue_doc_generation(db, _REPO_ID, False, bg)

        bg.add_task.assert_called_once()


# ──────────────────────────────────────────────────────────────
# 7. 라우터 엔드포인트 검증 (FastAPI TestClient)
# ──────────────────────────────────────────────────────────────

class GenTriggerRouterTests(unittest.TestCase):
    """DOCS-GEN-API-002 엔드포인트 HTTP 응답 검증"""

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

    def _body(self, **overrides):
        base = {"force": False}
        base.update(overrides)
        return base

    def test_202_success(self):
        """검증 통과 시 202와 jobId/repoId/status를 반환해야 한다."""
        with patch(
            "app.gen.router.validate_and_queue_doc_generation",
            new=AsyncMock(return_value=(_JOB_ID, 1)),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}",
                json=self._body(),
            )

        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        self.assertEqual(body["code"], 202)
        self.assertEqual(body["message"], "accepted")
        self.assertIn("jobId", body["data"])
        self.assertIn("repoId", body["data"])
        self.assertEqual(body["data"]["status"], "docs_queued")

    def test_404_repo_not_found(self):
        """RepoNotFoundError 발생 시 404 / REPO_NOT_FOUND를 반환해야 한다."""
        with patch(
            "app.gen.router.validate_and_queue_doc_generation",
            new=AsyncMock(side_effect=RepoNotFoundError()),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}",
                json=self._body(),
            )

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "REPO_NOT_FOUND")

    def test_409_docs_already_exists(self):
        """DocsAlreadyExistsError 발생 시 409 / DOCS_ALREADY_EXISTS를 반환해야 한다."""
        with patch(
            "app.gen.router.validate_and_queue_doc_generation",
            new=AsyncMock(side_effect=DocsAlreadyExistsError()),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}",
                json=self._body(),
            )

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["error"]["code"], "DOCS_ALREADY_EXISTS")

    def test_409_generation_in_progress(self):
        """DocsGenerationInProgressError 발생 시 409 / DOCS_GENERATION_IN_PROGRESS를 반환해야 한다."""
        with patch(
            "app.gen.router.validate_and_queue_doc_generation",
            new=AsyncMock(side_effect=DocsGenerationInProgressError()),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}",
                json=self._body(),
            )

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["error"]["code"], "DOCS_GENERATION_IN_PROGRESS")

    def test_422_analysis_not_completed(self):
        """AnalysisNotCompletedError 발생 시 422 / ANALYSIS_NOT_COMPLETED를 반환해야 한다."""
        with patch(
            "app.gen.router.validate_and_queue_doc_generation",
            new=AsyncMock(side_effect=AnalysisNotCompletedError()),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}",
                json=self._body(),
            )

        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"]["code"], "ANALYSIS_NOT_COMPLETED")

    def test_invalid_repo_id_format_returns_422(self):
        """repo_id가 UUID 형식이 아니면 422를 반환해야 한다."""
        resp = self.client.post(
            "/api/gen/docs/not-a-uuid",
            json=self._body(),
        )
        self.assertEqual(resp.status_code, 422)


# ──────────────────────────────────────────────────────────────
# 8. 정적 분석 Self 리뷰 자동화 테스트
# ──────────────────────────────────────────────────────────────

class GenTriggerStaticAnalysisTests(unittest.TestCase):
    """CLAUDE.md §7 정적 분석 Self 리뷰 자동화"""

    def test_background_module_importable(self):
        """app.gen.background가 정상 임포트 가능해야 한다."""
        import app.gen.background as m
        self.assertTrue(hasattr(m, "run_doc_generation"))
        self.assertTrue(hasattr(m, "is_generation_in_progress"))

    def test_markdown_module_importable(self):
        """app.gen.markdown이 정상 임포트 가능해야 한다."""
        import app.gen.markdown as m
        self.assertTrue(hasattr(m, "master_report_to_markdown"))

    def test_new_exceptions_in_common(self):
        """신규 예외 4종이 common.exceptions에 존재해야 한다."""
        from app.common import exceptions as exc
        for name in [
            "DocsAlreadyExistsError",
            "DocsGenerationInProgressError",
            "AnalysisNotCompletedError",
            "DocsGenerationFailedError",
        ]:
            self.assertTrue(hasattr(exc, name), f"{name}이 common.exceptions에 없습니다.")

    def test_validate_service_is_coroutine(self):
        """validate_and_queue_doc_generation은 async def이어야 한다."""
        import inspect
        from app.gen.service import validate_and_queue_doc_generation
        self.assertTrue(inspect.iscoroutinefunction(validate_and_queue_doc_generation))

    def test_run_doc_generation_is_coroutine(self):
        """run_doc_generation은 async def이어야 한다."""
        import inspect
        from app.gen.background import run_doc_generation
        self.assertTrue(inspect.iscoroutinefunction(run_doc_generation))

    def test_markdown_function_is_sync(self):
        """master_report_to_markdown은 동기 함수여야 한다 (asyncio.to_thread 격리 설계)."""
        import inspect
        self.assertFalse(inspect.iscoroutinefunction(master_report_to_markdown))

    def test_trigger_schemas_in_gen_schemas(self):
        """DocTriggerRequest, DocTriggerData, DocTriggerResponse가 gen.schemas에 존재해야 한다."""
        from app.gen import schemas as sch
        for name in ["DocTriggerRequest", "DocTriggerData", "DocTriggerResponse"]:
            self.assertTrue(hasattr(sch, name), f"{name}이 gen.schemas에 없습니다.")


if __name__ == "__main__":
    unittest.main()
