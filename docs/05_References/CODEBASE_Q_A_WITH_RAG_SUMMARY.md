# Manas2412/CodeBase-Q-A-with-RAG 요약 및 분석

**Manas2412/CodeBase-Q-A-with-RAG**는 코드베이스를 검색하고 상호작용하기 위해 특화된 **RAG(Retrieval-Augmented Generation)** 기반의 시스템입니다. 개발자가 방대한 코드베이스를 직접 탐색하는 대신, 자연어 질문을 통해 코드의 구조와 기능을 이해할 수 있도록 돕는 도구입니다.

## 📌 핵심 요약 (Core Highlights)

- **Semantic Code Search (의미론적 검색)**: 단순한 키워드 매칭이 아닌, 코드의 의미와 문맥을 이해하여 가장 관련성 높은 코드 스니펫을 찾아냅니다.
- **Language-Aware Chunking**: 코드를 분할할 때 문법 구조(AST 등)를 고려하여 함수나 클래스의 경계가 훼손되지 않도록 청킹(Chunking)을 수행합니다.
- **Conversational Interface**: 사용자가 코드베이스와 대화하듯 질문하고 답변을 받을 수 있는 직관적인 채팅 UI를 제공합니다.
- **다양한 LLM 지원**: OpenAI, 오픈소스 모델(HuggingFace, Ollama 등)과 유연하게 연동되어 답변을 생성합니다.

## ⚙️ 기술 스택
- **프론트엔드/UI**: Streamlit (대화형 인터페이스 제공)
- **오케스트레이션**: LangChain (데이터 로딩, 청킹, 검색, 생성 파이프라인 관리)
- **Vector DB**: ChromaDB, Pinecone, 또는 FAISS (코드 임베딩 저장 및 검색)
- **Embedding Model**: HuggingFace (`sentence-transformers`) 또는 OpenAI
- **AI/LLM**: OpenAI (GPT 모델), Groq, 또는 Ollama (로컬 모델)

## 🏗️ 주요 아키텍처 및 파이프라인 흐름

### 1. 데이터 수집 및 전처리 (Data Ingestion & Preprocessing)
GitHub 레포지토리 또는 로컬 디렉토리를 스캔하여 코드 파일을 추출하고 불필요한 데이터를 정제합니다.

### 2. 코드 청킹 및 인덱싱 (Chunking & Indexing)
- 코드를 적절한 크기로 분할합니다. 이때 코드의 논리가 깨지지 않도록 프로그래밍 언어의 특성을 반영한 분할기를 사용합니다.
- 분할된 코드 청크를 임베딩 모델을 통해 벡터로 변환하고, 파일 경로 및 라인 번호 등의 메타데이터와 함께 Vector DB에 저장합니다.

### 3. 검색 및 답변 생성 (Retrieval & Generation)
- 사용자가 질문을 입력하면 시스템이 이를 벡터로 변환하여 Vector DB에서 가장 유사도가 높은 코드 스니펫을 검색(Semantic Search)합니다.
- 검색된 코드 스니펫을 프롬프트의 컨텍스트로 삽입하여 LLM에 전달하고, LLM은 해당 코드 컨텍스트를 기반으로 정확한 자연어 답변을 생성합니다.

---

> **💡 CodeMap 프로젝트 적용 관점**
> 이 레포지토리는 전형적이고 강력한 코드 기반 RAG 시스템의 표준적인 아키텍처를 보여줍니다.
> 특히 **AST 기반의 언어 인지적 청킹(Language-Aware Chunking)**과 **LangChain-Streamlit 조합의 빠른 프로토타이핑**은 CodeMap의 데이터 전처리 및 검색 모듈 설계 시 훌륭한 참고 자료가 될 수 있습니다.
