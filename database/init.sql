-- PostgreSQL 및 pgvector 스키마 통합 초기화 마스터 SQL
-- 개별 파일들을 psql 환경에서 순서대로 동적 포함하여 실행합니다.

-- 1. 계정 생성 및 권한 설정
\i 01_create_user_and_permissions.sql

-- 2. 분석 작업 테이블 생성
\i 02_analysis_jobs.sql

-- 3. 소스코드 원본 테이블 생성
\i 03_source_files.sql

-- 4. 코드 청크 및 임베딩 테이블 생성
\i 04_code_chunks.sql

-- 5. 파일 의존성 테이블 생성
\i 05_file_dependencies.sql

-- 6. 대화 세션 테이블 생성
\i 06_chat_conversations.sql

-- 7. 대화 메시지 테이블 생성
\i 07_chat_messages.sql
