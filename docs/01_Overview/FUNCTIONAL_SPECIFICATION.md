# 🚀 CodeMap: AI 코드베이스 온보딩 도우미 — GitHub 레포 분석 RAG 서비스

## 🌟 Executive Summary
GitHub 레포 URL을 입력하면 README, 폴더 구조, 핵심 파일, 실행 방법, 처음 읽을 순서를 분석해서 **"신입 개발자용 온보딩 문서"를 자동 생성**하는 FastAPI(Python 3.12) + React 19 기반 LLM 웹앱입니다.

### 문제 정의 — 왜 필요한가
* 처음 보는 레포는 README만으로 전체 구조를 이해하기 어렵습니다.
* 팀 프로젝트에서 "어떤 파일부터 봐야 하는지", "어떻게 실행하는지", "핵심 로직이 어디 있는지" 찾는 데 시간이 많이 듭니다.
* 단순 챗봇이 아니라 실제 개발자가 바로 쓸 수 있는 온보딩/문서화 도구로 제품성이 있습니다.

---

## 📂 프로젝트 이름 후보 리스트
최종 채택된 프로젝트 명은 **CodeMap** 입니다. 아래는 기획 단계에서 제안되었던 이름 후보 목록입니다.

| 이름 | 한국어 어감 | 영어 어감 | 직관성 | 기억용이성 | 프로젝트 성격 반영 | 차별성 | 총평 |
|---|---|---|---|---|---|---|---|
| **AskRepo AI** | “레포에 물어본다”가 바로 이해됨 | 자연스럽고 짧음 | 5 | 5 | 4 | 3 | Q&A 기능은 매우 잘 드러나지만 온보딩/분석보다 질문 서비스 느낌이 강함 |
| **RepoTalk AI** | 레포와 대화한다는 느낌 | 부드럽고 서비스명 같음 | 4 | 5 | 3 | 3 | 친근하지만 챗봇 이미지가 강함 |
| **CodeTalk AI** | 코드와 대화한다는 의미가 쉬움 | 자연스러움 | 4 | 5 | 3 | 3 | 범용 코드 챗봇처럼 보여 레포 온보딩 특화성이 약함 |
| **RepoChat AI** | 레포 챗봇 느낌 | 매우 직관적 | 5 | 4 | 3 | 2 | 기능은 바로 보이지만 너무 챗봇 중심으로 들림 |
| **CodeChat AI** | 코드 챗봇 느낌 | 흔한 편 | 5 | 4 | 2 | 2 | 일반적인 코드 챗 서비스처럼 보임 |
| **CodeMap AI** | 코드 지도를 만든다는 느낌 | 짧고 제품명 같음 | 4 | 5 | 5 | 4 | 구조 분석/파일 탐색 성격이 잘 맞음 |
| **RepoMap AI** | 레포 지도를 만든다는 느낌 | 간결함 | 4 | 5 | 5 | 4 | GitHub 레포 분석 서비스라는 범위가 CodeMap보다 명확함 |
| **Code Compass** | 코드 나침반, 방향 안내 느낌 | 세련되고 안정적 | 4 | 4 | 5 | 4 | 온보딩/탐색/가이드 성격이 잘 살아남 |
| **DevCompass** | 개발자 나침반 느낌 | 자연스럽고 브랜드감 있음 | 3 | 4 | 4 | 4 | 개발자 도구 느낌은 좋지만 레포 분석이 직접 드러나진 않음 |
| **GitPilot** | Git을 조종/안내한다는 느낌 | 강하고 개발자스러움 | 4 | 5 | 4 | 4 | 이름은 좋지만 Git 자체 기능 도구로 오해될 수 있음 |
| **CodePilot** | 코드 작업을 안내하는 느낌 | 익숙하고 강함 | 4 | 5 | 4 | 3 | 좋은 이름이지만 Copilot 연상과 범용성 때문에 특화성이 약간 흐림 |
| **RepoMate** | 레포를 같이 봐주는 동료 느낌 | 친근하고 짧음 | 4 | 5 | 4 | 4 | 온보딩 도우미 이미지가 좋고 부담 없음 |
| **CodeMate** | 코드 동료 느낌 | 자연스럽고 친근함 | 4 | 5 | 3 | 3 | 범용 개발 보조 도구처럼 보임 |
| **GitMate** | Git 동료 느낌 | 짧고 귀여움 | 3 | 5 | 3 | 3 | Git 명령/브랜치 도구로 오해될 수 있음 |
| **DevMate** | 개발자 동료 느낌 | 친근함 | 3 | 5 | 3 | 3 | 넓은 개발 보조 서비스 느낌, 레포 분석 특화성은 약함 |
| **RepoGuide** | 레포 길잡이 느낌 | 매우 명확함 | 5 | 4 | 5 | 3 | 기능 설명력 최고. 다만 브랜드명으로는 조금 평범함 |
| **CodeGuide** | 코드 길잡이 느낌 | 자연스럽고 안정적 | 4 | 4 | 4 | 3 | 무난하지만 범용 코드 학습/문서 서비스처럼 보일 수 있음 |
| **RepoNavigator** | 레포 탐색기/길찾기 느낌 | 의미가 정확함 | 5 | 3 | 5 | 4 | 프로젝트 성격은 잘 맞지만 이름이 길어서 기억성은 낮음 |
| **CodeNavigator** | 코드 탐색기 느낌 | 전문적이고 명확함 | 4 | 3 | 4 | 4 | 구조 탐색 도구 느낌이 좋지만 다소 길고 무거움 |

