# 🏛️ Architecture Standard (아키텍처 표준 및 폴더 구조)

본 프로젝트는 대규모 확장성과 팀 협업 효율을 극대화하기 위해, 프론트엔드와 백엔드 모두 철저한 **도메인(기능) 주도 설계(Domain-Driven Design)**를 따르는 모노레포(Monorepo) 구조로 구성되었습니다.

---

## 1. Frontend Architecture (React / Vite)
프론트엔드는 응집도를 높이고 결합도를 낮추기 위해 글로벌 스탠다드인 **Feature-Sliced Design**과 **Bulletproof React**의 철학을 차용하였습니다. `pages/` 폴더에는 껍데기만 남기고, 모든 핵심 로직은 `features/` 하위에 격리합니다.

```text
frontend/
├── src/
│   ├── common/           # 🌐 [공통 영역] 버튼, 모달, 유틸, 훅 등 순수 재사용 요소
│   ├── features/         # 🧠 [도메인 영역] (예: user, analysis) 도메인 특화 컴포넌트, 훅, API 통신 로직
│   └── pages/            # 📄 [라우팅 영역] 로직 없이 조각들을 화면에 배치만 하는 레고 조립판
```

## 2. Backend Architecture (FastAPI)
백엔드는 기술 계층(models, routers)이 아닌 비즈니스 도메인 단위로 폴더를 구성하며, 객체지향 설계의 모범인 **Java Spring Boot의 3-Tier 아키텍처**를 완벽하게 파이썬(Pythonic) 생태계로 치환하여 적용하였습니다.

```text
backend/app/
├── {domain}/             # (예: user, analysis) 기능별 독립 도메인 모듈
│   ├── router.py         # 📡 API 진입점 (Controller)
│   ├── service.py        # 🧠 비즈니스 로직 (Service)
│   ├── repository.py     # 🗄️ DB 접근 로직 (DAO / Repository)
│   ├── schemas.py        # 🚚 데이터 유효성 검증 및 전송 모델 (DTO / Pydantic)
│   └── models.py         # 🏗️ 데이터베이스 테이블 매핑 (Entity / SQLAlchemy)
```

---

## 📚 References & Justifications

본 아키텍처의 설계적 당위성과 레퍼런스는 다음의 소프트웨어 공학 표준 문서들을 따릅니다.

- **Frontend Standard:** 
  - [Bulletproof React 공식 GitHub](https://github.com/alan2207/bulletproof-react)
  - [Feature-Sliced Design (FSD)](https://feature-sliced.design/)
- **Backend Standard:**
  - **Screaming Architecture**: 폴더 명만 봐도 비즈니스가 소리치듯 보여야 한다는 Robert C. Martin의 아키텍처 철학.
  - **Martin Fowler's Patterns**: Service Layer 및 Repository Pattern을 적용한 견고한 3계층 분리.
  - [FastAPI Official: Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
