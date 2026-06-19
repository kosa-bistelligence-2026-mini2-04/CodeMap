-- 3. 코드 청크 및 임베딩 테이블 (N: 벡터 유사도 검색용)
CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
    chunk_summary TEXT NOT NULL,
    embedding_vector vector(3072), -- OpenAI text-embedding-3-large 3072차원 기본 설정
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 코사인 유사도 검색을 위한 HNSW 인덱스 구축
CREATE INDEX IF NOT EXISTS code_chunks_vector_idx ON code_chunks USING hnsw (embedding_vector vector_cosine_ops);
