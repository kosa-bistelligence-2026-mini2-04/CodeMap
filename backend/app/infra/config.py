"""
환경 변수 설정 모듈

애플리케이션 전역에서 사용하는 환경 변수를 Pydantic Settings로 관리한다.
DATABASE_URL, CLONE_BASE_DIR, OPENAI_API_KEY 등 핵심 설정값을 .env 파일
또는 시스템 환경 변수에서 읽어온다.
"""

import os
import re
import json
import subprocess
import urllib.request
import urllib.error
from typing import Optional
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

# backend/.env 파일의 절대 경로 계산 (실행 디렉토리에 구애받지 않도록 설정)
current_dir = os.path.dirname(os.path.abspath(__file__))  # app/infra
backend_dir = os.path.dirname(os.path.dirname(current_dir))  # backend
env_path = os.path.join(backend_dir, ".env")


# ──────────────────────────────────────────────
# GitHub API 기반 Actions Variables 동적 조회 함수
# ──────────────────────────────────────────────
def fetch_github_variables() -> None:
    """
    환경 변수에 GITHUB_TOKEN 및 명시적인 연동 활성화 플래그(FETCH_REMOTE_VARS=true)가 존재하는 경우,
    GitHub 저장소 Actions Variables API를 호출하여 정의된 비민감 환경 변수들을 os.environ에 백필(Backfill)합니다.
    """
    fetch_vars = os.environ.get("FETCH_REMOTE_VARS", "").lower() == "true"
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not fetch_vars or not token:
        return

    owner, repo = "", ""
    try:
        # 로컬 git 설정에서 원격 저장소 주소 획득 시도
        git_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
    except Exception:
        # Git 명령이 불가능하거나 실패한 경우 CI 환경 변수(GITHUB_REPOSITORY) 등 조회
        git_url = os.environ.get("GITHUB_REPOSITORY", "")
        if not git_url:
            return
        owner_repo = git_url.split("/")
        if len(owner_repo) == 2:
            owner, repo = owner_repo
    else:
        # URL 형태 파싱 (https://github.com/owner/repo.git 또는 git@github.com:owner/repo.git)
        match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?", git_url)
        if match:
            owner, repo = match.group(1), match.group(2)

    if not owner or not repo:
        return

    # GitHub Actions Variables API 엔드포인트 호출
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/variables"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "CodeMap-Backend-Config")

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            variables = res_data.get("variables", [])
            for var in variables:
                name = var.get("name")
                value = var.get("value")
                # 환경 변수 및 .env 파일 등에 아직 설정되지 않은 빈 설정 항목만 동적으로 주입
                if name and value is not None and name not in os.environ:
                    os.environ[name] = str(value)
    except urllib.error.URLError as e:
        # API 오류(권한 만료, 403, 404 등) 발생 시 실행 중단 없이 경고 메시지 출력 후 조용히 계속 진행
        print(f"[Warning] GITHUB_TOKEN을 이용한 GitHub Actions Variables 백필 실패: {e}")


# ──────────────────────────────────────────────
# Pydantic Settings 초기화 전 원격 변수 동기화 실행
# ──────────────────────────────────────────────
fetch_github_variables()


