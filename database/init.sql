-- PostgreSQL 및 pgvector 스키마 초기화 SQL

-- 1. pgvector Extension 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 소스코드 원문 테이블 (1: 파일 정보 및 원문 저장)
CREATE TABLE IF NOT EXISTS source_files (
    id UUID PRIMARY KEY,
    repo_id UUID NOT NULL,
    file_path TEXT NOT NULL,
    raw_code TEXT,
    file_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. 코드 청크 및 임베딩 테이블 (N: 벡터 유사도 검색용)
CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
    chunk_summary TEXT NOT NULL,
    embedding_vector vector(1536), -- OpenAI text-embedding-3-large 1536차원 기본 설정
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. 파일 간 의존성 관계 테이블 (Fan-in / Fan-out 그래프 구현용)
CREATE TABLE IF NOT EXISTS file_dependencies (
    id UUID PRIMARY KEY,
    source_file_id UUID NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
    target_file_path TEXT NOT NULL, -- 참조(import)하고 있는 대상 파일 경로
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. 인덱스 설정 (Cosine 유사도 검색을 위한 HNSW 인덱스 구축)
CREATE INDEX IF NOT EXISTS code_chunks_vector_idx ON code_chunks USING hnsw (embedding_vector vector_cosine_ops);
