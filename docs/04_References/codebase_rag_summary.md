# mehmoodosman/codebase-rag 요약 및 분석

**mehmoodosman/codebase-rag**는 Retrieval-Augmented Generation (RAG)을 사용하여 코드베이스에 대해 질문하고 이해할 수 있도록 설계된 **AI 기반 대화형 인터페이스**입니다.

## 📌 핵심 요약 (Core Highlights)

- **대화형 인터페이스 (Conversational Interface)**: Streamlit으로 구축된 사용자 친화적인 채팅 경험을 제공하여 특정 코드베이스와 상호 작용하고 질문할 수 있습니다.
- **의미론적 코드 검색 (Semantic Code Search)**: 임베딩 모델을 사용하여 벡터 유사도 검색을 수행, 자연어 질의를 기반으로 관련 코드 스니펫을 찾을 수 있습니다.
- **다중 레포지토리 지원 (Multiple Repository Support)**: 벡터 데이터베이스 내에서 "네임스페이스(namespaces)"를 활용하여 여러 코드베이스를 지원하고 전환할 수 있습니다.
- **문맥 인지 (Context-Aware)**: 상호 작용하는 동안 일관되고 문맥을 고려한 응답을 제공하기 위해 채팅 기록을 유지합니다.

## ⚙️ 기술 스택
- **프론트엔드**: Streamlit
- **LLM**: Groq (Llama models)
- **Vector Database**: Pinecone
- **Embeddings**: HuggingFace Sentence Transformers (`all-mpnet-base-v2`)

## 🏗️ 주요 아키텍처 및 파이프라인 흐름

간단하고 효율적으로 설계된 표준 RAG 파이프라인 아키텍처를 따릅니다:

### 1. Frontend
**Streamlit** 웹 애플리케이션이 사용자 인터페이스 역할을 합니다.

### 2. Indexing/Embedding
코드를 처리하여 **HuggingFace Sentence Transformers**를 사용해 벡터 임베딩을 생성합니다.

### 3. Vector Store
**Pinecone**을 사용하여 이러한 임베딩을 저장하고 빠른 의미론적 검색(semantic retrieval)을 수행합니다.

### 4. Generation
검색된 코드 문맥(context)은 대형 언어 모델(LLM)—특히 **Groq을 통한 Llama 모델**—로 전송되어 사람이 읽을 수 있는 답변을 생성합니다.

### 5. RAG Logic
맞춤형 구현(Custom implementation)을 통해 관련 코드 스니펫의 검색을 조정하고 이 문맥을 바탕으로 LLM 프롬프트를 증강(augment)합니다.
