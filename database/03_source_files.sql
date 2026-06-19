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
