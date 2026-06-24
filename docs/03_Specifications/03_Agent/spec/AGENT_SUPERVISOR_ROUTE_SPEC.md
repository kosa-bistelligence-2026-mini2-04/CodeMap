# AGENT SUPERVISOR ROUTE 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-SUPERVISOR / AGENT-ROUTE | **최종 업데이트**: 2026-06-23

## 범위

이 문서는 사용자 질문을 실행 가능한 탐색 계획으로 바꾸는 `Supervisor Agent`와, 그 계획을 검증하고 worker 실행으로 라우팅하는 `Route Node`를 정의합니다.

| 구분 | Supervisor Agent | Route Node |
| --- | --- | --- |
| 구현 위치 | `agent_graph/agents/supervisor_agent.py` | `agent_graph/nodes/route_node.py` |
| 성격 | LLM agent | deterministic code node |
| 책임 | 의도 분석, query rewrite, worker 후보 선택 | schema 검증, path allowlist, traversal 차단, worker fan-out |
| 도구 접근 | 직접 파일 I/O 없음 | 직접 LLM 추론 없음 |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-SUPERVISOR-B-201 | Supervisor Agent 계획 수립 | Backend | Phase 1 |
| AGENT-ROUTE-B-201 | Route Node plan 검증 | Backend | Phase 1 |
| AGENT-ROUTE-B-202 | 경로 보안 및 traversal 차단 | Backend | Phase 1 |
| AGENT-ROUTE-B-203 | Worker 비동기 병렬 라우팅 | Backend | Phase 1 |

---

## AGENT-SUPERVISOR-B-201: Supervisor Agent 계획 수립

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | SUPERVISOR |

**설명**

사용자 질문을 코드 탐색에 적합한 구조화 plan으로 변환합니다. Supervisor는 파일을 직접 읽거나 grep하지 않고, 어떤 worker가 필요한지와 어떤 경로 범위를 우선 볼지 제안합니다.

**입력**

| 필드 | 설명 |
| --- | --- |
| `user_query` | 사용자 원문 질문 |
| `repo_summary` | 저장소 요약/기술 스택 |
| `available_workers` | route node가 허용할 수 있는 worker 목록 |
| `mode` | `lite`, `standard`, `deep` 등 실행 모드 |

**출력 access_plan**

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `rewrittenQuery` | String | 검색용으로 보정된 질의 |
| `intent` | String | `find_file`, `explain_flow`, `debug`, `architecture`, `unknown` |
| `selectedWorkers` | Array<String> | 실행 후보 worker |
| `allowedPaths` | Array<String> | 탐색 우선 경로 후보 |
| `blockedPatterns` | Array<String> | 피해야 할 경로/파일 패턴 힌트 |
| `riskLevel` | String | `normal`, `sensitive`, `blocked` |
| `reason` | String | worker 선택 이유 |

**완료 조건**

- plan은 JSON schema로 파싱 가능해야 합니다.
- Supervisor 출력은 제안일 뿐이며 최종 권한 판단은 Route Node가 합니다.
- `.env`, token, key, secret, private file 접근을 요구하는 질문은 `riskLevel`을 올립니다.

**access_plan JSON 예시**

일반 질문 (find_file):

```json
{
  "rewrittenQuery": "login signin auth authentication 로그인 인증",
  "intent": "find_file",
  "selectedWorkers": ["search", "grep", "read"],
  "allowedPaths": ["backend/app", "frontend/src"],
  "blockedPatterns": [".env", "*.key", "node_modules"],
  "riskLevel": "normal",
  "searchHints": ["login", "signin", "auth", "authentication", "session"],
  "reason": "사용자가 로그인 관련 코드 위치를 묻고 있으므로 인증 관련 키워드로 검색 및 grep 수행 후 후보 파일을 읽습니다."
}
```

민감 경로 접근 질문:

```json
{
  "rewrittenQuery": "database connection configuration 데이터베이스 연결 설정",
  "intent": "explain_flow",
  "selectedWorkers": ["search", "grep", "read"],
  "allowedPaths": ["backend/app/core", "backend/app/db"],
  "blockedPatterns": [".env", "*.pem", "alembic/versions"],
  "riskLevel": "sensitive",
  "searchHints": ["database", "connection", "pool", "session", "engine"],
  "reason": "DB 설정 파일에 credential이 포함될 수 있어 riskLevel을 올립니다. Route Node에서 secret 파일 접근을 추가 검증합니다."
}
```

