# AGENT API 명세서

> **도메인**: AGENT | **최종 업데이트**: 2026-06-23

본 문서는 CodeMap AGENT API 명세의 인덱스입니다. 기존 단일 파일 구조는 최신 `chat/` + `agent_graph/` 아키텍처를 반영하기 어렵기 때문에, 사용자-facing API와 확장 API를 파일 단위로 분리합니다.

## 문서 구성

| 파일 | 범위 | 관련 기능 |
| --- | --- | --- |
| `AGENT_COMMON_API_SPEC.md` | 공통 응답, 공통 에러, SSE 이벤트 형식 | AGENT-CORE |
| `AGENT_CHAT_RUN_API_SPEC.md` | run 생성, SSE 스트림 | AGENT-CHAT-B-101, AGENT-CHAT-B-203 |
| `AGENT_RUN_MANAGEMENT_API_SPEC.md` | run 상태 조회, 취소, evidence 조회 | AGENT-CHAT-B-204, AGENT-EVIDENCE-B-201 |
| `AGENT_ADVANCED_API_SPEC.md` | 장기 기억, 허용 외부 도구, reasoning 확장 | AGENT-MEMORY-B-201, AGENT-WORKER-B-206, AGENT-WORKER-B-207 |

## 아키텍처 기준

| 항목 | 기준 |
| --- | --- |
| 실행 생성 | `POST /api/chat/{repo_id}/runs` |
| 스트림 | `GET /api/chat/{repo_id}/runs/{run_id}/stream` |
| 상태 조회 | `GET /api/chat/{repo_id}/runs/{run_id}` |
| 취소 | `POST /api/chat/{repo_id}/runs/{run_id}/cancel` |
| 근거 조회 | `GET /api/chat/{repo_id}/runs/{run_id}/evidence` |
| LangGraph 계층 | `backend/app/agent_graph/` |
| Application 계층 | `backend/app/chat/` |
| 최종 답변 생성 | `chat/final_answer_agent.py` |

## 폐기된 이전 API

| 이전 API | 처리 |
| --- | --- |
| `POST /api/chat/{repo_id}` | `POST /api/chat/{repo_id}/runs` + SSE stream으로 대체 |
| `POST /api/chat/{repo_id}/context` | evidence 조회와 worker 결과 기반 flow로 대체 |
| `POST /api/search/{repo_id}/grep` | 외부 공개 API가 아니라 내부 `grep_worker` tool contract로 이동 |
| `GET /api/search/{repo_id}/file` | 외부 공개 API가 아니라 내부 `read_worker`/`dir_worker` tool contract로 이동 |
| `GET /api/chat/{repo_id}/agent/status` | `GET /api/chat/{repo_id}/runs/{run_id}`로 대체 |

## 관련 기능 명세

| 기능 명세 | 설명 |
| --- | --- |
| `../spec/AGENT_CHAT_SPEC.md` | Chat Application Layer |
| `../spec/AGENT_CORE_SPEC.md` | 이벤트, 상태, 실패 처리 |
| `../spec/AGENT_GRAPH_SPEC.md` | CodeMapState, LangGraph workflow |
| `../spec/AGENT_SUPERVISOR_ROUTE_SPEC.md` | Supervisor Agent, Route Node |
| `../spec/AGENT_WORKER_EVIDENCE_SPEC.md` | Workers, Evidence Aggregator |
| `../spec/AGENT_MEMORY_EXTENSION_SPEC.md` | Memory, external tools, advanced reasoning |
