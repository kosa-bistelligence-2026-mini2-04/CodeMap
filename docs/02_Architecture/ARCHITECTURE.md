# 🏛️ Architecture Standard (아키텍처 표준 및 폴더 구조)

본 프로젝트는 대규모 확장성과 팀 협업 효율을 극대화하기 위해, 프론트엔드와 백엔드 모두 철저한 **도메인(기능) 주도 설계(Domain-Driven Design)**를 따르는 모노레포(Monorepo) 구조로 구성되었습니다.

---

## 1. Frontend Architecture (Next.js)

프론트엔드는 응집도를 높이고 결합도를 낮추기 위해 글로벌 스탠다드인 **Feature-Sliced Design**과 **Bulletproof React**의 철학을 차용하였습니다. Next.js의 App Router 구조인 `app/` 폴더에는 껍데기만 남기고, 모든 핵심 로직은 `features/` 하위에 격리합니다.

```text
frontend/
├── src/
│   ├── app/              # 📄 [라우팅 영역] Next.js App Router
│   │   ├── analyze/      # 코드 분석 페이지 라우트
│   │   ├── chat/         # AI 채팅 페이지 라우트
│   │   ├── docs/         # 문서 확인 페이지 라우트
│   │   ├── globals.css   # 전역 스타일시트
│   │   └── layout.tsx / page.tsx # 최상위 레이아웃 및 진입 페이지
│   │
│   ├── common/           # 🌐 [공통 영역] 도메인에 종속되지 않는 재사용 요소
│   │   ├── components/   # 범용 UI 컴포넌트 (버튼, 모달, 입력창 등)
│   │   ├── contexts/     # 전역 상태 컨텍스트 (테마, 사용자 설정 등)
│   │   ├── hooks/        # 공통 커스텀 훅 (useClickOutside 등)
│   │   ├── i18n/         # 다국어 지원 리소스 및 설정
│   │   ├── types/        # 공통 TypeScript 타입 정의
│   │   └── utils/        # 공용 유틸리티 함수 (포맷팅, 계산 등)
│   │
│   └── features/         # 🧠 [도메인 영역] 도메인 특화 비즈니스 로직
│       ├── analysis/     # 코드 분석 및 결과 화면 컴포넌트/로직
│       ├── chat/         # 대화형 AI 채팅 인터페이스 및 로직
│       ├── docs/         # 문서 생성 및 조회 컴포넌트
│       ├── graph/        # 코드베이스 아키텍처 시각화(그래프) 도메인
│       ├── history/      # 분석 및 작업 내역 도메인
│       ├── landing/      # 랜딩 페이지 특화 컴포넌트
│       └── repository/   # 레포지토리 연동 및 관리 도메인
```

## 2. Backend Architecture (FastAPI)

백엔드는 기술 계층(models, routers)이 아닌 비즈니스 도메인 단위로 폴더를 구성하며, 객체지향 설계의 모범인 **Java Spring Boot의 3-Tier 아키텍처**를 완벽하게 파이썬(Pythonic) 생태계로 치환하여 적용하였습니다. 실제 구현되어 있는 주요 도메인은 다음과 같습니다.

```text
backend/app/
├── infra/                # ⚙️ 애플리케이션 인프라 (Config, Database, Auth)
├── common/               # 📋 도메인 간 공통 계약 (Exceptions, Schemas)
├── util/                 # 🛠️ 순수 유틸리티 함수
├── agent/                # 🤖 LLM 멀티에이전트 도메인 (LangGraph)
│   ├── llm_client.py     #    LLM provider/factory only
│   ├── nodes/            #    Planner, Dispatcher, Evaluator LangGraph nodes
│   └── workers/          #    search/dir/grep/read 단일 목적 worker adapters
├── tool/                 # 🔧 도구 도메인 (검색 알고리즘 + MCP I/O)
├── auth/                 # 🔐 인증 도메인
├── team/                 # 👥 팀 workspace, 초대, 멤버십, 공유 범위 도메인 (Phase 2)
├── chat/                 # 💬 채팅 대화 도메인 (Final Answer 생성 및 스트리밍)
│   ├── final_answer_agent.py # 최종 답변 정제 에이전트
│   └── ...
├── embed/                # 🧠 임베딩 처리 도메인
├── list/                 # 📋 리스트 데이터 처리 도메인
├── parse/                # 📄 파싱 도메인
├── pipeline/             # 🔀 파이프라인 처리 도메인
└── repo/                 # 🗄️ 리포지토리/코드 저장소 접근 도메인
    # 각 도메인(기능) 내부는 다음과 같은 3-Tier 패턴을 따릅니다:
    # ├── router.py       # 📡 API 진입점 (Controller)
    # ├── service.py      # 🧠 비즈니스 로직 (Service)
    # ├── repository.py   # 🗄️ DB 접근 로직 (DAO / Repository)
    # ├── schemas.py      # 🚚 데이터 유효성 검증 및 전송 모델 (DTO / Pydantic)
    # └── models.py       # 🏗️ 데이터베이스 테이블 매핑 (Entity / SQLAlchemy)
```

