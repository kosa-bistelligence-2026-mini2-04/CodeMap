# RAG GRAPH 기능 명세서

> **도메인**: RAG | **모듈**: RAG-GRAPH | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| RAG-GRAPH-B-201 | 의존성 그래프 시각화 | Backend | Phase 2 |
| RAG-GRAPH-F-201 | 의존성 관계 그래프 UI | Frontend | Phase 2 |

---

## Phase 2

> Phase 2 기능은 Phase 1 MVP 완성 이후 우선순위에 따라 구현합니다.

### RAG-GRAPH-B-201: 의존성 그래프 시각화

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GRAPH |
| 우선순위 | v3 포지셔닝 신규 기능 |

**설명**

Import 관계 노드/엣지 그래프 렌더링을 위한 데이터 처리 및 D3.js 기반 UI. 코드 심볼(함수, 클래스, 모듈) 간 의존성 그래프 구성 및 저장.

**구현 노트**

- RAG-PARSE-B-208의 import 관계 분석 결과를 입력으로 사용
- NetworkX로 그래프 구성
- Frontend용 노드/엣지 JSON 반환


### RAG-GRAPH-F-201: 의존성 관계 그래프 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | GRAPH |
| 우선순위 | v3 포지셔닝 신규 기능 |

**설명**

imports / imported_by 메타데이터 기반 파일 간 의존성을 인터랙티브 그래프(react-flow 또는 mermaid)로 렌더링.

**구현 노트**

- react-flow 또는 mermaid 사용
- 노드 클릭 시 해당 파일 상세 표시
- 줌/패닝 지원


