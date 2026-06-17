# 🏛️ Architecture Standard (아키텍처 표준 및 폴더 구조)

본 프로젝트는 대규모 확장성과 팀 협업 효율을 극대화하기 위해, 프론트엔드와 백엔드 모두 철저한 **도메인(기능) 주도 설계(Domain-Driven Design)**를 따르는 모노레포(Monorepo) 구조로 구성되었습니다.

---

## 1. Frontend Architecture (React / Vite)

프론트엔드는 응집도를 높이고 결합도를 낮추기 위해 글로벌 스탠다드인 **Feature-Sliced Design**과 **Bulletproof React**의 철학을 차용하였습니다. `pages/` 폴더에는 껍데기만 남기고, 모든 핵심 로직은 `features/` 하위에 격리합니다.

```text
apps/frontend/
├── src/
│   ├── common/           # 🌐 [공통 영역] 버튼, 모달, 유틸, 훅 등 순수 재사용 요소
│   ├── features/         # 🧠 [도메인 영역] (예: user, analysis) 도메인 특화 컴포넌트, 훅, API 통신 로직
│   └── pages/            # 📄 [라우팅 영역] 로직 없이 조각들을 화면에 배치만 하는 레고 조립판
```

## 2. Backend Architecture (FastAPI)

백엔드는 기술 계층(models, routers)이 아닌 비즈니스 도메인 단위로 폴더를 구성하며, 객체지향 설계의 모범인 **Java Spring Boot의 3-Tier 아키텍처**를 완벽하게 파이썬(Pythonic) 생태계로 치환하여 적용하였습니다.

```text
apps/backend/app/
├── {domain}/             # (예: user, analysis) 기능별 독립 도메인 모듈
│   ├── router.py         # 📡 API 진입점 (Controller)
│   ├── service.py        # 🧠 비즈니스 로직 (Service)
│   ├── repository.py     # 🗄️ DB 접근 로직 (DAO / Repository)
│   ├── schemas.py        # 🚚 데이터 유효성 검증 및 전송 모델 (DTO / Pydantic)
│   └── models.py         # 🏗️ 데이터베이스 테이블 매핑 (Entity / SQLAlchemy)
```

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