### 🏷️ Backend 모듈 네이밍 및 분리 규칙 (Naming Conventions)

백엔드 전역 공통 모듈과 각 도메인 하위 모듈 간의 명칭 혼동을 방지하기 위해 다음 규칙을 엄격히 따릅니다.

* **`app/infra` (애플리케이션 인프라)**: 앱 구동에 필요한 인프라 컴포넌트입니다. (Config, Database, Auth 등)
* **`app/common` (공통 계약)**: 도메인 간 공유되는 예외 처리, 스키마 등 공통 계약입니다. (Exceptions, Schemas, Global Handlers 등)
* **`app/agent` (LLM 에이전트 도메인)**: AI 멀티에이전트의 핵심 로직이 위치하는 도메인입니다. 하위 모듈은 역할(Role)에 기반하여 명명합니다.
  * `nodes/`: LangGraph 제어 노드입니다. `planner_node.py`는 LLM 계획 수립, `dispatcher_node.py`는 결정론적 검증/fan-out, `evaluator_node.py`는 Phase 1 근거 압축과 Phase 2 충분성 판단을 담당합니다.
  * `workers/`: `search_worker.py`, `dir_worker.py`, `grep_worker.py`, `read_worker.py`처럼 단일 목적 worker adapter만 둡니다.
  * `llm_client.py`: 모델 생성 factory만 담당하고, node 책임을 흡수하지 않습니다.
