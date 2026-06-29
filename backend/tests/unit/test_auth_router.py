"""
PROJECT-AUTH 유닛 테스트 (unittest.TestCase 스타일)

테스트 대상: POST /api/auth/register, /login, /refresh, /logout
Mock 전략: AuthService 전체를 patch하여 DB 없이 라우터 계층만 테스트.
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


class AuthRegisterTests(unittest.TestCase):
    """회원가입 엔드포인트 테스트"""

    def setUp(self):
        self.client = TestClient(app)

    @patch("app.auth.router.AuthService")
    def test_register_success(self, mock_service_class):
        """정상 회원가입 → 201 + userId/email 반환"""
        from app.auth.schemas import RegisterData, RegisterResponse

        mock_svc = mock_service_class.return_value
        mock_svc.register = AsyncMock(
            return_value=RegisterResponse(
                data=RegisterData(userId="test-uuid", email="test@example.com")
            )
        )

        resp = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["code"], 201)
        self.assertEqual(data["data"]["email"], "test@example.com")
        self.assertIn("userId", data["data"])

    @patch("app.auth.router.AuthService")
    def test_register_email_already_exists(self, mock_service_class):
        """중복 이메일 가입 → 200 + success=False + error_code=EMAIL_ALREADY_EXISTS"""
        from app.auth.schemas import RegisterResponse

        mock_svc = mock_service_class.return_value
        mock_svc.register = AsyncMock(
            return_value=RegisterResponse(
                success=False,
                message="이미 가입된 이메일입니다.",
                error_code="EMAIL_ALREADY_EXISTS",
            )
        )

        resp = self.client.post(
            "/api/auth/register",
            json={"email": "exists@example.com", "password": "password123"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error_code"], "EMAIL_ALREADY_EXISTS")

    def test_register_password_too_short(self):
        """비밀번호 8자 미만 → 422 Validation Error"""
        resp = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "short"},
        )
        self.assertEqual(resp.status_code, 422)


class AuthLoginTests(unittest.TestCase):
    """로그인 엔드포인트 테스트"""

    def setUp(self):
        self.client = TestClient(app)

    @patch("app.auth.router.AuthService")
    def test_login_success(self, mock_service_class):
        """정상 로그인 → 200 + accessToken 반환 + refreshToken httpOnly 쿠키 설정"""
        from app.auth.schemas import LoginData, LoginResponse

        mock_svc = mock_service_class.return_value
        response = LoginResponse(
            data=LoginData(
                accessToken="mock-access-token",
                expiresIn=3600,
            )
        )
        object.__setattr__(response, "refresh_token", "mock-refresh-token")
        mock_svc.login = AsyncMock(return_value=response)

        resp = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["code"], 200)
        self.assertIn("accessToken", data["data"])
        self.assertNotIn("refreshToken", data["data"])
        self.assertEqual(data["data"]["expiresIn"], 3600)
        self.assertIn("cm-refresh-token=", resp.headers["set-cookie"])
        self.assertIn("HttpOnly", resp.headers["set-cookie"])

    @patch("app.auth.router.AuthService")
    def test_login_invalid_credentials(self, mock_service_class):
        """잘못된 비밀번호 → 200 + success=False + error_code=INVALID_CREDENTIALS"""
        from app.auth.schemas import LoginResponse

        mock_svc = mock_service_class.return_value
        mock_svc.login = AsyncMock(
            return_value=LoginResponse(
                success=False,
                message="이메일 또는 비밀번호가 올바르지 않습니다.",
                error_code="INVALID_CREDENTIALS",
            )
        )

        resp = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error_code"], "INVALID_CREDENTIALS")


class AuthRefreshTests(unittest.TestCase):
    """토큰 갱신 엔드포인트 테스트"""

    def setUp(self):
        self.client = TestClient(app)

    @patch("app.auth.router.AuthService")
    def test_refresh_success(self, mock_service_class):
        """유효한 Refresh Token cookie → 200 + 새 accessToken 반환 + cookie rotation"""
        from app.auth.schemas import RefreshData, RefreshResponse

        mock_svc = mock_service_class.return_value
        response = RefreshResponse(
            data=RefreshData(
                accessToken="new-access-token",
                expiresIn=3600,
            )
        )
        object.__setattr__(response, "refresh_token", "new-refresh-token")
        mock_svc.refresh = AsyncMock(return_value=response)

        resp = self.client.post(
            "/api/auth/refresh",
            cookies={"cm-refresh-token": "valid-refresh-token"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("accessToken", resp.json()["data"])
        self.assertNotIn("refreshToken", resp.json()["data"])
        self.assertIn("cm-refresh-token=", resp.headers["set-cookie"])

    @patch("app.auth.router.AuthService")
    def test_refresh_invalid_token(self, mock_service_class):
        """만료/위조된 Refresh Token → 401 INVALID_REFRESH_TOKEN"""
        from app.common.exceptions import InvalidRefreshTokenError

        mock_svc = mock_service_class.return_value
        mock_svc.refresh = AsyncMock(side_effect=InvalidRefreshTokenError())

        resp = self.client.post(
            "/api/auth/refresh",
            json={"refreshToken": "expired-token"},
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"]["code"], "INVALID_REFRESH_TOKEN")


class AuthServiceRotationTests(unittest.IsolatedAsyncioTestCase):
    """Refresh Token Rotation 서비스 로직 회귀 테스트"""

    async def test_refresh_rotation_issues_distinct_refresh_token(self):
        """같은 사용자 토큰 갱신 시 새 refreshToken은 기존 토큰과 달라야 한다."""
        from app.auth.service import AuthService, _create_refresh_token

        user_id = uuid4()
        email = "test@example.com"
        old_refresh_token = _create_refresh_token(user_id=str(user_id), email=email)

        service = AuthService(MagicMock())
        service.db.commit = AsyncMock()
        service.repo = MagicMock()
        service.repo.get_refresh_token = AsyncMock(
            return_value=SimpleNamespace(
                user_id=user_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        service.repo.delete_refresh_token = AsyncMock(return_value=1)
        service.repo.save_refresh_token = AsyncMock()

        response = await service.refresh(old_refresh_token)

        self.assertNotEqual(getattr(response, "refresh_token"), old_refresh_token)
        service.repo.save_refresh_token.assert_awaited_once()
        saved_kwargs = service.repo.save_refresh_token.await_args.kwargs
        self.assertEqual(saved_kwargs["user_id"], user_id)
        self.assertEqual(saved_kwargs["token"], getattr(response, "refresh_token"))


class AuthPasswordHashingTests(unittest.TestCase):
    """bcrypt 72 byte 제한을 넘는 비밀번호 처리 회귀 테스트"""

    def test_long_password_hash_and_verify(self):
        from app.auth.service import _hash_password, _verify_password

        password = "가" * 80 + "long-password"
        hashed = _hash_password(password)

        self.assertTrue(_verify_password(password, hashed))
        self.assertFalse(_verify_password(password + "x", hashed))


class AuthLogoutTests(unittest.TestCase):
    """로그아웃 엔드포인트 테스트"""

    def setUp(self):
        self.client = TestClient(app)

    @patch("app.auth.router.AuthService")
    @patch("app.infra.auth.verify_access_token")
    def test_logout_success(self, mock_verify, mock_service_class):
        """유효한 토큰 + Refresh Token → 200 로그아웃 성공"""
        from app.auth.schemas import LogoutResponse

        # JWT 검증 mock (get_current_user 우회)
        mock_verify.return_value = {"sub": "test-uuid", "email": "test@example.com"}

        mock_svc = mock_service_class.return_value
        mock_svc.logout = AsyncMock(return_value=LogoutResponse())

        resp = self.client.post(
            "/api/auth/logout",
            json={"refreshToken": "some-refresh-token"},
            headers={"Authorization": "Bearer valid-access-token"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["code"], 200)

    def test_logout_without_token(self):
        """Authorization 헤더 없음 → 401 UNAUTHORIZED"""
        resp = self.client.post(
            "/api/auth/logout",
            json={"refreshToken": "some-token"},
        )
        self.assertEqual(resp.status_code, 401)


class AuthWithdrawTests(unittest.TestCase):
    """회원 탈퇴 엔드포인트 테스트"""

    def setUp(self):
        self.client = TestClient(app)

    @patch("app.auth.router.AuthService")
    @patch("app.infra.auth.verify_access_token")
    def test_withdraw_invalid_sub_returns_401_envelope(
        self,
        mock_verify,
        mock_service_class,
    ):
        """UUID 형식이 아닌 sub 클레임은 500이 아니라 401 표준 envelope."""
        mock_verify.return_value = {
            "sub": "not-a-uuid",
            "email": "test@example.com",
        }

        resp = self.client.delete(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-sub-token"},
        )

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"]["code"], "UNAUTHORIZED")
        mock_service_class.return_value.withdraw.assert_not_called()


class JwtProtectedListTests(unittest.TestCase):
    """기존 list 엔드포인트에 JWT 보호가 적용되었는지 검증"""

    def setUp(self):
        self.client = TestClient(app)

    def test_list_analysis_no_token_returns_401(self):
        """Authorization 헤더 없이 list 조회 → 401"""
        resp = self.client.get("/api/list/analysis")
        self.assertEqual(resp.status_code, 401)

    def test_list_analysis_invalid_token_returns_401(self):
        """위조된 JWT로 list 조회 → 401"""
        resp = self.client.get(
            "/api/list/analysis",
            headers={"Authorization": "Bearer totally.fake.token"},
        )
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
