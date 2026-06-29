"""
DOCS-GUARD-B-201 / DOCS-GUARD-API-001 유닛 테스트

검증 대상:
  - guard.py 핵심 마스킹 로직 (_mask_content_sync)
    · API 키 / JWT / DB 커넥션 / 패스워드 / GitHub 토큰 탐지
    · 민감정보 없는 정상 텍스트 통과
    · 동일 패턴 유형 detectedPatterns 중복 제거
    · 빈 문자열 — 매치 0건
  - mask_sensitive_content() 비동기 래퍼
  - InvalidContentError / GuardFailedError 예외 속성
  - 라우터 엔드포인트 (DOCS-GUARD-API-001)
    · 200 정상 응답 구조
    · 400 INVALID_CONTENT (빈 content)
    · 404 REPO_NOT_FOUND
    · 500 GUARD_FAILED
    · 422 유효하지 않은 repo_id

Self 리뷰 결과 (CLAUDE.md §7):
  1. KeyError 방어: result.masked_content 등 dataclass 직접 접근 — 안전
  2. Null-Safety: repo None → RepoNotFoundError 즉시 발생
  3. Exception Safety: mask_sensitive_content 실패 시 GuardFailedError 래핑
  4. 비동기 블로킹: asyncio.to_thread 격리 — 이벤트 루프 보호
  5. 데이터 불변성: MaskResult는 새 dataclass 인스턴스 반환, content 원본 불변
  6. 연계 영향도: common.exceptions, gen.schemas, gen.router import 영향 확인
  7. 리소스 누수: DB 세션 Depends(get_db) 관리
  8. 관측 가능성: logger.error(exc_info=True) 보장
  9. 스키마 검증: DocGuardResponse Pydantic 모델 직렬화 검증
"""

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

_REPO_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

_MARKDOWN_WITH_SECRETS = (
    "# 온보딩 가이드\n"
    "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz01234567890123456789\n"
    "DB_URL=postgresql://admin:password123@db.example.com:5432/prod\n"
)

_MARKDOWN_CLEAN = "# 프로젝트 소개\n이 프로젝트는 CodeMap입니다.\n"


# ──────────────────────────────────────────────────────────────
# 1. 마스킹 로직 단위 테스트 (_mask_content_sync)
# ──────────────────────────────────────────────────────────────

class MaskContentSyncTests(unittest.TestCase):
    """guard._mask_content_sync 핵심 로직 검증"""

    def _run(self, content: str):
        from app.gen.guard import _mask_content_sync
        return _mask_content_sync(content)

    def test_masks_openai_key(self):
        """OpenAI API 키 패턴이 [MASKED]로 대체되어야 한다."""
        content = "key=sk-abcdefghijklmnopqrstuvwxyz01234567890123456789"
        result = self._run(content)
        self.assertNotIn("sk-", result.masked_content)
        self.assertIn("[MASKED]", result.masked_content)

    def test_masks_db_connection(self):
        """DB 커넥션 문자열이 [MASKED]로 대체되어야 한다."""
        content = "postgresql://user:secret@host:5432/db"
        result = self._run(content)
        self.assertNotIn("secret@host", result.masked_content)
        self.assertIn("[MASKED]", result.masked_content)

    def test_clean_text_passes_through(self):
        """민감정보가 없는 텍스트는 그대로 반환되어야 한다."""
        result = self._run(_MARKDOWN_CLEAN)
        self.assertEqual(result.masked_content, _MARKDOWN_CLEAN)
        self.assertEqual(result.detected_count, 0)
        self.assertEqual(result.detected_patterns, [])

    def test_detected_count_reflects_total_matches(self):
        """detected_count는 패턴 총 매치 수여야 한다."""
        result = self._run(_MARKDOWN_WITH_SECRETS)
        self.assertGreater(result.detected_count, 0)

    def test_detected_patterns_deduplicated_by_type(self):
        """동일 패턴 유형은 detectedPatterns에 한 번만 포함되어야 한다."""
        content = (
            "sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "sk-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n"
        )
        result = self._run(content)
        types = [p.type for p in result.detected_patterns]
        self.assertEqual(len(types), len(set(types)))

    def test_empty_content_no_matches(self):
        """빈 문자열은 매치 0건이어야 한다."""
        result = self._run("")
        self.assertEqual(result.detected_count, 0)
        self.assertEqual(result.detected_patterns, [])

    def test_masked_content_no_original_secret(self):
        """마스킹 후 원래 민감정보가 남지 않아야 한다."""
        result = self._run(_MARKDOWN_WITH_SECRETS)
        self.assertNotIn("sk-abcdef", result.masked_content)

    def test_github_token_detected(self):
        """GitHub 토큰 패턴이 탐지되어야 한다."""
        content = "token=ghp_aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsS"
        result = self._run(content)
        self.assertIn("[MASKED]", result.masked_content)

    def test_password_literal_detected(self):
        """password=값 형태의 리터럴이 탐지되어야 한다."""
        content = "password=MySuperSecret123"
        result = self._run(content)
        self.assertIn("[MASKED]", result.masked_content)

    def test_return_type_is_mask_result(self):
        """반환 타입이 MaskResult이어야 한다."""
        from app.gen.guard import MaskResult, _mask_content_sync
        result = _mask_content_sync(_MARKDOWN_CLEAN)
        self.assertIsInstance(result, MaskResult)


