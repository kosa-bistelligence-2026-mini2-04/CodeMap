# Repository Summary: google-gemini/gemini-fullstack-langgraph-quickstart

이 저장소는 Google Gemini 모델과 LangGraph를 결합하여 실시간 웹 리서치를 수행할 수 있는 대화형 AI 에이전트를 구축하기 위한 오픈소스 풀스택 레퍼런스 아키텍처입니다.

## 🌟 핵심 요약 (Core Highlights)
* **심층 리서치 에이전트 (Deep Research Assistant)**: 사용자 질문을 기반으로 스스로 검색 쿼리를 생성하고 웹을 탐색하며, 수집된 정보를 분석하여 지식의 공백을 파악(Reflection)한 뒤 출처가 명시된 심층 보고서를 생성합니다.
* **풀스택 템플릿**: 직관적인 사용자 인터페이스를 제공하는 프론트엔드와 에이전트 로직을 처리하는 백엔드가 분리된 구조로 제공됩니다.
* **프로덕션 레벨 아키텍처**: 장기 메모리 저장, 백그라운드 작업, 실시간 스트리밍을 안정적으로 처리하기 위해 PostgreSQL 및 Redis와의 통합을 기본적으로 지원하며, Docker를 통한 쉬운 배포가 가능합니다.

## 🛠 기술 스택 (Tech Stack)
* **프론트엔드 (Frontend)**:
  * React (Vite 환경)
  * 스타일 및 UI 컴포넌트: Tailwind CSS, Shadcn UI
* **백엔드 (Backend)**:
  * 프레임워크: FastAPI (Python)
  * 에이전트 오케스트레이션: **LangGraph** (상태 기반 다단계 추론 워크플로우 제어)
  * 언어 모델 (LLM): Google Gemini (Google Gen AI API 및 LangChain 연동)
* **데이터베이스 및 인프라 (Infrastructure)**:
  * **PostgreSQL**: 대화 스레드 상태, 에이전트 설정 및 메모리 영구 저장
  * **Redis**: 백그라운드 태스크 및 실시간 결과 스트리밍을 위한 Pub/Sub 메시지 브로커
  * 컨테이너화: Docker 및 Docker-Compose
* **모니터링 (Observability)**:
  * LangSmith (선택적 통합을 통해 에이전트의 내부 추론 과정 모니터링 및 디버깅 지원)

## 🏗 아키텍처 구조 (Architecture)
모듈화된 아키텍처를 기반으로 에이전트의 반복적이고 복잡한 작업 흐름을 제어합니다.

1. **사용자 인터페이스 & 백그라운드 연동**: 프론트엔드(React)에서 사용자 질의를 FastAPI 서버로 전송하면, Redis 큐를 통해 백그라운드에서 LangGraph 작업이 트리거됩니다.
2. **질의 분석 및 생성 (Query Generation)**: Gemini 모델이 초기 입력을 분석하여 최적의 검색 쿼리 목록을 도출합니다.
3. **실시간 정보 탐색 (Web Research)**: 구글 검색 등의 도구를 활용해 실시간으로 최신 정보를 수집합니다.
4. **반성적 추론 (Reflective Reasoning)**: LangGraph 기반의 그래프 구조 내에서 에이전트가 수집된 데이터의 적합성을 평가합니다. 지식 공백이 발견되면 자동으로 검색 쿼리를 수정하고 추가 정보를 수집하는 반복(Iterative) 루프를 돕니다.
5. **결과 합성 및 실시간 스트리밍 (Synthesis & Streaming)**: 충분한 데이터가 모이면, 모델이 최종 답변과 함께 인용 출처(Citations)를 종합하며, 이 결과는 사용자 화면으로 실시간 스트리밍됩니다.