아키텍처 파악 질문:

```json
{
  "rewrittenQuery": "project directory structure architecture 프로젝트 구조 아키텍처",
  "intent": "architecture",
  "selectedWorkers": ["dir", "search"],
  "allowedPaths": ["backend", "frontend"],
  "blockedPatterns": ["node_modules", "__pycache__", ".git"],
  "riskLevel": "normal",
  "searchHints": ["router", "service", "model", "schema"],
  "reason": "프로젝트 전체 구조 파악이 필요하므로 dir worker로 구조를 먼저 파악하고 search로 핵심 모듈을 찾습니다."
}
```

> `searchHints`는 Supervisor가 `rewrittenQuery` 외에 추가로 제안하는 키워드 목록입니다. Search Worker와 Grep Worker가 보조 검색어로 활용합니다. `CodeMapState.access_plan` 객체 안에 포함됩니다.

---

## AGENT-ROUTE-B-201: Route Node plan 검증

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | ROUTE |

**설명**

Supervisor가 만든 plan을 deterministic code로 검증합니다. 이 node는 LLM이 아니며, plan JSON schema와 worker allowlist를 확인합니다.

**검증 항목**

| 항목 | 기준 |
| --- | --- |
| JSON schema | 필수 필드와 타입 검사 |
| worker allowlist | `search`, `dir`, `grep`, `read`, `reasoning` 중 허용된 worker만 통과 |
| mode policy | `lite`에서는 reasoning_worker 제한 가능 |
| maxToolCalls | 요청/서버 정책 중 더 낮은 값 적용 |
| timeoutSeconds | 서버 상한 초과 불가 |

**출력**

| 필드 | 설명 |
| --- | --- |
| `allowed` | 실행 허용 여부 |
| `selectedWorkers` | 최종 허용 worker 목록 |
| `parallelGroups` | 병렬 실행 가능한 worker 그룹 |
| `blockedReason` | 차단 사유 |

---

## AGENT-ROUTE-B-202: 경로 보안 및 traversal 차단

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | ROUTE |

**설명**

사용자 또는 LLM plan이 repo 외부 파일, 비밀 파일, 시스템 경로에 접근하지 못하도록 차단합니다.

**차단 기준**

| 패턴 | 처리 |
| --- | --- |
| `..` 포함 path | 차단 |
| 절대 경로 | 차단 |
| `.env`, `.pem`, `.key` | 기본 차단 |
| `token`, `secret`, `credential` 포함 파일 | 기본 차단 |
| repo root 밖 resolved path | 차단 |
| binary/large file | worker 정책에 따라 skip |

**완료 조건**

- path 정규화 후 repo root boundary를 검사합니다.
- 차단된 path는 event에 원문 전체를 노출하지 않고 안전하게 축약합니다.
- Route Node가 차단한 작업은 worker에 전달하지 않습니다.

---

## AGENT-ROUTE-B-203: Worker 비동기 병렬 라우팅

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | ROUTE |

**설명**

검증된 plan을 worker 실행으로 변환합니다. 가능한 worker는 병렬로 실행하여 응답 지연을 줄입니다.

**라우팅 원칙**

| Worker | 실행 조건 |
| --- | --- |
| `search_worker` | 자연어/semantic search가 필요한 경우 |
| `dir_worker` | 구조 파악, 경로 후보 탐색이 필요한 경우 |
| `grep_worker` | 키워드, symbol, alias 검색이 필요한 경우 |
| `read_worker` | 후보 파일 경로가 검증된 경우 |
| `reasoning_worker` | 충분한 evidence가 있고 deep mode이거나 사용자가 해석을 요구한 경우 |

**완료 조건**

- worker 실행 전 `worker_started` 이벤트를 발행합니다.
- worker 결과는 상위 node 자연어 요약이 아니라 `CodeMapState.worker_results`에 직접 기록됩니다.
- 일부 worker 실패 시 전체 run을 즉시 실패시킬지, partial evidence로 진행할지 정책을 적용합니다.
