-- 6. 대화 메시지 테이블
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'quick',
    "references" JSONB NOT NULL DEFAULT '[]'::jsonb, -- references 예약어 큰따옴표 이스케이프 처리
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 메시지 히스토리 순서별 조회 최적화 인덱스
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages (conversation_id, created_at);
