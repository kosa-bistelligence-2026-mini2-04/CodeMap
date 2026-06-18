# Neverdecel/CodeRAG 요약 및 분석

**Neverdecel/CodeRAG**는 OpenAI GPT 모델과 FAISS(Facebook AI Similarity Search) 기반의 벡터 검색을 결합하여, 프로젝트 전체 문맥(Full-Context)을 이해하고 실시간으로 코드베이스 질의 및 증강(Augmentation)을 제공하는 **AI 기반 실시간 코드 어시스턴트 도구(POC)**입니다.

## 📌 핵심 요약 (Core Highlights)

- **전체 문맥 인식 (Full-Context Awareness)**: 기존의 소규모 컨텍스트 윈도우에 제한된 AI 어시스턴트와 달리, 전체 코드베이스를 인덱싱하여 프로젝트의 완전한 문맥을 바탕으로 답변과 제안을 제공합니다.
- **벡터 기반 검색 (Vector-Based Search)**: FAISS를 활용하여 코드베이스 전체에 대해 효율적이고 의미론적인(Semantic) 검색을 수행합니다.
- **실시간 인덱싱 (Real-Time Indexing)**: 코드베이스에 변경 사항이 발생하면 자동으로 업데이트되어 AI 어시스턴트가 항상 최신 프로젝트 상태를 유지할 수 있도록 합니다.
- **AI 통합 (AI Integration)**: OpenAI의 GPT 모델을 활용하여 지능적인 코드 분석, 리팩토링, 그리고 코드 관련 질의응답(Q&A) 기능을 지원합니다.

## ⚙️ 기술 스택
- **언어**: Python 3.11+
- **데이터베이스/검색**: FAISS (Facebook AI Similarity Search)
- **AI/LLM**: OpenAI GPT Models (GPT-4 등)
- **개발 도구**: `black`, `isort`, `flake8`, `mypy`, `pre-commit` 등

## 🏗️ 주요 아키텍처 및 파이프라인 흐름

### 1. 벡터 인덱싱 파이프라인 (Vector Search & Indexing)
- 저장소 내 코드베이스 전체를 스캔하여 추상 구문 트리(AST) 등을 이용한 청킹(Chunking) 과정을 거칩니다.
- 나누어진 코드 청크들은 임베딩 모델을 통해 벡터로 변환되며, 이 데이터들은 **FAISS** 벡터 데이터베이스에 저장되어 관리됩니다.
- 코드 변경 시 실시간 인덱싱 전략을 통해 최신 상태의 벡터 맵을 갱신합니다.

### 2. 질의응답 및 생성 (Core AI Engine)
- 사용자가 질문이나 분석을 요청하면, FAISS를 통해 관련성이 높은 코드 파일과 맥락을 신속하게 검색합니다.
- 추출된 전체 코드 문맥(Full-Context)과 사용자의 질의를 결합해 OpenAI 모델에 전달하여, 최종적인 답변 생성 및 코드 리팩토링을 수행합니다.

---

> **💡 적용 및 참고 관점**
> Neverdecel의 CodeRAG는 기존의 RAG 아키텍처를 코드베이스에 효율적으로 적용하기 위해 FAISS와 실시간 인덱싱 기법을 도입한 실용적인 POC(Proof of Concept)입니다. 자체적인 RAG 기반 코드 어시스턴트 도구나 검색 파이프라인을 구축할 때 핵심 참고 자료로 활용할 수 있습니다.