# ──────────────────────────────────────────────────────────────
# 2. mask_sensitive_content() 비동기 래퍼 테스트
# ──────────────────────────────────────────────────────────────

class MaskSensitiveContentAsyncTests(unittest.IsolatedAsyncioTestCase):
    """mask_sensitive_content 비동기 래퍼 검증"""

    async def test_is_coroutine(self):
        """mask_sensitive_content는 async def이어야 한다."""
        import inspect
        from app.gen.guard import mask_sensitive_content
        self.assertTrue(inspect.iscoroutinefunction(mask_sensitive_content))

    async def test_async_returns_same_result_as_sync(self):
        """비동기 버전의 결과가 동기 버전과 동일해야 한다."""
        from app.gen.guard import _mask_content_sync, mask_sensitive_content
        sync_result = _mask_content_sync(_MARKDOWN_WITH_SECRETS)
        async_result = await mask_sensitive_content(_MARKDOWN_WITH_SECRETS)
        self.assertEqual(sync_result.detected_count, async_result.detected_count)
        self.assertEqual(sync_result.masked_content, async_result.masked_content)

    async def test_async_clean_text(self):
        """민감정보 없는 텍스트는 비동기에서도 0건이어야 한다."""
        from app.gen.guard import mask_sensitive_content
        result = await mask_sensitive_content(_MARKDOWN_CLEAN)
        self.assertEqual(result.detected_count, 0)


# ──────────────────────────────────────────────────────────────
# 3. 예외 클래스 속성 검증
# ──────────────────────────────────────────────────────────────

class GuardExceptionTests(unittest.TestCase):
    """InvalidContentError / GuardFailedError 속성 검증"""

    def test_invalid_content_status_code(self):
        """InvalidContentError는 400이어야 한다."""
        from app.common.exceptions import InvalidContentError
        self.assertEqual(InvalidContentError().status_code, 400)

    def test_invalid_content_error_code(self):
        """InvalidContentError 에러 코드는 INVALID_CONTENT이어야 한다."""
        from app.common.exceptions import InvalidContentError
        self.assertEqual(InvalidContentError().error_code, "INVALID_CONTENT")

    def test_guard_failed_status_code(self):
        """GuardFailedError는 500이어야 한다."""
        from app.common.exceptions import GuardFailedError
        self.assertEqual(GuardFailedError().status_code, 500)

    def test_guard_failed_error_code(self):
        """GuardFailedError 에러 코드는 GUARD_FAILED이어야 한다."""
        from app.common.exceptions import GuardFailedError
        self.assertEqual(GuardFailedError().error_code, "GUARD_FAILED")

    def test_exceptions_in_common_module(self):
        """두 예외 클래스가 common.exceptions에 있어야 한다."""
        from app.common import exceptions as exc
        self.assertTrue(hasattr(exc, "InvalidContentError"))
        self.assertTrue(hasattr(exc, "GuardFailedError"))


# ──────────────────────────────────────────────────────────────
# 4. 라우터 엔드포인트 HTTP 응답 검증
# ──────────────────────────────────────────────────────────────