---

## 🏗️ 시스템 아키텍처 및 파이프라인
본 프로젝트는 대규모 확장성과 팀 협업 효율을 극대화하기 위해, 프론트엔드와 백엔드 모두 철저한 **도메인(기능) 주도 설계(Domain-Driven Design)**를 따르는 모노레포(Monorepo) 구조로 구성되었습니다.

### 1. 전체 아키텍처 흐름도
(추후 다이어그램 첨부 예정)

### 2. 프로젝트 디렉토리 구조 (Monorepo)
```plain text
CodeMap/
├── apps/
│   ├── frontend/                 # React 19 (Bulletproof React & FSD 패턴)
│   │   ├── src/
│   │   │   ├── common/           # [공통 영역] 버튼, 모달, 유틸, 훅 등 순수 재사용 요소
│   │   │   ├── features/         # [도메인 영역] 도메인 특화 컴포넌트, 훅, API 통신 로직
│   │   │   └── pages/            # [라우팅 영역] 로직 없이 조각들을 화면에 배치만 하는 레고 조립판
│   │   └── vite.config.js        # Vite 및 로컬 HTTPS(mkcert) 설정
│   └── backend/                  # FastAPI - Python 3.12 (3-Tier 아키텍처 적용)
│       ├── app/
│       │   ├── {domain}/         # (예: user, analysis) 기능별 독립 도메인 모듈
│       │   │   ├── router.py     # 📡 API 진입점 (Controller)
│       │   │   ├── service.py    # 🧠 비즈니스 로직 (Service)
│       │   │   ├── repository.py # 🗄️ DB 접근 로직 (DAO / Repository)
│       │   │   ├── schemas.py    # 🚚 데이터 유효성 검증 및 전송 모델 (DTO / Pydantic)
│       │   │   └── models.py     # 🏗️ 데이터베이스 테이블 매핑 (Entity / SQLAlchemy)
│       │   └── main.py           # FastAPI 진입점 및 CORS 설정
│       ├── certs/                # 로컬 HTTPS 통신용 인증서
│       └── requirements.txt
├── database/                     # DB 초기화 및 구성 스크립트 
│   └── init.sql                  # PostgreSQL 테이블 및 pgvector 스키마 초기화 SQL
├── scripts/                      # 인프라 및 서버 환경 자동 구성 스크립트
│   ├── docker-compose.yml        # 🐳 인프라 컨테이너 구성 (PostgreSQL, pgvector 등)
│   ├── setup_env.sh              # 🛠️ 로컬/운영 실행 환경(인증서, 의존성 등) 구축 셸 스크립트
│   └── init_db.sh                # 🔄 DB 마이그레이션 및 컨테이너 초기화 자동 실행 스크립트
└── docs/                         # 아키텍처 및 개발 환경 세팅 가이드
```

### 3. API 및 통신 설계
* 로컬 개발 환경에서 Frontend(포트 5173)와 Backend(포트 8000)는 `mkcert`를 통한 **HTTPS 기반 CORS 통신**을 수행합니다.
* Backend API는 기능별 도메인 모듈 내 `router.py`에 정의되며, FastAPI 라우터 객체를 통해 `main.py`에 통합됩니다.
* `POST /api/analysis` (예시) : GitHub URL 입력 시 처리 시작 및 클론 작업 큐 추가.
* `GET /api/analysis/{repo_id}` : 레포 메타데이터, 상태, 요약 결과 반환.
* `POST /api/chat/{repo_id}` : RAG 기반의 질문 처리 및 소스 파일명 반환.


