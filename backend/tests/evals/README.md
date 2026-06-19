# RAG evaluations

질문별 예상 파일·심볼·근거를 `retrieval_cases.jsonl`로 관리하고 Recall@K, MRR, 근거 포함률, 지연 시간과 모델 비용을 기록한다. 현재 검색 구현의 회귀 기준은 `test_retrieval_quality.py`에서 검증한다.
