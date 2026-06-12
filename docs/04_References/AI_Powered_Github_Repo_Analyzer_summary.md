# aniketkarne/AI-Powered-Github-Repo-Analyzer 요약 및 분석

**aniketkarne/AI-Powered-Github-Repo-Analyzer**는 인공지능을 활용하여 원시 GitHub 프로필 및 레포지토리 지표를 실행 가능한 인사이트로 변환해 주는 대화형 분석 도구입니다.

## 📌 핵심 요약 (Core Highlights)

- **프로필 및 레포지토리 지표 (Profile & Repo Metrics)**: 프로그래밍 언어 분포(차트), Star/Fork 동향, 그리고 활동 히트맵 등의 데이터를 시각적으로 제공합니다.
- **AI 기반 분석 (AI-Driven Analysis)**: 
  - **README 품질 평가**: 프로젝트의 README를 평가하고 개선점을 제안합니다.
  - **키워드 추출**: 레포지토리의 발견성(Discoverability)을 높이기 위한 주요 키워드를 식별합니다.
  - **대화형 Q&A**: 간단한 AI 채팅 인터페이스를 통해 레포지토리의 맥락에 대한 질의응답이 가능합니다.

## ⚙️ 기술 스택
- **백엔드**: FastAPI (Python), httpx, aioredis
- **프론트엔드**: React, Axios, Chart.js, React-Chartjs-2
- **AI/LLM**: OpenAI (GPT Models)

## 🏗️ 주요 아키텍처 및 파이프라인 흐름

### 1. 데이터 수집 및 캐싱 (Data Handling & Caching)
- GitHub 클라이언트와 `httpx`를 사용하여 GitHub API에 요청을 보내며, 페이지네이션된 레포지토리 데이터를 효율적으로 가져옵니다.
- API 호출을 최적화하고 응답 시간을 줄이기 위해 **aioredis**를 활용하여 데이터를 캐싱합니다.

### 2. AI 분석 파이프라인 (AI Integration)
- 분석 대상 데이터를 OpenAI의 모델(GPT)로 전달하여, 요약 정보 생성, 리드미(README) 분석 결과 및 대화형 답변을 생성합니다.

### 3. 프론트엔드 시각화 (Frontend Visualization)
- React와 Axios를 통해 백엔드의 분석 데이터를 비동기적으로 가져온 뒤, Chart.js 및 React-Chartjs-2를 통해 대시보드 형태의 시각화 컴포넌트로 사용자에게 제공합니다.
