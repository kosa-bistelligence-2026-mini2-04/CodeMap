# LLM API 명세서

> **도메인**: LLM | **최종 업데이트**: 2026-06-25

본 문서는 CodeMap LLM API 명세의 인덱스입니다. 기존 단일 파일 구조는 최신 `chat/` + `agent/` 아키텍처를 반영하기 어렵기 때문에, 사용자-facing API와 확장 API를 파일 단위로 분리합니다.

## 문서 구성

| 파일 | 범위 | 관련 기능 |
| --- | --- | --- |
| `LLM_COMMON_API_SPEC.md` | 공통 응답, 공통 에러, SSE 이벤트 형식 | LLM-OPS |
| `LLM_CHAT_RUN_API_SPEC.md` | run 생성, SSE 스트림 | LLM-CHAT-B-101, LLM-CHAT-B-203 |
| `LLM_RUN_MANAGEMENT_API_SPEC.md` | run 상태 조회, 취소, evidence 조회 | LLM-CHAT-B-204, LLM-EVALUATOR-B-201 |
| `LLM_ADVANCED_API_SPEC.md` | 장기 기억, 허용 외부 도구, reasoning 확장 | LLM-MEMORY-B-201, LLM-WORKER-B-206, LLM-WORKER-B-207 |

## 아키텍처 기준

| 항목 | 기준 |
| --- | --- |
| 실행 생성 | `POST /api/chat/{repo_id}/runs` |
| 스트림 | `GET /api/chat/{repo_id}/runs/{run_id}/stream` |
| 상태 조회 | `GET /api/chat/{repo_id}/runs/{run_id}` |
| 취소 | `POST /api/chat/{repo_id}/runs/{run_id}/cancel` |
| 근거 조회 | `GET /api/chat/{repo_id}/runs/{run_id}/evidence` |
| LangGraph 계층 | `backend/app/agent/` |
| Application 계층 | `backend/app/chat/` |
| 최종 답변 생성 | `chat/final_answer_agent.py` |

## 폐기된 이전 API

> 아래 표의 **소스 코드 상태**는 2026-06-25 기준 `grep -rn` 전수 검색으로 확인했습니다.
> `backend/` 코드에서 라우터 등록이 제거되었고 남은 참조는 HTTP 예시 파일과 명세서 내 설명 문구뿐입니다.

| 이전 API | 처리 | 소스 코드 상태 |
| --- | --- | --- |
| `POST /api/chat/{repo_id}` | `POST /api/chat/{repo_id}/runs` + SSE stream으로 대체 | ✅ 라우터에서 제거 완료. `chat/router.py`에 미존재 확인 |
| `POST /api/chat/{repo_id}/context` | evidence 조회와 worker 결과 기반 flow로 대체 | ✅ 라우터에서 제거 완료. `chat/router.py`에 미존재 확인 |
| `POST /api/search/{repo_id}/grep` | 외부 공개 API가 아니라 내부 `grep_worker` tool contract로 이동 | ⚠️ `backend/tests/http/LLM-TOOL/post-grep-001.http` 예시 파일에 참조 잔존 (구현 시작 전 예시이므로 실제 라우터 미노출) |
| `GET /api/search/{repo_id}/file` | 외부 공개 API가 아니라 내부 `read_worker`/`dir_worker` tool contract로 이동 | ⚠️ `backend/tests/http/LLM-TOOL/get-file-002.http` 예시 파일에 참조 잔존 (구현 시작 전 예시이므로 실제 라우터 미노출) |
| `GET /api/chat/{repo_id}/agent/status` | `GET /api/chat/{repo_id}/runs/{run_id}`로 대체 | ✅ 라우터에서 제거 완료. `agent/router.py`의 `get_run_status`로 대체 확인 |

## 관련 기능 명세

| 기능 명세 | 설명 |
| --- | --- |
| `../spec/LLM_CHAT_SPEC.md` | Chat Application Layer |
| `../spec/LLM_AGENT_SPEC.md` | CodeMapState, LangGraph workflow, dispatcher 보안/fan-out, 이벤트·상태, 메모리(통합본) |
| `../spec/LLM_PLANNER_SPEC.md` | Planner Node 계획 수립 |
| `../spec/LLM_EVALUATOR_SPEC.md` | 근거 집계 및 충분성 평가 |
| `../spec/LLM_TOOL_SPEC.md` | Workers, RRF 하이브리드 검색, 결정론적 도구 실행 |
