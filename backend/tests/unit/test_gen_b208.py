"""
DOCS-GEN-B-208 / DOCS-GEN-API-006 유닛 테스트

검증 대상:
  - service._normalize_first_tasks()
    · str 항목 → DocTaskItem(title=str, difficulty="미분류")
    · dict {task, difficulty} 항목 → DocTaskItem 변환
    · dict {title, difficulty} 항목 → DocTaskItem 변환
    · 빈 리스트 → 빈 결과
    · 비어있는 str / None 항목 → 필터링
    · 리스트 아닌 타입(dict, str) → 빈 결과
  - service.get_recommended_tasks()
    · 정상 반환 (tasks 목록 + total 일치)
    · 404 REPO_NOT_FOUND (저장소 없음)
    · 404 DOCS_NOT_FOUND (가이드북 없음)
    · guide.first_tasks 없을 때 빈 목록 반환
  - router GET /{repo_id}/tasks
    · 200 정상 응답 구조 (code/message/data)
    · 404 REPO_NOT_FOUND
    · 404 DOCS_NOT_FOUND
    · 422 유효하지 않은 repo_id

Self 리뷰 결과 (CLAUDE.md §7):
  1. KeyError 방어: report.get("guide") or {} / guide.get("first_tasks") or [] 방어적 조회
  2. Null-Safety: analysis_job / doc None → 즉시 예외 발생
  3. Exception Safety: 서비스 계층은 DB 예외를 DocsNotFoundError / RepoNotFoundError로 전환
  4. 비동기 블로킹: DB I/O는 SQLAlchemy async — 블로킹 없음
  5. 데이터 불변성: DocTaskData는 신규 Pydantic 인스턴스 반환, report_json 원본 불변
  6. 연계 영향도: schemas.py / service.py / router.py import 연계 전체 검증
  7. 리소스 누수: DB 세션 Depends(get_db) 컨텍스트 관리
  8. 관측 가능성: logger.info/warning 구조화 로그 확인
  9. 스키마 검증: DocTaskResponse Pydantic 직렬화 검증
"""

import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

_REPO_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

_REPORT_WITH_TASKS = {
    "guide": {
        "first_tasks": [
            "README 업데이트 — 설치 가이드 보완",
            {"task": "단위 테스트 추가", "difficulty": "중"},
            {"title": "린터 설정 정비", "difficulty": "하"},
        ]
    }
}

_REPORT_NO_GUIDE = {
    "summary": "테스트 프로젝트"
}

_REPORT_EMPTY_TASKS = {
    "guide": {"first_tasks": []}
}


# ──────────────────────────────────────────────────────────────
# 1. _normalize_first_tasks 단위 테스트
# ──────────────────────────────────────────────────────────────

