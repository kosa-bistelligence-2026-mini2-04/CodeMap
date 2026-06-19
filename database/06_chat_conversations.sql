-- 5. 대화 세션 테이블
CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY,
    repo_id UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    title VARCHAR(160) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 대화 세션 역순 조회 최적화 인덱스
CREATE INDEX IF NOT EXISTS idx_chat_conversations_repo ON chat_conversations (repo_id, updated_at DESC);
