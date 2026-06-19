# DOCS GUARD 기능 명세서

> **도메인**: DOCS | **모듈**: DOCS-GUARD | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| DOCS-GUARD-B-201 | 민감정보 마스킹 | Backend | Phase 2 |

---

## Phase 2

> Phase 2 기능은 Phase 1 MVP 완성 이후 우선순위에 따라 구현합니다.

### DOCS-GUARD-B-201: 민감정보 마스킹

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GUARD |
| 우선순위 | Phase 2 기능 |

**설명**

API key, token, password pattern 탐지 시 원문 제거. report 생성 전 report에 민감정보 원문이 노출되지 않도록 검증.

**구현 노트**

- 정규식 패턴: AWS key, JWT token, DB connection string 등
- 탐지 시 `[MASKED]`로 대체
- 보고서 생성 파이프라인 전처리 단계에 통합


