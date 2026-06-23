import os


# ──────────────────────────────────────────────
# setup_env 메인 실행 함수
# ──────────────────────────────────────────────
def main():
    '''
    로컬 개발 환경용 .env 템플릿 파일을 생성하는 스크립트.
    기존 .env 파일이 존재하지 않는 경우에만 작동하며,
    시스템 환경 변수에 GITHUB_TOKEN이 이미 등록되어 있다면 자동으로 바인딩하여 생성합니다.
    '''
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(backend_dir, ".env")

    if os.path.exists(env_path):
        print(f"[Info] .env 파일이 이미 {env_path}에 존재합니다. 생성을 생략합니다.")
        return

    ## 시스템 전역 환경 변수에서 GITHUB_TOKEN을 우선적으로 읽어옵니다.
    global_github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    ## 로컬 개발 및 튜토리얼용 표준 환경 변수 템플릿 구성
    env_content = f"""# ==========================================
# CodeMap Backend Environment Configuration
# ==========================================

# 1. Database Configuration (Match with local DB / Docker Compose)
DB_USER=postgres
DB_PASSWORD=""
DB_HOST=localhost
DB_PORT=5432
DB_NAME=codemap_db
# DATABASE_URL=postgresql://postgres:password@localhost:5432/codemap_db

# 2. Local Workspace / Clone Base Directory
CLONE_BASE_DIR=""
CLONE_BASE_DIR_WINDOWS=C:/temp/codemap/jobs
CLONE_BASE_DIR_UNIX=/tmp/codemap/jobs

# 3. Clone limits & Validation Configurations
CLONE_TIMEOUT_SECONDS=300
MAX_REPO_SIZE_MB=500
MAX_FILE_COUNT=10000
GITHUB_TOKEN="{global_github_token}"

# 4. Debug Mode
DEBUG=true

# 5. OpenAI Configuration
OPENAI_API_KEY=""
OPENAI_MODEL=gpt-4o-mini

# 6. RAG Embedding Configuration
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=1536
EMBEDDING_BATCH_SIZE=100
EMBEDDING_MAX_RETRIES=3
"""

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content)
        print(f"[Success] 새 .env 템플릿 파일이 {env_path}에 생성되었습니다.")
        if global_github_token:
            print(">> [Info] 시스템 환경 변수에서 감지된 GITHUB_TOKEN을 .env 파일에 자동으로 주입했습니다.")
        print(">> 생성된 .env 파일을 열고 필요한 환경 변수(DB_PASSWORD 등)를 알맞게 채워주세요.")
    except Exception as e:
        print(f"[Error] .env 파일 생성 중 오류 발생: {e}")


if __name__ == "__main__":
    main()
