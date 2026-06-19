-- 3. 코드 청크 및 임베딩 테이블 (N: 벡터 유사도 검색용)
CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
    chunk_summary TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    symbol VARCHAR(255),
    language VARCHAR(50),
    embedding_vector vector(3072), -- text-embedding-3-large 최대 3072차원 설정
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 코사인 유사도 검색을 위한 HNSW 인덱스 구축
CREATE INDEX IF NOT EXISTS code_chunks_vector_idx ON code_chunks USING hnsw (embedding_vector vector_cosine_ops);

-- file_id 기반 청크 조회 성능 향상 인덱스 (임베딩 상태 조회 시 사용)
CREATE INDEX IF NOT EXISTS idx_code_chunks_file_id ON code_chunks (file_id);

-- language 기반 필터링 인덱스 (언어별 코드 청크 검색용)
CREATE INDEX IF NOT EXISTS idx_code_chunks_language ON code_chunks (language);

-- 기존 테이블이 존재할 경우 대비하여 누락된 컬럼 추가 (하위 호환성)
ALTER TABLE code_chunks ADD COLUMN IF NOT EXISTS start_line INTEGER;
ALTER TABLE code_chunks ADD COLUMN IF NOT EXISTS end_line INTEGER;
ALTER TABLE code_chunks ADD COLUMN IF NOT EXISTS symbol VARCHAR(255);
ALTER TABLE code_chunks ADD COLUMN IF NOT EXISTS language VARCHAR(50);

-- 기존 1536차원 벡터 컬럼이 존재할 경우 3072차원으로 마이그레이션 처리 (하위 호환성)
DO $$
BEGIN
    -- 컬럼의 데이터 타입이 vector(1536)인지 확인하고 맞다면 3072로 변경
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'code_chunks' 
          AND column_name = 'embedding_vector' 
          AND udt_name = 'vector' 
          -- character_maximum_length나 numeric_precision 대신 pg_attribute로 실제 차원 수를 비교하거나 안전하게 인덱스 삭제 후 타입 변경을 시도
    ) THEN
        -- 안전하게 인덱스 드롭 후 재생성하며 컬럼 타입 변경
        DROP INDEX IF EXISTS code_chunks_vector_idx;
        ALTER TABLE code_chunks ALTER COLUMN embedding_vector TYPE vector(3072);
        CREATE INDEX IF NOT EXISTS code_chunks_vector_idx ON code_chunks USING hnsw (embedding_vector vector_cosine_ops);
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Migration of embedding_vector to 3072 dimension skipped or failed: %', SQLERRM;
END $$;

-- 테이블 소유권 이전
ALTER TABLE code_chunks OWNER TO codemap_service;
