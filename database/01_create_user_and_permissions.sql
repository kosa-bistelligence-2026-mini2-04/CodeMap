-- pgvector 활성화 및 계정 생성/권한 부여 (관리자 계정으로 실행)

-- 1. pgvector Extension 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 서비스 전용 권한 및 역할 부여
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
GRANT CREATE ON SCHEMA public TO codemap_service;

-- 기존 테이블이 존재할 경우 소유권을 codemap_service로 이전하여 서비스 계정 DDL/DML 권한을 완벽히 보장
ALTER TABLE IF EXISTS analysis_jobs OWNER TO codemap_service;
ALTER TABLE IF EXISTS source_files OWNER TO codemap_service;
ALTER TABLE IF EXISTS code_chunks OWNER TO codemap_service;
ALTER TABLE IF EXISTS file_dependencies OWNER TO codemap_service;
ALTER TABLE IF EXISTS chat_conversations OWNER TO codemap_service;
ALTER TABLE IF EXISTS chat_messages OWNER TO codemap_service;

-- 기본 권한 설정 (이후 생성될 테이블 자동 권한 매핑)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO codemap_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO codemap_service;
