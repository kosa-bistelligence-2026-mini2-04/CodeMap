# CodeWiki (codewiki.google.com) 참조 요약

## 1. 개요
본 문서는 CodeMap 프로젝트의 아키텍처 및 서비스 설계 시 **메인 레퍼런스**로 참고한 `codewiki.google.com`의 핵심 개념과 벤치마킹 요소들을 정리한 문서입니다.

## 2. 주요 참조 사항 (Key References)

- **Agentic RAG 설계 원칙**
  단순한 텍스트 검색(Keyword Match)을 넘어, 대규모 언어 모델(LLM)이 직접 시스템 도구(Tool)를 활용하여 능동적으로 코드를 탐색하고 의존성을 추적하는 자율적 에이전트 구조를 차용했습니다.

- **계층적 구조화 요약 (Hierarchical Summarization)**
  수만 줄의 소스코드를 한 번에 분석할 때 발생하는 토큰 한계와 정보 누락(Lost in the middle) 현상을 극복하기 위해, 파일 단위 요약 후 폴더 단위로 통합하는 Bottom-up 방식의 문서화 파이프라인(Map-Reduce)을 채택했습니다.

- **Vector DB 기반 시맨틱 검색 최적화**
  코드에 담긴 의도와 의미를 효율적으로 벡터화하여 PostgreSQL(pgvector) 기반으로 저장하고 쿼리하는 데이터베이스 스키마 및 임베딩 모델(text-embedding-3-large) 최적화 전략을 벤치마킹했습니다.

## 3. 적용 결과
위 참조 사항들을 바탕으로 CodeMap은 단순한 검색 도구를 넘어, 신규 개발자의 온보딩 비용을 획기적으로 줄여주는 **'지능형 소스코드 대화 비서'**로 설계되었습니다.
