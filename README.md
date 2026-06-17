# 🗺️ CodeMap

> **GitHub Repository Analysis Chatbot**  
> GitHub 레포지토리의 구조와 코드를 분석하고, 사용자와 대화하며 인사이트를 제공하는 AI 챗봇 서비스입니다.

---

## ✨ Key Features (주요 기능)
- **프로젝트 등록 (Git 클론 및 필터링):** GitHub URL 입력으로 실시간 저장소 연동 및 노이즈 필터링
- **코드 맥락 및 관계망 이해 (RAG 및 코드 임베딩):** AST 기반 코드 청킹, 파일 간 import 관계 분석 및 pgvector 기반 저장
- **자율 탐색형 AI 코드 분석 (Agentic Search):** AI 비서가 저장소 구조를 파악해 스스로 질문에 답변 탐색
- **계층형 프로젝트 가이드북 자동 생성:** README, 폴더 구조, 핵심 실행 플로우 등 온보딩 문서 자동 요약 및 생성

## 🛠 Tech Stack (기술 스택)
- **Frontend:** HTML, CSS(SCSS), JavaScript, React.js (v19.2), Vite
- **Backend:** Python (v3.12), FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL, pgvector
- **Infra/Deploy:** Docker Compose, 로컬 HTTPS(mkcert), 환경 자동화 셸 스크립트
- **Tools:** Photoshop, Premiere Pro, Figma, Git
- **Collaboration:** GitHub, Notion, Discord, Slack

---

## 🚀 Architecture Overview (아키텍처 요약)
프론트엔드는 **Bulletproof React (Feature-Sliced Design)** 구조를 도입하여 기능(Feature) 단위의 높은 응집도를 확보하였고, 백엔드는 **FastAPI 환경에 3-Tier 아키텍처(Controller-Service-Repository)**를 적용하여 철저한 도메인 주도 설계(DDD)를 구현했습니다.

> 세부적인 폴더 트리 구조와 설계 철학은 아래의 **Architecture Guide** 문서에서 확인하실 수 있습니다.

---

## 📖 가이드 문서 (Documentation)
프로젝트 상세 구조, 실행 방법 및 팀 협업 규칙은 메인 문서를 깔끔하게 유지하기 위해 전용 문서로 분리하여 관리합니다. 작업 전 반드시 아래 문서들을 확인해 주세요.

> **💡 핵심 참조 사항 (Main Reference)**  
> 본 프로젝트는 **codewiki.google.com**을 메인 아키텍처로 참조하여 설계되었으며, 그 외 다양한 시스템 구조 및 외부 리서치 자료들은 `docs/04_References` 폴더에 통합 정리되어 있습니다.

- 👉 **[Architecture Guide (상세 설계 및 폴더 구조)](./ARCHITECTURE.md)**
- 👉 **[Getting Started (서버 로컬 실행 가이드)](./GETTING_STARTED.md)**
- 👉 **[Contributing Guidelines (Git 브랜치 및 커밋 규칙)](./CONTRIBUTING.md)**

---

## 👥 Contributors (팀원 소개)
| 이름 | 역할 | 이메일 | GitHub 프로필 |
|---|---|---|---|
| **신성민** | (역할 작성) | (이메일 작성) | [GitHub 링크](#) |
| **강영우** | (역할 작성) | (이메일 작성) | [GitHub 링크](#) |
| **장우수** | (역할 작성) | (이메일 작성) | [GitHub 링크](#) |
| **김효** | (역할 작성) | (이메일 작성) | [GitHub 링크](#) |