class Settings(BaseSettings):
    """애플리케이션 환경 설정 클래스"""

    # 데이터베이스 상세 접속 정보 (로그인을 위한 계정 정보 포함)
    DB_USER: str = ""
    DB_PASSWORD: SecretStr = SecretStr("")
    DB_HOST: str = "localhost"
    DB_PORT: Optional[int] = 5432
    DB_NAME: str = "codemap_db"

    # 데이터베이스 연결 URL (PostgreSQL + pgvector)
    # SecretStr 선언으로 로그/출력 시 자동 마스킹 (보안 정책 대응)
    DATABASE_URL: SecretStr = SecretStr("")

    # Git 저장소 clone 시 사용할 임시 디렉토리 경로
    CLONE_BASE_DIR: str = ""
    CLONE_BASE_DIR_WINDOWS: str = "C:/temp/codemap/jobs"
    CLONE_BASE_DIR_UNIX: str = "/tmp/codemap/jobs"

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

    # Evaluator가 근거 부족 판단 시 허용할 추가 re-plan 횟수
    # 기본 2회: 최초 계획 1회 + 추가 탐색 계획 최대 2회
    AGENT_MAX_REPLANS: int = 2

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

    # ── [PROJECT-AUTH] JWT 인증 설정 ──────────────────────────────────────────
    # 서명 키: 운영 환경에서는 반드시 충분히 긴 랜덤 문자열로 교체할 것
    JWT_SECRET: str = "change-me-in-production-use-long-random-string"
    # 서명 알고리즘 (HS256 고정)
    JWT_ALGORITHM: str = "HS256"
    # Access Token 만료 시간 (분), 기본 60분
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Refresh Token 만료 시간 (일), 기본 7일
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 내부 서버 간 호출 전용 서비스 토큰
    SERVICE_TOKEN: str = "service-token"

    model_config = {
        "env_file": env_path,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "env_file_ignore_missing": True
    }


    # ──────────────────────────────────────────────
    # 데이터베이스 연결 정보 및 복사 디렉토리 조립
    # ──────────────────────────────────────────────
    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        """
        DATABASE_URL 및 CLONE_BASE_DIR 설정값 동적 조립 및 정합성 검증
        """
        # 1. CLONE_BASE_DIR이 비어있거나 생략된 경우 OS 플랫폼별 지정 환경 변수 경로로 자동 조립
        if not self.CLONE_BASE_DIR or not self.CLONE_BASE_DIR.strip():
            if os.name == "nt":
                if not self.CLONE_BASE_DIR_WINDOWS or not self.CLONE_BASE_DIR_WINDOWS.strip():
                    raise ValueError("Windows 환경을 위한 CLONE_BASE_DIR_WINDOWS 설정이 누락되었습니다.")
                self.CLONE_BASE_DIR = self.CLONE_BASE_DIR_WINDOWS.strip()
            else:
                if not self.CLONE_BASE_DIR_UNIX or not self.CLONE_BASE_DIR_UNIX.strip():
                    raise ValueError("Unix/Linux 환경을 위한 CLONE_BASE_DIR_UNIX 설정이 누락되었습니다.")
                self.CLONE_BASE_DIR = self.CLONE_BASE_DIR_UNIX.strip()

        # CLONE_BASE_DIR 경로 정규화 (역슬래시를 슬래시로 통일하고 말미 구분자 제거)
        self.CLONE_BASE_DIR = self.CLONE_BASE_DIR.replace("\\", "/").rstrip("/")

        # 2. DATABASE_URL이 비어있거나 생략된 경우 URL.create()로 동적 조립 (특수문자 이스케이프 대응)
        current_db_url = self.DATABASE_URL.get_secret_value() if isinstance(self.DATABASE_URL, SecretStr) else getattr(self, "DATABASE_URL", "")
        if not current_db_url or not current_db_url.strip():
            if not getattr(self, "DB_USER", None) or not getattr(self, "DB_HOST", None) or not getattr(self, "DB_NAME", None):
                raise ValueError("DATABASE_URL 또는 DB 상세 접속 정보(DB_USER, DB_HOST, DB_NAME)가 설정되지 않았습니다.")
            raw_url = URL.create(
                drivername="postgresql+asyncpg",  # 실제 database.py의 asyncpg 드라이버 기준
                username=self.DB_USER,
                password=self.DB_PASSWORD.get_secret_value() if isinstance(self.DB_PASSWORD, SecretStr) else self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT,
                database=self.DB_NAME,
            ).render_as_string(hide_password=False)  # 실제 연결에 패스워드가 필요하므로 False 유지
            self.DATABASE_URL = SecretStr(raw_url)
            return self

        # 3. 옛날 postgres:// 스킴을 표준 postgresql:// 로 정정
        if current_db_url.startswith("postgres://"):
            current_db_url = current_db_url.replace("postgres://", "postgresql://", 1)
            self.DATABASE_URL = SecretStr(current_db_url)

        # 4. SQLAlchemy URL 파서를 통한 주소의 엄밀한 검증 및 에러 조기 감지
        try:
            parsed_url = make_url(current_db_url)
        except ArgumentError as exc:
            raise ValueError("DATABASE_URL 형식이 올바르지 않습니다.") from exc

        if not parsed_url.drivername.startswith("postgresql"):
            raise ValueError("PostgreSQL DATABASE_URL만 사용할 수 있습니다.")

        return self


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스를 반환한다 (캐싱으로 중복 생성 방지)"""
    return Settings()