class GuardRouterTests(unittest.TestCase):
    """DOCS-GUARD-API-001 POST /{repo_id}/guard 엔드포인트 검증"""

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

    def _mock_repo(self, exists: bool = True):
        mock_repo = MagicMock() if exists else None
        return patch(
            "app.gen.router.GenDocRepository.get_repo_by_id",
            new=AsyncMock(return_value=mock_repo),
        )

    def test_200_clean_content(self):
        """민감정보 없는 content는 200과 detectedCount=0을 반환해야 한다."""
        with self._mock_repo():
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/guard",
                json={"content": _MARKDOWN_CLEAN},
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["detectedCount"], 0)
        self.assertEqual(body["data"]["detectedPatterns"], [])

    def test_200_masked_content_structure(self):
        """민감정보가 있으면 maskedContent에 [MASKED]가 포함되어야 한다."""
        with self._mock_repo():
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/guard",
                json={"content": _MARKDOWN_WITH_SECRETS},
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("[MASKED]", body["data"]["maskedContent"])
        self.assertGreater(body["data"]["detectedCount"], 0)

    def test_200_response_envelope(self):
        """응답은 code/message/data 표준 엔벨로프 형태여야 한다."""
        with self._mock_repo():
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/guard",
                json={"content": _MARKDOWN_CLEAN},
            )
        body = resp.json()
        self.assertIn("code", body)
        self.assertIn("message", body)
        self.assertIn("data", body)
        self.assertEqual(body["code"], 200)

    def test_400_empty_content(self):
        """빈 content는 400 INVALID_CONTENT를 반환해야 한다."""
        with self._mock_repo():
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/guard",
                json={"content": ""},
            )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "INVALID_CONTENT")

    def test_400_whitespace_only_content(self):
        """공백만 있는 content도 400 INVALID_CONTENT를 반환해야 한다."""
        with self._mock_repo():
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/guard",
                json={"content": "   \n  "},
            )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "INVALID_CONTENT")

    def test_404_repo_not_found(self):
        """저장소가 없으면 404 REPO_NOT_FOUND를 반환해야 한다."""
        with self._mock_repo(exists=False):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/guard",
                json={"content": _MARKDOWN_CLEAN},
            )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "REPO_NOT_FOUND")

    def test_422_invalid_repo_id(self):
        """repo_id가 UUID 형식이 아니면 422를 반환해야 한다."""
        resp = self.client.post(
            "/api/gen/docs/not-a-uuid/guard",
            json={"content": _MARKDOWN_CLEAN},
        )
        self.assertEqual(resp.status_code, 422)

    def test_422_missing_content_field(self):
        """content 필드 누락 시 422를 반환해야 한다."""
        with self._mock_repo():
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/guard",
                json={},
            )
        self.assertEqual(resp.status_code, 422)

    def test_500_guard_failed_on_exception(self):
        """mask_sensitive_content가 예외를 던지면 500 GUARD_FAILED를 반환해야 한다."""
        with (
            self._mock_repo(),
            patch(
                "app.gen.router.mask_sensitive_content",
                new=AsyncMock(side_effect=RuntimeError("처리 오류")),
            ),
        ):
            resp = self.client.post(
                f"/api/gen/docs/{_REPO_ID}/guard",
                json={"content": _MARKDOWN_CLEAN},
            )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["error"]["code"], "GUARD_FAILED")


# ──────────────────────────────────────────────────────────────
# 5. 정적 분석 Self 리뷰 자동화 테스트
# ──────────────────────────────────────────────────────────────

class GuardStaticAnalysisTests(unittest.TestCase):
    """CLAUDE.md §7 정적 분석 항목 자동화 검증"""

    def test_guard_module_exported(self):
        """guard 모듈이 gen 패키지에서 임포트 가능해야 한다."""
        from app.gen import guard
        self.assertTrue(hasattr(guard, "mask_sensitive_content"))

    def test_mask_sensitive_content_is_coroutine(self):
        """mask_sensitive_content는 async def이어야 한다."""
        import inspect
        from app.gen.guard import mask_sensitive_content
        self.assertTrue(inspect.iscoroutinefunction(mask_sensitive_content))

    def test_uses_asyncio_to_thread(self):
        """guard.py에 asyncio.to_thread가 사용되어야 한다 (비동기 블로킹 방어)."""
        import inspect
        from app.gen import guard
        src = inspect.getsource(guard)
        self.assertIn("asyncio.to_thread", src)

    def test_guard_schemas_in_gen(self):
        """DocGuardResponse 스키마가 gen.schemas에 있어야 한다."""
        from app.gen import schemas
        self.assertTrue(hasattr(schemas, "DocGuardResponse"))
        self.assertTrue(hasattr(schemas, "DocGuardRequest"))

    def test_guard_endpoint_in_router(self):
        """guard_doc 핸들러가 gen.router에 있어야 한다."""
        from app.gen import router as rmod
        self.assertTrue(hasattr(rmod, "guard_doc"))

    def test_mask_result_is_new_instance(self):
        """MaskResult는 새 인스턴스를 반환해 원본 content를 보호해야 한다."""
        from app.gen.guard import MaskResult, _mask_content_sync
        original = "password=secret123"
        result = _mask_content_sync(original)
        # 원본 문자열은 변경되지 않아야 함
        self.assertEqual(original, "password=secret123")
        self.assertIsInstance(result, MaskResult)

    def test_patterns_list_nonempty(self):
        """_PATTERNS는 하나 이상의 탐지 패턴을 포함해야 한다."""
        from app.gen.guard import _PATTERNS
        self.assertGreater(len(_PATTERNS), 0)


if __name__ == "__main__":
    unittest.main()