## 🛠️ 인프라 및 환경 구성 명세 (Infrastructure & Configuration)
기능 명세(F, B)와 분리하여, 프로젝트를 실행하고 유지보수하기 위한 인프라 스크립트 및 환경 구성 요소를 별도로 관리합니다.
* **DB 초기화 명세 (`database/`)**: RAG 파이프라인 구동을 위한 `pgvector` 확장 적용 및 관계형 테이블 설계를 위한 뼈대(init.sql)만 유지합니다. 인위적인 더미 데이터(seed)는 주입하지 않으며, **개발 완료 후 CodeMap 프로젝트 자체를 분석 타겟으로 삼아(Dogfooding) 파이프라인을 직접 테스트하고 데이터를 적재**합니다.
* **환경 설정 자동화 (`scripts/`)**: Docker Compose 파일과 실행 셸 스크립트를 한 곳(`scripts/`)에 모아 두어, 스크립트가 인프라 컨테이너를 구동할 때의 실행 경로 응집도를 극대화했습니다. 개발(로컬), 스테이징, 운영(Production) 등 각 실행 타겟 환경에 맞춰 `.env` 템플릿 복사, 필수 라이브러리 설치, SSL 인증서(`mkcert`) 발급을 한 번에 진행합니다. 신규 개발자 합류 및 서버 배포 시 **명령어 1줄(One-Click)**로 완벽하게 환경이 세팅되도록 보장하여 온보딩(Onboarding) 리소스를 최소화합니다.


---

## 💡 프로젝트 핵심 기능 (Core Features)

### 1. 프로젝트 등록 (Git 클론 및 필터링)
* **기능 개요**: 사용자가 입력한 Git 저장소의 소스코드를 실시간으로 복제하고, 분석에 필요한 정보만 걸러내어 저장.
* **원클릭 저장소 연동**: 브라우저 화면에서 GitHub URL만 입력하면 서버 내부에 실시간 복제.
* **지능형 노이즈 필터링**: `node_modules`, `build`, 바이너리 파일 등을 자동 제외하고, 설정/문서 파일은 보존하여 분석 효율을 극대화합니다.

### 2. 코드 맥락 및 관계망 이해 (RAG 및 코드 임베딩)
* **기능 개요**: 단순 단어 비교 검색을 뛰어넘어, 코드가 갖는 고유한 역할, 설계 의미, 파일 간의 연결 관계를 학습해 의미 기반 사전을 구축.
* **유기적 관계망 지도 구축**: 의존성 및 Import 흐름을 추적하여 논리적 지도를 구성하고 상향식으로 개념을 탐색.
* **자연어 질문 해석**: 평상어 질문 문맥을 파악해 의도에 맞는 소스코드 파일을 정확히 탐색합니다.

### 3. 자율 탐색형 AI 코드 분석 (Agentic Search)
* **기능 개요**: AI 비서가 스스로 계획을 세우고 디렉토리를 열어보며 답을 찾아내는 자율형 탐색 기능.
* **자가 교정(Self-Correction)**: 탐색 실패 시 다른 경로를 탐색하여 오류를 자가 검증. 무한 분석 루프 방지를 위해 최대 5회, 처리 시간 20초로 제한.
* **명확한 출처 제공**: 답변 시 소스코드 파일명과 줄 번호를 제공하여 신뢰성을 확보.

### 4. 계층형 프로젝트 가이드북 자동 생성 (Map-Reduce 문서화)
* **기능 개요**: 방대한 코드를 읽지 않아도 한눈에 파악할 수 있는 고품질의 Markdown 형식 '프로젝트 가이드북'을 자동 집필.
* **상향식 정보 집필**: 개별 소스코드 요약 -> 폴더 요약 -> 마스터 리포트로 융합.
* **아키텍처 시각화**: 저장소 연동 직후 트리, 핵심 데이터 흐름을 시각적으로 제공하여 온보딩 리소스 절감.

---

## 📋 프로젝트 기능명세서

MVP(최소 기능 제품) 구현을 위한 **Phase 1(핵심 기능)**과 이후 점진적으로 도입할 **Phase 2(고도화 추가 기능)**으로 분할하여 관리합니다. 기능 명세서는 사용자에게 직접적인 비즈니스 가치를 제공하는 기능에만 집중하므로, 인프라 구축이나 내부 DB 설계(ERD) 등의 기술적 선행 작업은 명세서에서 제외합니다.

<aside>
🏗️

