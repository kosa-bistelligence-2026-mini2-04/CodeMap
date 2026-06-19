-- 3. 코드 청크 및 임베딩 테이블 (N: 벡터 유사도 검색용)
CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
    chunk_summary TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    symbol VARCHAR(255),
    language VARCHAR(50),
    embedding_vector vector(1536), -- text-embedding-3-large 1536차원 설정
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

-- 테이블 소유권 이전
ALTER TABLE code_chunks OWNER TO codemap_service;
