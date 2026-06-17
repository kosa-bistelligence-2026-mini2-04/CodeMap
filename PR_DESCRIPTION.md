# 🏷️ PR 제목 (Title)
`feat: DB 스키마 설계, 인프라 자동화 및 92개 기능 단위 스켈레톤 구축`

---

# 📝 PR 본문 (Body)

## 🎯 작업 목적
- PostgreSQL 17 + pgvector 기반의 의존성 관계(Fan-in) 및 코드 청크 벡터 DB 데이터 모델 설계
- 리눅스 및 로컬 개발 환경에서 도커 컨테이너 실행 및 스키마 자동 주입까지 원클릭으로 구동할 수 있는 자동화 스크립트 구축
- 기획서 및 최신 Notion 백업 페이지 명세를 기반으로 전체 개발 가이드 문서(`docs/`) 동기화 및 92개 세분화 기능 명세 작성
- 프로젝트 기능 명세서 상의 92개 원자적 단위 기능(Phase 1: 69개 / Phase 2: 23개)과 1:1 매핑되는 3-Tier(FastAPI) & FSD(React) 구조의 스켈레톤 파일 일괄 생성
- 임시 구성되어 있던 불필요 예제 폴더(`user`, `analysis`) 정리

## ✨ 주요 변경 사항
- [x] **데이터베이스 및 인프라 자동화 (`database/`, `scripts/`)**:
  - `database/init.sql`: pgvector 익스텐션 활성화 및 `source_files`, `code_chunks`, `file_dependencies` 테이블 정의 및 HNSW 인덱스 적용.
  - `scripts/setup_env.sh`: PostgreSQL 17 + pgvector 컨테이너 기동 (최대 커넥션 500, 포트 5432 포워딩, 볼륨 마운트).
  - `scripts/init_db.sh`: `pg_isready`를 활용하여 DB 기동 대기 후 `init.sql` 스키마 자동 주입.
  - `scripts/docker-compose.yml`: 컨테이너 구동 설정 1:1 동기화.
  - `.gitignore`: venv 규칙에 의해 무시되던 최상위 `/scripts/` 폴더를 예외 처리(`!/scripts/`).
- [x] **기능 명세 기반 92개 스켈레톤 파일 생성 (`apps/`)**:
  - **백엔드 (3-Tier)**: 12개 도메인 모듈별 패키지 초기화 파일(`__init__.py`) 및 `router.py`, `service.py`, `repository.py` 생성.
  - **프론트엔드 (FSD)**: 3개 라우팅 페이지(`pages/`) 및 8개 모듈의 ui, api 등 레이어별 컴포넌트/훅 파일(총 19개) 생성 (명세서 항목명을 깔끔한 영문 CamelCase 파일명으로 매핑).
  - **임시 폴더 삭제**: 기존의 예제용 폴더 `user`와 `analysis`는 명세서 기능 목록 범위 밖이므로 삭제 조치했습니다.
- [x] **Notion 기반 문서 고도화 및 치환 (`docs/`)**:
  - `docs/01_Overview/FUNCTIONAL_SPECIFICATION.md`: 세분화 완료된 92개 기능 목록표(Features Table)로 Section 5 전면 업데이트.
  - `docs/01_Overview/PROJECT_CONTEXT.md`: 노션 서비스 소개 내용을 반영하여 프로젝트 개요, 문제 정의, 타깃 사용자 및 아키텍처 흐름도(Mermaid) 명세.
  - `docs/03_Decisions/conventions.md` (신규): Git 커밋, Python PEP 8, 브랜치 명명, PR 컨벤션을 통합한 문서 추가.
  - `CodeCompass` 가칭 표기들을 최종 브랜드명인 **CodeMap**으로 전면 치환 및 동기화.

## 🛠️ 리뷰 및 로컬 테스트 방법

1. **브랜치 체크아웃**:
   ```bash
   git checkout feat/infra-db-and-features
   ```
2. **인프라(DB) 컨테이너 기동 및 스키마 주입 테스트**:
   ```bash
   # setup_env.sh 실행 (컨테이너 기동)
   sh CodeMap/scripts/setup_env.sh
   
   # init_db.sh 실행 (스키마 자동 주입)
   sh CodeMap/scripts/init_db.sh
   ```
3. **스키마 및 스켈레톤 생성 확인**:
   ```bash
   # 생성된 테이블 리스트 확인
   docker exec -it postgresql-17 psql -U codemap -d codemap -c "\dt"
   
   # apps/ 폴더 아래 뼈대 파일 확인
   git status
   ```

## ⚠️ 리뷰어에게 당부하는 점
- `user` 및 `analysis` 임시 예제 폴더가 깔끔히 정리되고, 명세 기반의 92개 스켈레톤 파일(크기 0 Byte)만 누락 없이 제 자리에 배치되었는지 파일 트리 검토를 부탁드립니다.
- `docs/` 내 전체 마크다운 가이드의 최신 Notion 동기화 여부 및 `CodeMap` 브랜드 명칭 일치성을 검토해 주세요.