- 기능 ID 규칙 보기
    
    **[기능 ID 명명 규칙 (Domain-Driven Naming Convention)]**
    작업 할당과 역할 분담의 명확성을 위해 철저한 도메인 주도 설계(DDD)를 기반으로 기능 ID를 부여합니다. 모든 기능의 최종 코드는 `{대분류ID}-{모듈명}-{F/B}-{3자리_번호}` 형식을 따릅니다.
    
    - **대분류 ID**: 비즈니스 도메인 카테고리 (예: `PROJECT`, `RAG`, `AGENT`, `DOCS`)
    - **모듈명**: 도메인 내 세부 서브모듈/폴더명 (예: `REPO`, `PARSE`, `EMBED`, `CHAT`, `CORE`, `SEARCH`, `GEN` 등)
    - **F/B**: 개발 계층 (F: Frontend, B: Backend)
    - **3자리 번호**: 아키텍처 폴더/계층을 매핑하는 3자리 숫자 대역
        - **프론트엔드 (F - FSD 아키텍처 기준)**:
            - `1xx`: Pages / Views (화면 진입점 페이지)
            - `2xx`: UI Components (재사용 및 개별 컴포넌트)
            - `3xx`: API Hooks / Queries (서버 통신 훅)
            - `4xx`: Model / Store (Zustand 등 상태 관리 및 클라이언트 비즈니스 로직)
            - `5xx`: Types / Utils (공통 타입 정의 및 유틸리티)
        - **백엔드 (B - 3-Tier 아키텍처 기준)**:
            - `1xx`: Router (API 엔드포인트 진입점)
            - `2xx`: Service (핵심 비즈니스 로직)
            - `3xx`: Repository (DB CRUD 및 데이터베이스 접근)
            - `4xx`: Schemas (Pydantic Request/Response DTO)
            - `5xx`: Models (SQLAlchemy 테이블 엔티티)
            
    - *예시 (백엔드)*: 프로젝트 등록(`PROJECT`)의 저장소 연동(`REPO`) 백엔드(`B`) Router API 👉 `PROJECT-REPO-B-101`
    - *예시 (프론트엔드)*: 프로젝트 등록(`PROJECT`)의 저장소 연동(`REPO`) 프론트엔드(`F`) UI 입력 폼 👉 `PROJECT-REPO-F-201`
    - *예시 (공통 인프라)*: 챗봇(`AGENT`)의 분석 파이프라인 실패 처리(`CORE`) 백엔드(`B`) Service 👉 `AGENT-CORE-B-204`
</aside>

### 🥇 Phase 1: MVP 핵심 기능 (69개)

