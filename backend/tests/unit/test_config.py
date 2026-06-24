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


if __name__ == "__main__":
    unittest.main()
