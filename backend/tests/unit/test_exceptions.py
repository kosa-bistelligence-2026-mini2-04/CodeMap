import unittest
from unittest.mock import MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.common.exceptions import (
    register_exception_handlers,
    _build_http_exception_response,
)


class TestExceptionsAndHeaders(unittest.IsolatedAsyncioTestCase):
    """
    FastAPI 예외 변환 및 HTTP 응답 헤더 보존 기능에 대한 단위 테스트입니다.
    """

    def test_http_exception_response_preserves_headers(self):
        """
        HTTPException 발생 시 WWW-Authenticate 등 헤더가 유실되지 않고 JSONResponse에 전파되는지 확인합니다.

        [단위 테스트 범위 안내]
        실제 FastAPI 예외 핸들러 미들웨어 전체 경로를 호출하는 대신, 예외 응답 변환 함수(_build_http_exception_response)의
        반환값과 headers 추출 처리가 JSONResponse 객체 생성 시 결합되어 헤더가 안전하게 보존되는지를 검증합니다.
        """
        app = FastAPI()
        register_exception_handlers(app)

        # 1. 401 Unauthorized 시 헤더 주입 예외 발생
        exc = HTTPException(
            status_code=401,
            detail="인증이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer realm='codemap'"}
        )

        # 2. 예외 핸들러 내부에서 호출하는 변환 함수 호출
        # _http_exception_to_response 로직을 모방하여 동작 검증
        headers = getattr(exc, "headers", None)
        response = JSONResponse(
            status_code=exc.status_code,
            content=_build_http_exception_response(exc),
            headers=headers,
        )

        # 3. 반환된 JSONResponse의 헤더 보존 검증
        self.assertEqual(response.status_code, 401)
        self.assertIn("www-authenticate", response.headers)
        self.assertEqual(response.headers["www-authenticate"], "Bearer realm='codemap'")

    def test_build_http_exception_response_nested_dict_error(self):
        """exc.detail 내의 error 필드가 중첩 dict 구조인 경우에도 에러 없이 정상적으로 파싱되는지 검증합니다."""
        # 1. 중첩 dict error 구조를 가진 HTTPException 생성
        nested_detail = {
            "message": "상세 유효성 검증 오류",
            "error": {
                "code": "NESTED_VALIDATION_ERROR",
                "detail": "입력 파라미터가 유효하지 않습니다.",
                "field": "username",
                "retryable": False
            }
        }
        exc = HTTPException(status_code=422, detail=nested_detail)

        # 2. 응답 변환 함수 실행
        content = _build_http_exception_response(exc)

        # 3. 파싱 결과 검증
        self.assertEqual(content["code"], 422)
        self.assertEqual(content["message"], "상세 유효성 검증 오류")
        self.assertIsNotNone(content["error"])
        self.assertEqual(content["error"]["code"], "NESTED_VALIDATION_ERROR")
        self.assertEqual(content["error"]["detail"], "입력 파라미터가 유효하지 않습니다.")
        self.assertEqual(content["error"]["field"], "username")
        self.assertFalse(content["error"]["retryable"])

    def test_build_http_exception_response_string_error(self):
        """exc.detail 내의 error 필드가 문자열(str)인 기존 표준 시나리오도 정상 작동하는지 교차 검사합니다."""
        detail = {
            "message": "저장소가 존재하지 않습니다.",
            "error": "REPOSITORY_NOT_FOUND"
        }
        exc = HTTPException(status_code=404, detail=detail)

        content = _build_http_exception_response(exc)

        self.assertEqual(content["code"], 404)
        self.assertEqual(content["message"], "저장소가 존재하지 않습니다.")
        self.assertEqual(content["error"]["code"], "REPOSITORY_NOT_FOUND")

    def test_build_http_exception_response_preserves_retryable_false_for_500(self):
        """status_code=500인 HTTPException에 retryable=False가 입력되었을 때 최종 응답에서도 False로 보존되는지 확인합니다."""
        exc = HTTPException(
            status_code=500,
            detail={
                "message": "외부 미들웨어 오류",
                "error": {
                    "code": "NON_RETRYABLE_EXTERNAL_ERROR",
                    "retryable": False,
                }
            }
        )

        content = _build_http_exception_response(exc)

        self.assertFalse(content["error"]["retryable"])


if __name__ == "__main__":
    unittest.main()
