import os
import unittest
from unittest.mock import patch
from pydantic import SecretStr
from app.infra.config import Settings


# ──────────────────────────────────────────────
# TestConfigFallback
# ──────────────────────────────────────────────
class TestConfigFallback(unittest.TestCase):
    """
    .env 파일이 존재하지 않는 격리 상황에서 Settings 설정 객체가
    로컬 폴백 기본값들을 이용하여 안전하게 초기화되는지 검증하는 단위 테스트 클래스입니다.
    """

    def test_settings_initialization_without_env_file(self):
        """.env 파일을 로드하지 않는 가상 상황(_env_file=None)에서 정상 기동 및 조립 여부를 단언합니다."""
        # _env_file=None 으로 설정하여 외부 파일 로딩을 차단하고,
        # 1. 시스템 환경 변수를 빈 딕셔너리로 하되 필수 필드만 마스킹하여 순수 코드 레벨 기본값으로 기동을 테스트합니다.
        with patch.dict(os.environ, {"DB_USER": "test_user", "DB_PASSWORD": "test_password"}, clear=True):
            settings = Settings(_env_file=None)
            
            # 1. DB 상세 접속 정보 폴백 검증
            self.assertEqual(settings.DB_USER, "test_user")
            self.assertEqual(settings.DB_PASSWORD.get_secret_value(), "test_password")
            self.assertEqual(settings.DB_HOST, "localhost")
            self.assertEqual(settings.DB_PORT, 5432)
            self.assertEqual(settings.DB_NAME, "codemap_db")

            # 2. OS 플랫폼별 clone base directory 자동 매핑 검증
            if os.name == "nt":
                self.assertEqual(settings.CLONE_BASE_DIR, "C:/temp/codemap/jobs")
            else:
                self.assertEqual(settings.CLONE_BASE_DIR, "/tmp/codemap/jobs")

            # 3. DATABASE_URL 동적 조립 검증
            expected_db_url = "postgresql+asyncpg://test_user:test_password@localhost:5432/codemap_db"
            self.assertEqual(settings.DATABASE_URL.get_secret_value(), expected_db_url)

    def test_settings_accepts_database_url_without_db_detail_fields(self):
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://user:pass@localhost:5432/db"},
            clear=True,
        ):
            settings = Settings(_env_file=None)

        self.assertEqual(
            settings.DATABASE_URL.get_secret_value(),
            "postgresql://user:pass@localhost:5432/db",
        )

    def test_settings_loads_jwt_secret_from_file(self):
        """설정된 키 파일 경로가 실재할 때 파일 내용으로 JWT_SECRET이 정상 덮어써지는지 검증합니다."""
        import tempfile
        
        # 1. 파일이 존재할 때 검증
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8") as tmp:
            tmp.write("custom-file-based-jwt-secret-key-12345\n")
            tmp_path = tmp.name
        
        try:
            settings = Settings(
                _env_file=None, 
                JWT_SECRET_KEY_PATH=tmp_path,
                DATABASE_URL="postgresql://user:pass@localhost/db"
            )
            self.assertEqual(settings.JWT_SECRET, "custom-file-based-jwt-secret-key-12345")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        # 2. 파일이 존재하지 않을 때 (자동 생성 검증)
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        no_file_path = os.path.join(backend_dir, "non_existent_file_path_xyz")

        try:
            settings_no_file = Settings(
                _env_file=None, 
                JWT_SECRET_KEY_PATH=no_file_path,
                DATABASE_URL="postgresql://user:pass@localhost/db"
            )
            self.assertTrue(os.path.exists(no_file_path))
            with open(no_file_path, "r", encoding="utf-8") as f:
                generated_val = f.read().strip()
            self.assertEqual(settings_no_file.JWT_SECRET, generated_val)
        finally:
            if os.path.exists(no_file_path):
                os.remove(no_file_path)

    def test_sync_jwt_secret_with_db_failure_raises_exception(self):
        """DB 키 조회 실패 또는 최종 키가 비어 있을 때 기동 차단(RuntimeError)이 정상 유발되는지 검증합니다."""
        import asyncio
        from app.infra.auth import sync_jwt_secret_with_db, _get_cipher_suite, encrypt_token
        import app.infra.auth as auth_mod
        from unittest.mock import AsyncMock, MagicMock

        # 1. DB 쿼리 에러 발생 시 예외 발생 검증
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        
        # async with conn.begin()에 대응하도록 컨텍스트 매니저 모킹
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction.__aexit__ = AsyncMock(return_value=False)
        mock_conn.begin = MagicMock(return_value=mock_transaction)
        mock_conn.execute.side_effect = Exception("DB Connection Refused")
        
        with patch("app.infra.database.engine", mock_engine):
            with self.assertRaises(RuntimeError) as ctx:
                asyncio.run(sync_jwt_secret_with_db())
            self.assertIn("Database query failed", str(ctx.exception))

        # 2. 대칭키(settings.JWT_SECRET)가 비어 있는 상황에서 Fernet 암호화 레이어 기동 시 fail-open 차단 검증
        with patch("app.infra.auth.settings") as mock_settings:
            mock_settings.JWT_SECRET = ""
            
            # 기존 전역 cipher_suite를 소거하여 lazy 재초기화 유도
            with patch("app.infra.auth._cipher_suite", None):
                with self.assertRaises(RuntimeError) as ctx_empty:
                    encrypt_token("some_payload")
                self.assertIn("JWT 대칭키가 초기화되지 않았거나 빈 값입니다", str(ctx_empty.exception))


if __name__ == "__main__":
    import asyncio
    unittest.main()