class NormalizeFirstTasksTests(unittest.TestCase):
    """service._normalize_first_tasks 정규화 로직 검증"""

    def _norm(self, raw):
        from app.gen.service import _normalize_first_tasks
        return _normalize_first_tasks(raw)

    def test_str_item_returns_title_with_default_difficulty(self):
        """str 항목은 title=str, difficulty='미분류'로 변환되어야 한다."""
        result = self._norm(["README 업데이트"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "README 업데이트")
        self.assertEqual(result[0].difficulty, "미분류")

    def test_dict_with_task_key(self):
        """dict의 task 키가 title로 매핑되어야 한다."""
        result = self._norm([{"task": "테스트 작성", "difficulty": "중"}])
        self.assertEqual(result[0].title, "테스트 작성")
        self.assertEqual(result[0].difficulty, "중")

    def test_dict_with_title_key(self):
        """dict의 title 키가 그대로 사용되어야 한다."""
        result = self._norm([{"title": "린터 설정", "difficulty": "하"}])
        self.assertEqual(result[0].title, "린터 설정")
        self.assertEqual(result[0].difficulty, "하")

    def test_dict_without_difficulty_defaults_to_unclassified(self):
        """difficulty 미제공 시 '미분류'가 기본값이어야 한다."""
        result = self._norm([{"task": "아무 작업"}])
        self.assertEqual(result[0].difficulty, "미분류")

    def test_empty_list_returns_empty(self):
        """빈 리스트 입력은 빈 결과를 반환해야 한다."""
        self.assertEqual(self._norm([]), [])

    def test_non_list_input_returns_empty(self):
        """리스트가 아닌 타입은 빈 결과를 반환해야 한다."""
        self.assertEqual(self._norm(None), [])
        self.assertEqual(self._norm({}), [])
        self.assertEqual(self._norm("문자열"), [])

    def test_empty_string_item_is_filtered(self):
        """빈 문자열 항목은 필터링되어야 한다."""
        result = self._norm(["", "  ", "유효한 작업"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "유효한 작업")

    def test_dict_missing_title_and_task_is_filtered(self):
        """title/task 키 모두 없는 dict는 필터링되어야 한다."""
        result = self._norm([{"difficulty": "하"}])
        self.assertEqual(result, [])

    def test_mixed_formats_all_converted(self):
        """혼합 형태의 항목들이 모두 올바르게 변환되어야 한다."""
        raw = [
            "str 작업",
            {"task": "dict task 작업", "difficulty": "상"},
            {"title": "dict title 작업"},
        ]
        result = self._norm(raw)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].title, "str 작업")
        self.assertEqual(result[1].difficulty, "상")
        self.assertEqual(result[2].difficulty, "미분류")

    def test_returns_doc_task_item_instances(self):
        """반환값은 DocTaskItem 인스턴스여야 한다."""
        from app.gen.schemas import DocTaskItem
        result = self._norm(["테스트"])
        self.assertIsInstance(result[0], DocTaskItem)


# ──────────────────────────────────────────────────────────────
# 2. get_recommended_tasks 서비스 계층 테스트
# ──────────────────────────────────────────────────────────────

class GetRecommendedTasksTests(unittest.IsolatedAsyncioTestCase):
    """service.get_recommended_tasks 비동기 서비스 검증"""

    def _make_db(self):
        return MagicMock()

    def _mock_repo(self, job_exists=True, doc_exists=True, report=None):
        mock_job = MagicMock() if job_exists else None
        mock_doc = MagicMock() if doc_exists else None
        if mock_doc:
            mock_doc.report_json = report if report is not None else _REPORT_WITH_TASKS

        patcher_job = patch(
            "app.gen.repository.GenDocRepository.get_repo_by_id",
            new=AsyncMock(return_value=mock_job),
        )
        patcher_doc = patch(
            "app.gen.repository.GenDocRepository.get_active_by_repo_id",
            new=AsyncMock(return_value=mock_doc),
        )
        return patcher_job, patcher_doc

    async def test_returns_correct_tasks_and_total(self):
        """정상 케이스: tasks 목록과 total이 일치해야 한다."""
        from app.gen.service import get_recommended_tasks
        p1, p2 = self._mock_repo()
        with p1, p2:
            result = await get_recommended_tasks(self._make_db(), _REPO_ID)
        self.assertEqual(result.total, 3)
        self.assertEqual(len(result.tasks), 3)

    async def test_repo_not_found_raises_404(self):
        """저장소 없으면 RepoNotFoundError(404)가 발생해야 한다."""
        from app.gen.service import get_recommended_tasks
        from app.common.exceptions import RepoNotFoundError
        p1, p2 = self._mock_repo(job_exists=False)
        with p1, p2:
            with self.assertRaises(RepoNotFoundError):
                await get_recommended_tasks(self._make_db(), _REPO_ID)

    async def test_docs_not_found_raises_404(self):
        """가이드북 없으면 DocsNotFoundError(404)가 발생해야 한다."""
        from app.gen.service import get_recommended_tasks
        from app.common.exceptions import DocsNotFoundError
        p1, p2 = self._mock_repo(doc_exists=False)
        with p1, p2:
            with self.assertRaises(DocsNotFoundError):
                await get_recommended_tasks(self._make_db(), _REPO_ID)

    async def test_report_without_guide_returns_empty_tasks(self):
        """guide 없는 report는 빈 tasks를 반환해야 한다."""
        from app.gen.service import get_recommended_tasks
        p1, p2 = self._mock_repo(report=_REPORT_NO_GUIDE)
        with p1, p2:
            result = await get_recommended_tasks(self._make_db(), _REPO_ID)
        self.assertEqual(result.tasks, [])
        self.assertEqual(result.total, 0)

    async def test_empty_first_tasks_returns_zero_total(self):
        """first_tasks 빈 배열이면 total=0이어야 한다."""
        from app.gen.service import get_recommended_tasks
        p1, p2 = self._mock_repo(report=_REPORT_EMPTY_TASKS)
        with p1, p2:
            result = await get_recommended_tasks(self._make_db(), _REPO_ID)
        self.assertEqual(result.total, 0)

    async def test_null_report_json_returns_empty_tasks(self):
        """report_json이 None이면 빈 tasks를 반환해야 한다."""
        from app.gen.service import get_recommended_tasks
        p1, p2 = self._mock_repo(report=None)
        ## doc.report_json을 None으로 설정
        with p1:
            with patch(
                "app.gen.repository.GenDocRepository.get_active_by_repo_id",
                new=AsyncMock(return_value=MagicMock(report_json=None)),
            ):
                result = await get_recommended_tasks(self._make_db(), _REPO_ID)
        self.assertEqual(result.tasks, [])


