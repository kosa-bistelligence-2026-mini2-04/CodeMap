-- PostgreSQL 및 pgvector 스키마 초기화 SQL

-- 1. pgvector Extension 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 사용자 테이블 (USER)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. 저장소 테이블 (REPOSITORY)
CREATE TABLE IF NOT EXISTS repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    branch VARCHAR(100) DEFAULT 'main',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. 파일 및 디렉토리 노드 테이블 (CODE_NODE)
CREATE TABLE IF NOT EXISTS code_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES code_nodes(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('FILE', 'DIRECTORY')),
    depth INT NOT NULL DEFAULT 0,
    content TEXT,
    summary TEXT,
    embedding vector(1536), -- OpenAI text-embedding-3-large 1536차원 기본 설정
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. 의존성 관계 테이블 (DEPENDENCY)
CREATE TABLE IF NOT EXISTS dependencies (
    source_id UUID NOT NULL REFERENCES code_nodes(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES code_nodes(id) ON DELETE CASCADE,
    type VARCHAR(50) DEFAULT 'import', -- import, require, inject 등
    PRIMARY KEY (source_id, target_id)
);

-- 6. 인덱스 설정
-- (1) pgvector Cosine 유사도 검색용 HNSW 인덱스
CREATE INDEX IF NOT EXISTS code_nodes_vector_idx ON code_nodes USING hnsw (embedding vector_cosine_ops);

-- (2) 의존성 역방향(Target -> Source) 탐색 속도 향상을 위한 인덱스
CREATE INDEX IF NOT EXISTS dependencies_target_idx ON dependencies (target_id);

-- (3) 저장소별 특정 파일 경로 빠르게 검색하기 위한 복합 인덱스
CREATE INDEX IF NOT EXISTS code_nodes_repo_path_idx ON code_nodes (repo_id, path);

-- 7. 서비스용 제한된 권한의 계정 생성 및 권한 부여
-- 이미 존재하는 경우 오류 방지를 위해 DO 블록 사용
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'codemap_service') THEN
        CREATE ROLE codemap_service WITH LOGIN PASSWORD 'codemap';
    END IF;
END
$$;

-- 테이블 및 시퀀스 권한 부여
GRANT CONNECT ON DATABASE codemap TO codemap_service;
GRANT USAGE ON SCHEMA public TO codemap_service;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO codemap_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO codemap_service;

-- 향후 생성될 테이블에 대한 기본 권한 설정
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO codemap_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO codemap_service;