| 기능 ID | 카테고리 | 도메인(모듈) | 구분 | 기능명 | 상세 설명 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PROJECT-LIST-B-101` | PROJECT | LIST | Backend | 레포 목록 조회 API | `GET /api/analysis` 전체 분석 이력 목록 반환 |
| `PROJECT-LIST-B-201` | PROJECT | LIST | Backend | 레포 파일 수 및 용량 사전 계산 서비스 | 클론 실행 전에 메타데이터 API 등을 통해 전체 파일 수와 용량을 사전 조회하고 계산하는 로직 |
| `PROJECT-LIST-B-203` | PROJECT | LIST | Backend | 제한 용량 초과 예외 응답 및 경고 서비스 | 사전 검증 또는 클론 후 제한 파일 수(100개) 혹은 용량(100KB) 초과 시 예외 처리 및 에러 스펙 규격 응답 생성 |
| `PROJECT-LIST-F-101` | PROJECT | LIST | Frontend | 분석 이력 목록 화면 | 이미 분석한 레포 목록과 각 분석상태(완료,처리중,실패)를 조회하는 홈화면 |
| `PROJECT-REPO-B-101` | PROJECT | REPO | Backend | 프로젝트 등록 API | `POST /api/analysis` 요청 처리 |
| `PROJECT-REPO-B-201` | PROJECT | REPO | Backend | Git Clone 처리 | 서버 내부 임시 디렉토리에 저장소 복제 |
| `PROJECT-REPO-B-202` | PROJECT | REPO | Backend | 파일 필터링 | `node_modules`, `.git`, `build`, `dist`, 'venv', '.next', '.env', 'key' 바이너리 파일 제외 |
| `PROJECT-REPO-B-203` | PROJECT | REPO | Backend | clone timeout 처리 | timeout seconds 설정, subprocess error capture, 실패 시 cleanup |
| `PROJECT-REPO-B-204` | PROJECT | REPO | Backend | 전체 분석 순서 정의 | clone → code map → doc generation → onboarding guide → report 저장 |
| `PROJECT-REPO-B-205` | PROJECT | REPO | Backend | job별 event queue 관리 | publish, subscribe, timeout, cleanup 구현 |
| `PROJECT-REPO-B-301` | PROJECT | REPO | Backend | GitHub URL 정규식 검증 로직 | 입력받은 URL이 올바른 GitHub 저장소 포맷인지 정규식 패턴 매칭 및 예외 처리 |
| `PROJECT-REPO-B-302` | PROJECT | REPO | Backend | 프로젝트 메타데이터 저장 | repo_name, owner, branch, clone_path 저장 |
| `PROJECT-REPO-B-303` | PROJECT | REPO | Backend | 고유 분석 Job ID 생성기 | 검증 완료 후 분석 작업을 스케줄링하기 위해 UUID 기반의 고유 작업 ID 발급 및 라우팅 |
| `PROJECT-REPO-F-101` | PROJECT | REPO | Frontend | progress WebSocket endpoint 정리 | frontend ProgressPanel에 이벤트 전달, /ws/progress/{job_id} 연결, subscribe, disconnect cleanup |
| `PROJECT-REPO-F-201` | PROJECT | REPO | Frontend | GitHub URL 입력 UI | 사용자가 GitHub 저장소 URL을 입력할 수 있는 입력 폼 제공 |
| `PROJECT-REPO-F-202` | PROJECT | REPO | Frontend | 저장소 분석 요청 버튼 | URL 검증 후 Backend API 호출 |
| `PROJECT-REPO-F-203` | PROJECT | REPO | Frontend | Git Clone 진행률 프로그레스 UI | 소비 파일 복제 진행 과정을 시각적으로 보여주는 프로그레스 바 및 상태 메시지 표시 |
| `PROJECT-REPO-F-204` | PROJECT | REPO | Frontend | AI 코드 분석 진행 상태 UI | 클론 이후 RAG 적재 및 리포트 생성이 비동기로 수행될 때의 단계별 상태 로딩 컴포넌트 |
| `RAG-EMBED-B-201` | RAG | EMBED | Backend | 임베딩 생성 | 코드 및 문서를 벡터화 |
| `RAG-EMBED-B-301` | RAG | EMBED | Backend | pgvector 저장 | 임베딩 및 메타데이터 저장 |
| `RAG-PARSE-B-101` | RAG | PARSE | Backend | 분석 결과 조회 API | `GET /api/analysis/{repo_id}` 반환 |
| `RAG-PARSE-B-201` | RAG | PARSE | Backend | README 분석 | README를 기반으로 프로젝트 목적 및 핵심 기능 추출 |
| `RAG-PARSE-B-202` | RAG | PARSE | Backend | 디렉토리 구조 분석 | 프로젝트 폴더 트리 구조 생성 |
| `RAG-PARSE-B-203` | RAG | PARSE | Backend | 핵심 파일 탐색 | entry point(`main.py`, `App.tsx` 등) 자동 탐색 |
| `RAG-PARSE-B-204` | RAG | PARSE | Backend | 설정 파일 탐색 | `package.json`, `requirements.txt`, `docker-compose` 등 분석 |
| `RAG-PARSE-B-205` | RAG | PARSE | Backend | 실행 방법 추론 | install/run command 자동 생성 |
| `RAG-PARSE-B-206` | RAG | PARSE | Backend | 기술 스택 추론 | package.json, requirements.txt, Dockerfile, docker-compose.yml 기반 프레임워크·런타임 자동 탐지 |
| `RAG-PARSE-B-207` | RAG | PARSE | Backend | AST 기반 코드 청킹 | 함수/클래스 단위 코드 분리 |
| `RAG-PARSE-B-208` | RAG | PARSE | Backend | 파일 간 import 관계 분석 | 의존 파일 목록 추출 [7. CODE-MAP ANALYSIS] AST 청킹, 의존성 트리, 엔트리포인트, 설정파일 종합 분석 파이프라인 간단히 파싱 |
| `RAG-PARSE-B-209` | RAG | PARSE | Backend | 계층형 Bottom-up 요약 로직 | 파일 요약 → 폴더 요약 → 프로젝트 마스터 요약 순서로 상향식 요약 파이프라인 구성 (Tree-based RAG 핵심) |
| `RAG-PARSE-B-210` | RAG | PARSE | Backend | 구조 분석 agent 구현 | 파일 트리, stack, entrypoint, risk, heatmap 결과 반환 |
| `RAG-PARSE-F-201` | RAG | PARSE | Frontend | 구조 분석 결과 표시 UI | 파일 트리·기술 스택·진입점 탐지 결과를 화면에 시각적으로 표시 |
| `AGENT-CHAT-B-101` | AGENT | CHAT | Backend | Repo Chat API | `POST /api/chat/{repo_id}` |
| `AGENT-CHAT-B-201` | AGENT | CHAT | Backend | 코드 컨텍스트 생성 | 관련 파일을 묶어 LLM Context 구성 |
| `AGENT-CHAT-B-202` | AGENT | CHAT | Backend | 에이전트 툴 호출 최대 횟수(5회) 제한 로직 | AI 에이전트가 답변을 생성하기 위해 코드 탐색 도구를 최대 5회까지만 반복 호출하도록 루프를 제약하는 예외 처리 |
| `AGENT-CHAT-B-203` | AGENT | CHAT | Backend | 에이전트 실행 시간(20초) 제한 모니터링 로직 | 에이전트 탐색 시간이 최대 20초를 초과할 경우 즉각 작업을 중단하고 현재까지 탐색된 최선의 정보로 답변을 생성하도록 조율하는 로직 |
| `AGENT-CHAT-F-201` | AGENT | CHAT | Frontend | AI 응답 UI | 답변 및 참조 파일명 표시 |
| `AGENT-CHAT-F-202` | AGENT | CHAT | Frontend | 탐색 루프 횟수/시간 제한 | 에이전트 도구 호출 최대 5회·처리 시간 최대 20초 제한, 초과 시 수집 정보 기반 최선 답변 반환 |
| `AGENT-CHAT-F-203` | AGENT | CHAT | Frontend | 관련 파일 검색 | 벡터 검색 기반 관련 코드 탐색 |
| `AGENT-CHAT-F-204` | AGENT | CHAT | Frontend | 스트리밍 응답 처리 | FastAPI SSE(Server-Sent Events) 기반 LLM 응답 스트리밍 처리 |
| `AGENT-CHAT-F-205` | AGENT | CHAT | Frontend | 답변 스트리밍 UI | LLM 답변을 실시간 스트리밍으로 받아 타이핑 효과로 표시 |
| `AGENT-CHAT-F-206` | AGENT | CHAT | Frontend | 질문 의도 분석 | 자연어 질문 파싱 |
| `AGENT-CORE-B-201` | AGENT | CORE | Backend | agent 시작/완료 이벤트 발행 | agent_status, agent_completed, completed, failed 이벤트 publish |
| `AGENT-CORE-B-202` | AGENT | CORE | Backend | completed/failed 후 cleanup | final event 이후 queue 정리 |
| `AGENT-CORE-B-203` | AGENT | CORE | Backend | agent 실행 시간 측정 | 각 agent start/end timestamp 기록 |
| `AGENT-CORE-B-204` | AGENT | CORE | Backend | agent 실패 처리 | 실패 agent, error message 저장 및 failed event 발행 |
| `AGENT-CORE-F-201` | AGENT | CORE | Frontend | ReportJsonResponse 필드 확정 | summary, stack, file_map, recommendations, heatmap, durations, guide 포함, frontend와 report 계약 고정 |
| `AGENT-SEARCH-B-201` | AGENT | SEARCH | Backend | 자가 교정 탐색 | 탐색 실패 시 최대 5회 재탐색 |
| `AGENT-SEARCH-B-202` | AGENT | SEARCH | Backend | Repo Chat UI | 사용자 질문 입력창 제공 |
| `AGENT-SEARCH-B-203` | AGENT | SEARCH | Backend | LLM 답변 생성 | 프로젝트 맥락 기반 응답 생성 |
| `AGENT-SEARCH-B-204` | AGENT | SEARCH | Backend | 에이전트 탐색 과정 표시 UI | 에이전트가 현재 탐색 중인 파일·단계를 실시간으로 화면에 표시 |
| `AGENT-SEARCH-B-205` | AGENT | SEARCH | Backend | Grep 기반 자연어 매칭 코드 검색 도구 정의 | LLM 에이전트가 소스코드 내 특정 키워드나 정규식 패턴을 검색할 때 호출하는 grep_search 도구 스펙 정의 및 등록 |
| `AGENT-SEARCH-B-206` | AGENT | SEARCH | Backend | 디렉토리 구조 및 개별 파일 조회 도구 정의 | 에이전트가 파일 내용을 열어보거나 폴더 트리를 조회하기 위해 호출하는 read_file, list_dir 도구 정의 및 권한 제어 |
| `DOCS-GEN-B-101` | DOCS | GEN | Backend | 가이드북 조회 API | `GET /api/docs/{repo_id}` 생성된 온보딩 가이드북 Markdown 반환 |
| `DOCS-GEN-B-201` | DOCS | GEN | Backend | 문서 요약 agent 구현 | README, config, package, route 파일 기반 프로젝트 설명 생성 |
| `DOCS-GEN-B-202` | DOCS | GEN | Backend | 온보딩 guide agent 구현 | 읽을 순서, 수정 시작점, 위험 파일, 추천 task 생성 |
| `DOCS-GEN-B-203` | DOCS | GEN | Backend | 폴더 단위 요약 | 하위 파일 요약 기반 디렉토리 설명 생성 |
| `DOCS-GEN-B-204` | DOCS | GEN | Backend | 프로젝트 마스터 리포트 생성 | 최종 온보딩 문서 통합 |
| `DOCS-GEN-B-205` | DOCS | GEN | Backend | README 기반 프로젝트 소개 생성 | 프로젝트 목적 및 핵심 기능 요약 |
| `DOCS-GEN-B-206` | DOCS | GEN | Backend | 핵심 실행 플로우 설명 | 요청 흐름 및 핵심 구조 설명 |
| `DOCS-GEN-B-207` | DOCS | GEN | Backend | 문서 재생성 | 기존 분석 기반 재생성 기능 |
| `DOCS-GEN-B-301` | DOCS | GEN | Backend | Markdown 저장 | 생성 결과 DB 저장 |
| `DOCS-GEN-F-101` | DOCS | GEN | Frontend | 온보딩 문서 화면 | JSON 기반 결과 렌더링 |
| `DOCS-GEN-F-201` | DOCS | GEN | Frontend | Markdown 포맷 내보내기 버튼 UI | 생성 완료된 온보딩 가이드를 로컬 마크다운 파일로 즉시 다운로드하는 버튼 컴포넌트 |
| `DOCS-GEN-F-202` | DOCS | GEN | Frontend | 파일 단위 요약 | 개별 코드 파일 요약 생성 |
| `DOCS-GEN-F-203` | DOCS | GEN | Frontend | 신입 개발자 기준 추천 읽기 순서 렌더러 | 파일 종속성 및 우선순위를 계층적으로 파악하여 신입 개발자에게 권장하는 최적의 파일 가독 순서 렌더링 UI |
| `DOCS-GEN-F-204` | DOCS | GEN | Frontend | PDF 변환 다운로드 버튼 UI | 가이드를 깔끔한 PDF 인쇄 규격으로 변환하여 저장할 수 있게 돕는 다운로드 버튼 및 인쇄 프리뷰 실행 인터랙션 |
| `DOCS-GEN-F-205` | DOCS | GEN | Frontend | 주의/위험 소스코드 및 다음 행동 가이드 경고창 | 설정 파일 유출 위험이나 복잡도가 너무 높은 병목 코드 등 수정 시작 전 주의해야 할 위험 요소를 경고해 주는 모달/경고 카드 컴포넌트 |
| `DOCS-GUARD-B-201` | DOCS | GUARD | Backend | 민감정보 마스킹 | API key, token, password pattern 탐지 시 원문 제거. report 생성 전 report에 민감정보 원문 미노출하도록 검증 |

### 🥈 Phase 2: 고도화 추가 기능 (23개)

| 기능 ID | 카테고리 | 도메인(모듈) | 구분 | 기능명 | 상세 설명 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PROJECT-LIST-B-202` | PROJECT |  | Backend | Service | 프로젝트 목록 조회 및 관리 |
| `PROJECT-LIST-B-301` | PROJECT |  | Backend | Repository | 분석 job metadata 저장 |
| `PROJECT-LIST-F-201` | PROJECT |  | Frontend | UI Component | store에서 최근 job 목록 조회 |
| `PROJECT-LIST-F-202` | PROJECT |  | Frontend | UI Component | job 상태 업데이트 |
| `PROJECT-LIST-F-203` | PROJECT |  | Frontend | UI Component | 실패 job error 저장 |
| `PROJECT-PIPELINE-B-201` | PROJECT |  | Backend | Service | 분석 단계 상태 관리 |
| `PROJECT-PIPELINE-B-202` | PROJECT |  | Backend | Service | 비동기 깊은 분석 파이프라인 |
| `PROJECT-PIPELINE-B-203` | PROJECT |  | Backend | Service | 파이프라인 외부 연동 |
| `PROJECT-PIPELINE-F-201` | PROJECT |  | Frontend | UI Component | 현재 분석 수준 안내 메시지 |
| `PROJECT-PIPELINE-F-202` | PROJECT |  | Frontend | UI Component | 얕은/깊은 분석 분리 프로그레스 UI |
| `PROJECT-PIPELINE-F-301` | PROJECT |  | Frontend | API/Query | 진행률 실시간 수신 |
| `PROJECT-REPO-B-303` | PROJECT |  | Backend | Repository | 중복 저장소 검사 |
| `RAG-GRAPH-B-201` | RAG |  | Backend | Service | 의존성 그래프 시각화 |
| `RAG-GRAPH-F-201` | RAG |  | Frontend | UI Component | 의존성 관계 그래프 UI |
| `RAG-PARSE-B-211` | RAG |  | Backend | Service | 위험 신호 태깅 |
| `RAG-PARSE-B-212` | RAG |  | Backend | Service | 기술 스택 점수화 |
| `RAG-PARSE-F-202` | RAG |  | Frontend | UI Component | heatmap용 risk score 생성 |
| `AGENT-CHAT-B-203` | AGENT |  | Backend | Service | 장기 기억 (Long-term Memory) |
| `AGENT-SEARCH-B-206` | AGENT |  | Backend | Service | 자율 외부 도구 사용 |
| `AGENT-SEARCH-B-207` | AGENT |  | Backend | Service | Advanced Reasoning |
| `DOCS-GEN-B-208` | DOCS |  | Backend | Service | 추천 작업 생성 |
| `DOCS-UTIL-B-201` | DOCS | UTIL | Backend | HTML-PDF 파일 렌더링 및 변환 서비스 | 마크다운 가이드를 HTML 렌더러 기반의 인쇄용 PDF 스타일시트와 조합하여 서버 사이드에서 PDF 문서로 렌더링하는 서비스 |
| `DOCS-UTIL-B-202` | DOCS | UTIL | Backend | 이메일 및 Slack 외부 공유 연동 서비스 | 지정된 팀원 이메일로 가이드북을 전송하거나 슬랙 웹훅 채널로 분석 완료 알림 및 요약본을 포워딩하는 서비스 |

