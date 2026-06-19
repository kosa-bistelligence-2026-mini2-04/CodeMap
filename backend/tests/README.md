# Backend tests

백엔드 검증 자료는 실행 범위에 따라 분리한다.

| 위치 | 역할 |
| --- | --- |
| `http/` | FastAPI REST, SSE, WebSocket 계약과 수동 호출 테스트 |
| `unit/` | 외부 서비스 없이 실행되는 함수, 서비스, 파이프라인 노드 테스트 |
| `integration/` | PostgreSQL, pgvector, 모델 연동을 포함한 통합 테스트 |
| `evals/` | 검색 정확도와 LLM 답변 품질을 고정 평가셋으로 검증 |
| `fixtures/` | 테스트와 평가에서 공유하는 소형 저장소 및 입력 데이터 |

전체 테스트는 `backend`에서 다음과 같이 실행한다. 아직 구현되지 않은 Notion RAG 계약은 삭제하지 않고 `skipped`로 표시되며, 해당 모듈과 함수가 추가되면 자동으로 활성화된다.

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
