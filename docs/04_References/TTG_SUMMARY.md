# HarishChandran3304/TTG 요약 및 분석

**HarishChandran3304/TTG** (TalkToGitHub)는 퍼블릭 GitHub 레포지토리와 직접 대화하며 코드를 분석할 수 있게 해주는 **AI 기반 오픈소스 도구**입니다. 레포지토리의 구조, 의존성, 기능에 대해 수동으로 분석할 필요 없이 질문하고 즉시 문맥에 맞는 답변을 얻을 수 있습니다.

## 📌 핵심 요약 (Core Highlights)

- **AI 기반 레포지토리 채팅 (TalkToGitHub)**: 레포지토리의 복잡한 코드나 README를 직접 읽는 대신, AI에게 아키텍처나 기능에 대해 바로 질문하여 파악할 수 있습니다.
- **간편한 접근성 (Easy Access)**: 기존 GitHub 레포지토리 URL 앞에 `talkto` 접두사만 붙여서 (예: `talktogithub.com/user/repo`) 즉각적으로 서비스에 접근할 수 있습니다.
- **오픈소스 (Open Source)**: 프로젝트 전체가 오픈소스로 공개되어 있어, 개발자가 로컬에서 직접 인스턴스를 실행하거나 커스텀하여 사용할 수 있습니다.

## ⚙️ 기술 스택

- **프론트엔드 (Frontend)**: Vite, React, TailwindCSS, Shadcn UI
- **백엔드 (Backend)**: Python, FastAPI
- **AI/LLM**: Google Gemini
- **패키지 관리**: uv (Python), npm (Node.js)

## 🏗️ 주요 아키텍처 및 파이프라인 흐름

### 1. 클라이언트-서버 분리형 구조
프로젝트는 사용자 인터페이스를 담당하는 프론트엔드와 AI 로직을 처리하는 백엔드가 독립적으로 구성되어 있습니다.
- **프론트엔드 클라이언트**: React와 Vite를 기반으로 구축되었으며, TailwindCSS 및 Shadcn UI를 활용해 빠르고 직관적인 채팅 UI를 제공합니다.
- **백엔드 서버**: Python의 FastAPI 프레임워크로 구현되었으며, 빠른 비동기 처리 성능을 제공합니다. 환경 구축에는 `uv`를 사용합니다.

### 2. AI 인퍼런스 파이프라인
백엔드 서버는 `GEMINI_API_KEY`를 통해 Google Gemini API와 연동됩니다. 사용자로부터 깃허브 레포지토리에 관한 질문을 받으면, FastAPI 백엔드가 Gemini 모델에 컨텍스트를 전달하고 답변을 생성하는 파이프라인을 거칩니다.

### 3. URL 기반 라우팅 방식
사용자가 기존 깃허브 주소에서 `github.com`을 `talktogithub.com`으로 변경하는 라우팅 방식을 채택하여 원활한 접근성과 사용자 경험(UX)을 확보했습니다.
