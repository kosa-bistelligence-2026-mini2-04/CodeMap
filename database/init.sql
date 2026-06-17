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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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

-- 동일 저장소 중복 분석 확인을 위한 복합 인덱스
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_repo_branch ON analysis_jobs (repo_url, branch, status);
