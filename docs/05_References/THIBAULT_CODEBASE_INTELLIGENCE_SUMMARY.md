# Thibault-Knobloch/codebase-intelligence 요약 및 분석

**Thibault-Knobloch/codebase-intelligence (Tibo)**는 로컬 코드 레포지토리를 인덱싱하여 자연어로 질의할 수 있게 해주는 **오픈소스 CLI(Command-Line Interface) 도구**입니다. AI 에이전트나 개발자가 코드베이스의 문맥을 이해하고 정보를 빠르게 검색할 수 있도록 RAG(Retrieval-Augmented Generation) 방식을 활용합니다.

## 📌 핵심 요약 (Core Highlights)

- **자연어 질의 (Natural Language Queries)**: 평문 영어를 사용하여 코드베이스에 대한 질문을 던지고 맥락을 고려한 답변을 받을 수 있습니다.
- **코드베이스 인덱싱 (Codebase Indexing)**: 로컬 프로젝트의 구조를 스캔하고 체계적으로 정리하여 검색 가능한 상태로 만듭니다.
- **호출 그래프 생성 (Call Graph Generation)**: 함수, 클래스, 파일 간의 관계를 매핑하여 단순한 텍스트 매칭을 넘어선 깊은 의존성 문맥(Dependency Context)을 제공합니다.
- **로컬 벡터 데이터베이스 (Local Vector Database)**: 코드를 논리적 단위로 청킹하고 임베딩하여 로컬에 저장함으로써, 프라이버시를 유지하면서도 빠르고 지능적인 검색을 지원합니다.
- **LLM 통합 (LLM Integration)**: 사용자가 직접 OpenAI API 키 등을 설정하여 검색 및 질의 응답 프로세스를 강화할 수 있습니다.

## ⚙️ 기술 스택
- **인터페이스**: CLI (Command-Line Interface)
- **AI/LLM**: OpenAI API 호환 LLM (GPT-4o-mini 등 활용)
- **데이터베이스**: 로컬 임베딩 및 벡터 스토어

## 🏗️ 주요 아키텍처 및 파이프라인 흐름

### 1. Codebase Indexing & Scanning 파이프라인
프로젝트 구조를 스캔하여 추후 검색과 분석이 용이하도록 코드를 구성합니다.

### 2. Call Graph 및 Context 매핑
단순 정적 분석을 넘어 함수와 클래스 간의 호출 그래프(Call Graph)를 생성합니다. 이를 통해 질문과 관련된 코드가 어떤 파일과 함수에 의존하고 있는지 명확한 구조적 맥락을 파악할 수 있습니다.

### 3. Chunking & Embedding 전략
코드를 임의의 텍스트 블록이 아닌 의미 있는 논리적 단위(함수, 클래스, 모듈 등)로 분할(Chunking)합니다. 이후 이 청크들을 수학적 벡터 임베딩으로 변환하여 로컬 벡터 데이터베이스에 저장합니다.

### 4. Query & Enrichment 흐름
사용자가 자연어로 질문을 하면, 시스템이 LLM을 통해 의도를 해석합니다. 저장된 벡터 임베딩과 대조하여 문맥상 가장 관련성 높은 파일과 코드 스니펫을 검색(RAG)하며, 호출 그래프 정보를 덧붙여 AI에게 풍부한 맥락을 전달함으로써 정확한 답변을 도출합니다.

---

> **💡 시사점 및 적용 관점**
> Tibo 프로젝트는 로컬 환경에서 프라이버시를 보호하면서 코드베이스를 지능적으로 탐색하는 훌륭한 레퍼런스입니다. 단순한 텍스트 검색(grep)을 넘어 **논리적 코드 청킹**과 **호출 그래프(Call Graph) 기반의 의존성 파악**을 RAG 파이프라인에 결합한 아키텍처는 컨텍스트의 품질을 높이는 데 큰 영감을 줍니다.