# ──────────────────────────────────────────────────────────────
# 3. 라우터 HTTP 응답 검증
# ──────────────────────────────────────────────────────────────

class TasksRouterTests(unittest.TestCase):
    """DOCS-GEN-API-006 GET /{repo_id}/tasks 엔드포인트 검증"""

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

        from fastapi.testclient import TestClient
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def _mock_service(self, task_data=None, side_effect=None):
        from app.gen.schemas import DocTaskData, DocTaskItem
        if task_data is None:
            task_data = DocTaskData(
                tasks=[
                    DocTaskItem(title="README 업데이트", difficulty="하"),
                    DocTaskItem(title="테스트 추가", difficulty="중"),
                ],
                total=2,
            )
        if side_effect:
            return patch(
                "app.gen.router.get_recommended_tasks",
                new=AsyncMock(side_effect=side_effect),
            )
        return patch(
            "app.gen.router.get_recommended_tasks",
            new=AsyncMock(return_value=task_data),
        )

    def test_200_response_structure(self):
        """200 응답은 code/message/data 표준 엔벨로프여야 한다."""
        with self._mock_service():
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/tasks")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("code", body)
        self.assertIn("message", body)
        self.assertIn("data", body)
        self.assertEqual(body["code"], 200)

    def test_200_data_has_tasks_and_total(self):
        """data 필드에 tasks 배열과 total 정수가 있어야 한다."""
        with self._mock_service():
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/tasks")
        data = resp.json()["data"]
        self.assertIn("tasks", data)
        self.assertIn("total", data)
        self.assertIsInstance(data["tasks"], list)
        self.assertEqual(data["total"], 2)

    def test_200_task_item_has_title_and_difficulty(self):
        """각 task 항목은 title과 difficulty 필드를 가져야 한다."""
        with self._mock_service():
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/tasks")
        task = resp.json()["data"]["tasks"][0]
        self.assertIn("title", task)
        self.assertIn("difficulty", task)

    def test_200_empty_tasks(self):
        """tasks가 빈 배열이어도 200이 반환되어야 한다."""
        from app.gen.schemas import DocTaskData
        empty_data = DocTaskData(tasks=[], total=0)
        with self._mock_service(task_data=empty_data):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/tasks")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["total"], 0)

    def test_404_repo_not_found(self):
        """저장소 없으면 404 REPO_NOT_FOUND를 반환해야 한다."""
        from app.common.exceptions import RepoNotFoundError
        with self._mock_service(side_effect=RepoNotFoundError()):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/tasks")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "REPO_NOT_FOUND")

    def test_404_docs_not_found(self):
        """가이드북 없으면 404 DOCS_NOT_FOUND를 반환해야 한다."""
        from app.common.exceptions import DocsNotFoundError
        with self._mock_service(side_effect=DocsNotFoundError()):
            resp = self.client.get(f"/api/gen/docs/{_REPO_ID}/tasks")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "DOCS_NOT_FOUND")

    def test_422_invalid_repo_id(self):
        """UUID 형식이 아닌 repo_id는 422를 반환해야 한다."""
        resp = self.client.get("/api/gen/docs/not-a-uuid/tasks")
        self.assertEqual(resp.status_code, 422)


