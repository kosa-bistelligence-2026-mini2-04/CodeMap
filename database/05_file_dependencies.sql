-- 4. 파일 간 의존성 관계 테이블 (Fan-in / Fan-out 그래프 구현용)
CREATE TABLE IF NOT EXISTS file_dependencies (
    id UUID PRIMARY KEY,
    source_file_id UUID NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
    target_file_path TEXT NOT NULL, -- 참조(import)하고 있는 대상 파일 경로
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
