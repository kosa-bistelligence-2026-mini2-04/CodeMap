import unittest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.exceptions import build_error_response, register_exception_handlers


class CoreExceptionHandlerTests(unittest.TestCase):
    def _client(self) -> TestClient:
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/auth-required")
        def auth_required():
            raise HTTPException(
                status_code=401,
                detail="인증이 필요합니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        @app.get("/standard-envelope")
        def standard_envelope():
            raise HTTPException(
                status_code=400,
                detail=build_error_response(
                    status_code=400,
                    message="job_id가 UUID 형식이 아닙니다.",
                    error_code="INVALID_JOB_ID",
                    detail="UUID 형식이 아닙니다.",
                    field="job_id",
                    retryable=False,
                ),
                headers={"X-Trace-Id": "trace-1"},
            )

        @app.get("/partial-envelope")
        def partial_envelope():
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "요청 형식이 올바르지 않습니다.",
                    "error": {
                        "code": "INVALID_JOB_ID",
                        "detail": "UUID 형식이 아닙니다.",
                        "field": "job_id",
                        "retryable": False,
                    },
                },
            )

        return TestClient(app)

    def test_http_exception_headers_are_preserved(self):
        response = self._client().get("/auth-required")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("www-authenticate"), "Bearer")

    def test_standard_error_response_headers_are_preserved(self):
        response = self._client().get("/standard-envelope")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers.get("x-trace-id"), "trace-1")
        self.assertEqual(response.json()["error"]["code"], "INVALID_JOB_ID")

    def test_http_exception_error_dict_uses_nested_code(self):
        response = self._client().get("/partial-envelope")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["message"], "요청 형식이 올바르지 않습니다.")
        self.assertEqual(body["error"]["code"], "INVALID_JOB_ID")
        self.assertEqual(body["error"]["detail"], "UUID 형식이 아닙니다.")
        self.assertEqual(body["error"]["field"], "job_id")
        self.assertFalse(body["error"]["retryable"])


if __name__ == "__main__":
    unittest.main()