# ──────────────────────────────────────────────────────────────
# 4. 스키마 속성 검증
# ──────────────────────────────────────────────────────────────

class TaskSchemaTests(unittest.TestCase):
    """DocTaskItem / DocTaskData / DocTaskResponse 스키마 검증"""

    def test_task_item_default_difficulty(self):
        """DocTaskItem difficulty 기본값은 '미분류'여야 한다."""
        from app.gen.schemas import DocTaskItem
        item = DocTaskItem(title="작업 1")
        self.assertEqual(item.difficulty, "미분류")

    def test_task_data_total_matches_tasks_length(self):
        """DocTaskData total은 tasks 배열 길이와 같아야 한다."""
        from app.gen.schemas import DocTaskData, DocTaskItem
        items = [DocTaskItem(title=f"작업 {i}") for i in range(3)]
        data = DocTaskData(tasks=items, total=len(items))
        self.assertEqual(data.total, 3)

    def test_task_response_default_code_and_message(self):
        """DocTaskResponse 기본값: code=200, message='success'."""
        from app.gen.schemas import DocTaskData, DocTaskResponse
        resp = DocTaskResponse(data=DocTaskData(tasks=[], total=0))
        self.assertEqual(resp.code, 200)
        self.assertEqual(resp.message, "success")

    def test_schemas_in_gen_module(self):
        """DocTaskItem/Data/Response가 gen.schemas에 있어야 한다."""
        from app.gen import schemas
        self.assertTrue(hasattr(schemas, "DocTaskItem"))
        self.assertTrue(hasattr(schemas, "DocTaskData"))
        self.assertTrue(hasattr(schemas, "DocTaskResponse"))


# ──────────────────────────────────────────────────────────────
# 5. 정적 분석 Self 리뷰 자동화 테스트
# ──────────────────────────────────────────────────────────────

class B208StaticAnalysisTests(unittest.TestCase):
    """CLAUDE.md §7 정적 분석 항목 자동화 검증"""

    def test_get_tasks_handler_in_router(self):
        """get_tasks 핸들러가 gen.router에 있어야 한다."""
        from app.gen import router as rmod
        self.assertTrue(hasattr(rmod, "get_tasks"))

    def test_get_recommended_tasks_is_coroutine(self):
        """get_recommended_tasks는 async def이어야 한다."""
        import inspect
        from app.gen.service import get_recommended_tasks
        self.assertTrue(inspect.iscoroutinefunction(get_recommended_tasks))

    def test_normalize_first_tasks_is_pure_sync(self):
        """_normalize_first_tasks는 동기 순수 함수여야 한다."""
        import inspect
        from app.gen.service import _normalize_first_tasks
        self.assertFalse(inspect.iscoroutinefunction(_normalize_first_tasks))

    def test_defensive_get_in_service(self):
        """service.py에서 report.get('guide') 방어적 조회가 있어야 한다."""
        import inspect
        from app.gen import service
        src = inspect.getsource(service.get_recommended_tasks)
        self.assertIn('.get("guide")', src)
        self.assertIn('.get("first_tasks")', src)


if __name__ == "__main__":
    unittest.main()
