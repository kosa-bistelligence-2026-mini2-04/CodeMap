"""
환경 변수 설정 모듈

애플리케이션 전역에서 사용하는 환경 변수를 Pydantic Settings로 관리한다.
DATABASE_URL, CLONE_BASE_DIR, OPENAI_API_KEY 등 핵심 설정값을 .env 파일
또는 시스템 환경 변수에서 읽어온다.
"""

import os
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

# backend/.env 파일의 절대 경로 계산 (실행 디렉토리에 구애받지 않도록 설정)
current_dir = os.path.dirname(os.path.abspath(__file__))  # app/core
backend_dir = os.path.dirname(os.path.dirname(current_dir))  # backend
env_path = os.path.join(backend_dir, ".env")


class Settings(BaseSettings):
    """애플리케이션 환경 설정 클래스"""

    # 데이터베이스 상세 접속 정보 (로그인을 위한 계정 정보 포함)
    DB_USER: str = "codemap_service"
    DB_PASSWORD: str = "codemap"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "codemap"

    # 데이터베이스 연결 URL (PostgreSQL + pgvector)
    DATABASE_URL: str = ""

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
    # 미설정 시 LLM 호출이 스킵되고 휴리스틱으로 폴백된다 (nodes.py 참조).
    # SecretStr 선언으로 로그/출력 시 자동 마스킹 (보안 C-01 대응)
    OPENAI_API_KEY: SecretStr = SecretStr("")

    # [Sec05 - ChatOpenAI] 사용할 OpenAI 모델
    # kosa-langchain-practice/langchain/api/sec05_create_agent/ 참고
    OPENAI_MODEL: str = "gpt-4o-mini"

    # [RAG-EMBED] 임베딩 모델 설정
    # 결정 근거: docs/04_Decisions/EMBEDDING_MODEL_DECISION.md
    # text-embedding-3-large + dimensions=1536: large 모델의 한국어↔영어 의미 검색 강점을
    # 유지하면서 저장공간·pgvector HNSW 인덱스 호환성을 확보하는 절충안
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 1536

    # [RAG-EMBED] 배치 임베딩 처리 설정
    # 배치 크기: 100개 청크 → OpenAI API 오버헤드 최소화 (RAG_EMBED_SPEC.md)
    EMBEDDING_BATCH_SIZE: int = 100

    # [RAG-EMBED] API 호출 실패 시 지수 백오프 재시도 횟수 (RAG_EMBED_SPEC.md)
    EMBEDDING_MAX_RETRIES: int = 3

    # GitHub API 호출 시 사용할 토큰 (미설정 시 빈 문자열)
    GITHUB_TOKEN: str = ""

    model_config = {"env_file": env_path, "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        # 1. DATABASE_URL이 비어있거나 생략된 경우 URL.create()로 동적 조립 (특수문자 이스케이프 대응)
        if not self.DATABASE_URL or not self.DATABASE_URL.strip():
            self.DATABASE_URL = URL.create(
                drivername="postgresql+asyncpg",  # 실제 database.py의 asyncpg 드라이버 기준
                username=self.DB_USER,
                password=self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT,
                database=self.DB_NAME,
            ).render_as_string(hide_password=False)  # 실제 연결에 패스워드가 필요하므로 False 유지
            return self

        # 2. 옛날 postgres:// 스킴을 표준 postgresql:// 로 정정
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)

        # 3. SQLAlchemy URL 파서를 통한 주소의 엄밀한 검증 및 에러 조기 감지
        try:
            parsed_url = make_url(self.DATABASE_URL)
        except ArgumentError as exc:
            raise ValueError("DATABASE_URL 형식이 올바르지 않습니다.") from exc

        if not parsed_url.drivername.startswith("postgresql"):
            raise ValueError("PostgreSQL DATABASE_URL만 사용할 수 있습니다.")

        return self


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스를 반환한다 (캐싱으로 중복 생성 방지)"""
    return Settings()
