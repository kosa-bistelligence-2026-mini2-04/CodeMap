-- PostgreSQL 및 pgvector 스키마 초기화 SQL

-- 1. pgvector Extension 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 분석 작업 테이블 (프로젝트 등록 및 파이프라인 상태 관리용)
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id UUID PRIMARY KEY,
    repo_url TEXT NOT NULL,
    repo_name VARCHAR(255) NOT NULL,
    owner VARCHAR(255) NOT NULL,
    branch VARCHAR(255) NOT NULL DEFAULT 'main',
    status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS',
    stage VARCHAR(20),
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    model_used VARCHAR(255) NOT NULL DEFAULT 'auto',
    force_refresh BOOLEAN NOT NULL DEFAULT FALSE,
    report_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS model_used VARCHAR(255) NOT NULL DEFAULT 'auto';
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS force_refresh BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS report_json JSONB;

-- 3. 소스코드 원문 테이블 (1: 파일 정보 및 원문 저장)
CREATE TABLE IF NOT EXISTS source_files (
    id UUID PRIMARY KEY,
    repo_id UUID NOT NULL,
    file_path TEXT NOT NULL,
    raw_code TEXT,
    file_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. 코드 청크 및 임베딩 테이블 (N: 벡터 유사도 검색용)
CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
    chunk_summary TEXT NOT NULL,
    embedding_vector vector(1536), -- OpenAI text-embedding-3-large 1536차원 기본 설정
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. 파일 간 의존성 관계 테이블 (Fan-in / Fan-out 그래프 구현용)
CREATE TABLE IF NOT EXISTS file_dependencies (
    id UUID PRIMARY KEY,
    source_file_id UUID NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
    target_file_path TEXT NOT NULL, -- 참조(import)하고 있는 대상 파일 경로
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. 인덱스 설정
-- 코사인 유사도 검색을 위한 HNSW 인덱스 구축
CREATE INDEX IF NOT EXISTS code_chunks_vector_idx ON code_chunks USING hnsw (embedding_vector vector_cosine_ops);

-- 분석 작업 상태 조회 성능 향상을 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status ON analysis_jobs (status);

-- 동일 저장소 중복 분석 확인을 위한 일반 인덱스 (기존 유지, 단순 검색용)
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_repo_branch ON analysis_jobs (repo_url, branch, status);

-- 동일 저장소 중복 분석 생성 방지를 위한 부분 유니크 인덱스 (Constraint)
CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_jobs_in_progress
ON analysis_jobs (repo_url, branch)
WHERE status = 'IN_PROGRESS';

CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY,
    repo_id UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    title VARCHAR(160) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_conversations_repo ON chat_conversations (repo_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'quick',
    references JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages (conversation_id, created_at);

-- 7. 서비스 전용 권한 및 역할 부여
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'codemap_service') THEN
        CREATE ROLE codemap_service WITH LOGIN PASSWORD 'codemap';
    END IF;
END
$$;

-- 데이터베이스 및 스키마 권한 부여
GRANT CONNECT ON DATABASE codemap TO codemap_service;
GRANT USAGE ON SCHEMA public TO codemap_service;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO codemap_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO codemap_service;

-- 이후 생성될 테이블에 대한 기본 권한 설정
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO codemap_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO codemap_service;