## 🗄️ 데이터베이스 및 청킹 전략 (DB & Chunking)
### 1. 정적 RAG와 Agentic CAG의 결합
전통적인 RAG의 문맥 파편화 단점을 보완하기 위해, 메인 LLM과 임베딩 모델을 쌍으로 구성하고 에이전트가 직접 탐색(도구 호출)하는 하이브리드 RAG를 채택합니다.
### 2. 계층적 트리 RAG (Tree-Based RAG)
개별 최하위 파일의 텍스트를 임베딩하고, 상위 디렉토리는 하위 텍스트들을 묶어 구조화 프롬프트로 '요약본'을 추출한 뒤 그 요약본을 임베딩(Bottom-up)하여 넓은 범위 문맥에 대응합니다.
### 3. PostgreSQL 기반 의존성 스키마 (pgvector)
폴더 구조를 무시하는 코드 참조 관계를 DB에 올바르게 기록합니다. 의존성 관계는 벡터가 아닌 **문자열 배열(Array)** 메타데이터로 저장하여 PostgreSQL의 `JOIN`과 재귀 쿼리(`WITH RECURSIVE`)를 통해 방사형 지식 그래프를 구성합니다.
### 4. AST 기반 의미론적 코드 청킹 (Semantic Chunking)
기본 분할(문자 수 기준)의 한계를 극복하고, 코드는 함수/클래스/라우터 단위로 분할하여 파일 경로 및 함수명 등의 메타데이터를 함께 저장합니다.

