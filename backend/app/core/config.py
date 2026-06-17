"""
환경 변수 설정 모듈

애플리케이션 전역에서 사용하는 환경 변수를 Pydantic Settings로 관리한다.
DATABASE_URL, CLONE_DIR, OPENAI_API_KEY 등 핵심 설정값을 .env 파일
또는 시스템 환경 변수에서 읽어온다.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 환경 설정 클래스"""

    # 데이터베이스 연결 URL (PostgreSQL + pgvector)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/codemap"

    # Git 저장소 clone 시 사용할 임시 디렉토리 경로
    CLONE_BASE_DIR: str = "/tmp/codemap/jobs"

    # Clone 제한 시간 (초)
    CLONE_TIMEOUT_SECONDS: int = 300

    # Clone 전 GitHub API 기준 저장소 최대 용량 (MB)
    MAX_REPO_SIZE_MB: int = 500

    # Clone 후 실제 파일 수 제한
    MAX_FILE_COUNT: int = 10000

    # 애플리케이션 실행 모드
    DEBUG: bool = True

    # [Sec05 - ChatOpenAI] LangChain Agent에서 사용할 OpenAI API 키
    # kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
    # .env에 OPENAI_API_KEY=sk-... 형태로 설정한다.
    # 미설정 시 시뮬레이션 모드로 폴백된다 (nodes.py 소)
    OPENAI_API_KEY: str = ""

    # [Sec05 - ChatOpenAI] 사용할 OpenAI 모델
    # kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
    OPENAI_MODEL: str = "gpt-4o-mini"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스를 반환한다 (캐싱으로 중복 생성 방지)"""
    return Settings()
