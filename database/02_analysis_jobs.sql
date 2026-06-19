-- 1. 분석 작업 테이블 (프로젝트 등록 및 파이프라인 상태 관리용)
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id UUID PRIMARY KEY,
    repo_url TEXT NOT NULL,
    repo_name VARCHAR(255) NOT NULL,
    owner VARCHAR(255) NOT NULL,
    branch VARCHAR(255) NOT NULL DEFAULT 'main',
    status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS',
    stage VARCHAR(20),
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    model_used VARCHAR(255) NOT NULL DEFAULT 'auto',
    force_refresh BOOLEAN NOT NULL DEFAULT FALSE,
    report_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 스키마 업데이트 검증을 위한 컬럼 추가 보장
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS model_used VARCHAR(255) NOT NULL DEFAULT 'auto';
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS force_refresh BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS report_json JSONB;

-- 분석 작업 상태 조회 성능 향상을 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status ON analysis_jobs (status);

-- 동일 저장소 중복 분석 확인을 위한 일반 인덱스 (기존 유지, 단순 검색용)
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_repo_branch ON analysis_jobs (repo_url, branch, status);

-- 동일 저장소 중복 분석 생성 방지를 위한 부분 유니크 인덱스 (Constraint)
CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_jobs_in_progress
ON analysis_jobs (repo_url, branch)
WHERE status = 'IN_PROGRESS';