## 🧠 AI 모델 적용 전략 (Model Selection Strategy)
### 1. 메인 에이전트 모델: `gpt-4o`
* **역할**: Agentic Search 및 판단 로직, 자가 교정(Self-Correction) 등 메인 Brain 역할.
* **채택 근거**: 다중 도구 호출(Parallel Tool Calling) 최적화와 복잡한 의존성 구조를 해석하는 최상위권의 다단계 추론(Multi-step Reasoning) 점수를 갖춤.
### 2. 코드 임베딩 모델: `text-embedding-3-large`
* **역할**: 코드와 문서를 수학적 벡터 공간으로 변환 및 RAG 구축.
* **채택 근거**: 다국어 정보 검색 평가(MIRACL)에서 압도적 점수를 기록하여 한글 주석과 영문 소스코드가 혼재된 환경에 최적. 차원을 축소해도 성능이 유지되는 마트료시카 표현 학습 지원.
### 3. 하이브리드 병행 모델: `gpt-4o-mini`
* **역할**: Map-Reduce 요약 파이프라인 및 초기 데이터 전처리.
* **채택 근거**: 엄청난 텍스트 양을 읽어야 하는 문서화 단계에서 발생할 막대한 API 비용을 절감. (GPT-4o 대비 입력 기준 약 33배 저렴) 비용 대비 뛰어난 인지 능력(MMLU 82.0%)으로 고품질 요약 보장.