* **`app/tool` (도구 도메인)**: RAG 검색 알고리즘(Hybrid Search, RRF), 파일 읽기, grep, 디렉토리 스캔과 MCP I/O 외부 인터페이스를 제공합니다.
* **`app/team` (팀 workspace 도메인, Phase 2)**: 팀 생성, 초대/수락, 멤버십, 개인/private 기록과 팀 공유 기록의 visibility 정책을 담당합니다. LIST/REPO/CHAT 도메인은 `repo_id`만 신뢰하지 않고 `analysis_jobs.created_by_user_id`, `visibility`, `team_id`와 팀 멤버십을 함께 확인해야 합니다.
* **`app/repo` 파일 프리뷰 경계**: `/analyze` 코드 프리뷰와 채팅 근거 라인 이동은 `repo` 도메인의 job-scoped 파일 읽기 API를 통해서만 workspace 파일에 접근합니다. `tool/file_read.py` 같은 내부 worker 도구를 사용자-facing API로 직접 노출하지 않습니다.
* **`/analyze` 화면 조합 책임**: `PROJECT_ANALYZE_SPEC.md`가 report, repository tree, code preview, history, compact chat의 화면 상태 연결을 정의합니다. 백엔드는 REPO/LIST/CHAT/RAG-PARSE 계약을 제공하고 화면 배치는 프론트가 조합합니다.
* **Frontend API error boundary (Issue #176)**: `features/*/api` client는 서버 envelope를 직접 화면에 넘기지 않고, 공통 parser를 통해 `{ status, code, message, field, retryable }` 형태로 정규화합니다. 사용자-facing 문구와 field-level 오류 표시 책임은 UI 계층에 둡니다.
* **Accessibility/i18n baseline (Issue #180)**: `common/components`의 버튼, 모달, toast, banner는 accessible name, focus-visible, keyboard navigation, `prefers-reduced-motion` fallback을 기본 계약으로 가집니다. 화면 문구와 `html lang`은 제품 기본 언어와 일치해야 합니다.
* **LLM model catalog boundary (Issue #181)**: 프론트 모델 선택지는 `LLM_COMMON_API_SPEC.md`의 모델 카탈로그 또는 동일 내용을 공유하는 정적 계약을 기준으로 구성합니다. 백엔드 allowlist와 UI 옵션을 별도 하드코딩해 unsupported model 선택 실패가 뒤늦게 발생하지 않게 합니다.

---

## 3. Database Architecture (데이터베이스 구조)

RAG 파이프라인과 메인 서비스의 데이터를 저장하기 위한 초기화 스크립트 및 테이블 뼈대 구조입니다.

```text
database/
└── init.sql                      # 🗄️ PostgreSQL 테이블 및 pgvector 스키마 초기화 SQL
```

* **설계 및 초기화 철학**: RAG 파이프라인 구동을 위한 `pgvector` 확장 적용 및 관계형 테이블 설계를 위한 뼈대만 유지합니다. 인위적인 더미 데이터(seed.sql)는 주입하지 않으며, **개발 완료 후 CodeMap 프로젝트 자체를 분석 타겟으로 삼아(Dogfooding) 파이프라인을 직접 테스트하고 실제 데이터를 적재**합니다.

---

## 4. Scripts & Environment (인프라 및 환경 자동화)

응용 프로그램 로직 외부에 위치하며, 시스템을 안정적으로 구동하고 배포하기 위한 환경 설정 및 실행 자동화 스크립트 구조입니다.

```text
scripts/
├── docker-compose.yml            # 🐳 인프라 컨테이너 구성 (PostgreSQL, pgvector 등)
├── setup_env.sh                  # 🛠️ 로컬/운영 실행 환경(인증서, 의존성 등) 구축 셸 스크립트
└── init_db.sh                    # 🔄 DB 마이그레이션 및 컨테이너 초기화 자동 실행 스크립트
```

* **환경 자동화 철학**: Docker Compose 파일과 실행 셸 스크립트를 한 곳(`scripts/`)에 모아 두어, 스크립트가 인프라 컨테이너를 구동할 때의 실행 경로 응집도를 극대화했습니다. 개발(로컬), 스테이징, 운영(Production) 등 각 실행 타겟 환경에 맞춰 `.env` 템플릿 복사, 필수 라이브러리 설치, SSL 인증서(`mkcert`) 발급을 한 번에 진행합니다. 신규 개발자 합류 및 서버 배포 시 **명령어 1줄(One-Click)**로 완벽하게 환경이 세팅되도록 보장하여 온보딩(Onboarding) 리소스를 최소화합니다.

---

## 📚 References & Justifications

본 아키텍처의 설계적 당위성과 레퍼런스는 다음의 소프트웨어 공학 표준 문서들을 따릅니다.

* **Frontend Standard:**
  * [Bulletproof React 공식 GitHub](https://github.com/alan2207/bulletproof-react)
  * [Feature-Sliced Design (FSD)](https://feature-sliced.design/)
* **Backend Standard:**
  * **Screaming Architecture & Clean Architecture**[^1]: 폴더 명만 봐도 프레임워크가 아닌 비즈니스 의도가 명확히 드러나야 한다는 Robert C. Martin(Uncle Bob)의 아키텍처 철학.
    * [Screaming Architecture (Clean Coder Blog, 2011)](https://blog.cleancoder.com/uncle-bob/2011/09/30/Screaming-Architecture.html)
    * [The Clean Architecture (Clean Coder Blog, 2012)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
  * **Martin Fowler's Patterns**: Service Layer 및 Repository Pattern을 적용한 견고한 3계층 분리.
  * [FastAPI Official: Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)

---

[^1]: **주석(Note)**: 로버트 C. 마틴은 애자일 소프트웨어 개발 선언(Agile Manifesto)의 공동 작성자이자, 전 세계 개발자들의 필독서인 『클린 코드(Clean Code)』, 『클린 아키텍처(Clean Architecture)』의 저자입니다. 본 프로젝트의 백엔드 디렉토리는 그가 주창한 "프레임워크 중심이 아닌 도메인과 비즈니스 목적이 소리치듯(Screaming) 드러나야 한다"는 설계 철학을 깊이 반영하고 있습니다.
