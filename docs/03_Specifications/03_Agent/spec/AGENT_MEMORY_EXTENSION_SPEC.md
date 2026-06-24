# AGENT MEMORY EXTENSION 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-MEMORY / AGENT-EXTENSION | **최종 업데이트**: 2026-06-23

## 범위

이 문서는 MVP 이후 확장 기능인 장기 기억, 허용 외부 도구 worker, 추가 reasoning run의 경계를 정의합니다. Phase 1의 기본 채팅 실행 경로에는 포함하지 않으며, 사용자 확인과 보안 정책이 필요한 확장 기능으로 취급합니다.

| 구분 | 기준 |
| --- | --- |
| Phase | Phase 2 / 보류 |
| 구현 위치 | `backend/app/chat/`, `backend/app/agent_graph/workers/`, 별도 memory 저장소 |
| 주요 API | `GET /api/chat/{repo_id}/memory`, `GET /api/chat/{repo_id}/tools/allowed`, `POST /api/chat/{repo_id}/runs/{run_id}/reasoning` |
| 기본 원칙 | 자동 write 금지, source run 추적, 사용자 확인 필요한 action 분리 |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-MEMORY-B-201 | 장기 기억 (Long-term Memory) | Backend | Phase 2 |
| AGENT-WORKER-B-206 | 허용된 외부 도구 worker 확장 | Backend | Phase 2 |
| AGENT-WORKER-B-207 | Code Reasoning Worker 고도화 | Backend | Phase 2 |

---

## AGENT-MEMORY-B-201: 장기 기억

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | MEMORY |

**설명**

반복 질문, 팀 합의, 자주 참조하는 파일/모듈 정보를 run 이후 재사용할 수 있는 memory item으로 저장합니다. Memory는 답변 품질 보조 정보이며, source evidence를 대체하지 않습니다.

**Memory item**

| 필드 | 설명 |
| --- | --- |
| `id` | memory ID |
| `repoId` | 대상 repo |
| `summary` | 기억 요약 |
| `sourceRunId` | memory 생성 근거 run |
| `sourceEvidenceIds` | 근거 evidence ID 목록 |
| `confidence` | 신뢰도 |
| `createdAt` | 생성 시각 |
| `lastUsedAt` | 마지막 사용 시각 |

**정책**

- 사용자가 명시적으로 저장을 허용하지 않은 개인 정보는 memory로 저장하지 않습니다.
- memory가 오래되었거나 source evidence가 사라진 경우 답변에서 낮은 신뢰도로 취급합니다.
- 최종 답변은 memory만으로 단정하지 않고 최신 evidence를 우선합니다.

---

## AGENT-WORKER-B-206: 허용된 외부 도구 worker 확장

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | EXTENSION |

**설명**

GitHub issue search, docs search, webhook 등 repo 외부 도구를 worker 형태로 확장합니다. 기본은 read/search action이며, write action은 사용자 확인을 요구합니다.

**정책**

| 정책 | 설명 |
| --- | --- |
| allowlist | repo 또는 workspace별 허용 도구만 노출 |
| action scope | `search`, `read`, `comment`, `write` 등 action별 권한 분리 |
| confirmation | write/comment action은 사용자 확인 필요 |
| audit | 외부 도구 호출 로그와 source run 저장 |

---

## AGENT-WORKER-B-207: Code Reasoning Worker 고도화

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | EXTENSION |

**설명**

이미 수집된 evidence를 기반으로 보안 분석, architecture reasoning, data flow tracing, bug risk 분석 등 고비용 reasoning을 별도 run으로 실행합니다.

**원칙**

- 기존 `worker_results`와 `compact_context`를 입력으로 사용합니다.
- 추가 파일 검색은 `includeNewSearch`가 true이고 Route Node가 허용한 경우에만 수행합니다.
- reasoning 결과도 evidence metadata와 source run을 남깁니다.

---

## Phase 1과의 관계

| Phase 1 기본 경로 | Phase 2 확장 경로 |
| --- | --- |
| 질문마다 fresh evidence 수집 | memory를 보조 context로 사용 |
| 내부 repo worker만 사용 | 허용된 외부 worker 추가 |
| Final Answer Agent가 즉시 답변 | 별도 reasoning run으로 심층 분석 |
| 사용자-facing API는 run/evidence 중심 | memory/tools/reasoning API 추가 |
