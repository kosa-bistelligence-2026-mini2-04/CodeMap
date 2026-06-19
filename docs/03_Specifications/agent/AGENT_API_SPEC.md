# AGENT API 명세서

본 문서는 CodeMap 백엔드의 **AGENT** 도메인 API에 대한 상세 명세서입니다.
AGENT 도메인은 `CHAT`(대화형 코드 Q&A), `SEARCH`(자율 탐색), `CORE`(에이전트 실행 관리) 세 모듈로 구성됩니다.

> **핵심 특징**: GPT-4o 기반 자가 교정(Self-Correction) 에이전트로, 최대 5회 도구 호출 + 20초 타임아웃 제한 내에서 코드를 자율 탐색합니다.

---

## 공통 규격

### 응답 공통 형식

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 에러 응답 공통 형식

```json
{
  "code": 400,
  "message": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "사용자 표시용 메시지",
    "detail": "개발자 디버깅용 상세 메시지"
  }
}
```

---

## AGENT-CHAT API 명세서

> 관련 기능 ID: `AGENT-CHAT-B-101`, `AGENT-CHAT-B-201`, `AGENT-CHAT-B-202`, `AGENT-CHAT-B-203`

---

### AGENT-CHAT-API-001 Repo Chat (SSE 스트리밍)

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/chat/{repo_id}` |
| Method | POST |
| 관련 기능 ID | `AGENT-CHAT-B-101` |
| 목적 | 저장소에 대한 자연어 질문을 받아 Agentic RAG 기반으로 SSE 스트리밍 답변 반환 |
| 상태 | 시작 전 |

> 에이전트는 도구 호출 **최대 5회**, 실행 시간 **최대 20초** 제한 내에서 자율 탐색 후 답변을 생성합니다.

#### 요청(Request)

##### Headers

| 헤더명 | 값 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| Content-Type | application/json | Y | 요청 본문 형식 |
| Authorization | Bearer {access_token} | Y | 인증 토큰 |
| Accept | text/event-stream | Y | SSE 스트리밍 응답 수신 |

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 질문 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| question | String | Y | - | 사용자 자연어 질문 |
| maxToolCalls | Integer | N | 5 | 에이전트 도구 호출 최대 횟수 |
| timeoutSeconds | Integer | N | 20 | 에이전트 탐색 최대 시간 (초) |

##### 요청 예시

```http
POST /api/chat/3f7cc46e-d954-83ab-9f12-013b0c9d2a1e HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Authorization: Bearer eyJhbGci...
Accept: text/event-stream

{
  "question": "이 프로젝트에서 RAG 임베딩 로직은 어느 파일에 있나요?",
  "maxToolCalls": 5,
  "timeoutSeconds": 20
}
```

#### 응답(Response) - SSE 스트리밍

##### 이벤트 타입별 데이터 포맷

| 이벤트 타입 | 데이터 필드 | 설명 |
| :--- | :--- | :--- |
| `agent_status` | step, message, toolCalls | 에이전트 탐색 단계 진행 상황 |
| `token` | content | LLM 답변 토큰 (타이핑 효과용) |
| `agent_completed` | answer, sourceFiles, toolCallCount, elapsedSeconds | 최종 답변 및 탐색 통계 |
| `agent_failed` | error, partialAnswer | 탐색 실패 또는 타임아웃 시 수집된 정보 기반 최선 답변 |

##### agent_status 이벤트 예시

```
event: agent_status
data: {
  "step": 1,
  "message": "관련 파일을 벡터 검색 중...",
  "toolCalls": ["search_vector_db"]
}
```

##### token 이벤트 예시

```
event: token
data: {
  "content": "RAG 임베딩 로직은"
}
```

##### agent_completed 이벤트 예시

```
event: agent_completed
data: {
  "answer": "RAG 임베딩 로직은 `backend/app/embed/service.py`에 구현되어 있습니다...",
  "sourceFiles": [
    { "path": "backend/app/embed/service.py", "lines": "12-45" },
    { "path": "backend/app/embed/repository.py", "lines": "8-32" }
  ],
  "toolCallCount": 3,
  "elapsedSeconds": 8.2
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 404 | `EMBEDDING_NOT_READY` | 사전 검증 | 임베딩이 완료되지 않아 검색 불가 |
| 422 | `QUESTION_TOO_LONG` | 입력 검증 | 질문이 최대 길이 초과 |
| 500 | `AGENT_INTERNAL_ERROR` | 에이전트 실행 | LLM 호출 또는 도구 실행 중 내부 오류 |

---

### AGENT-CHAT-API-002 코드 컨텍스트 검색

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/chat/{repo_id}/context` |
| Method | POST |
| 관련 기능 ID | `AGENT-CHAT-B-201` |
| 목적 | 자연어 질문과 의미적으로 관련된 코드 파일을 벡터 검색으로 조회 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 검색 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| question | String | Y | - | 검색 쿼리 (자연어 질문) |
| topK | Integer | N | 5 | 반환할 최대 관련 파일 수 |
| threshold | Float | N | 0.7 | 코사인 유사도 최소 임계값 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.question | String | 입력된 질문 |
| data.results | Array<Object> | 관련 코드 청크 목록 |
| data.results[].filePath | String | 파일 경로 |
| data.results[].startLine | Integer | 코드 청크 시작 줄 |
| data.results[].endLine | Integer | 코드 청크 끝 줄 |
| data.results[].content | String | 코드 청크 내용 |
| data.results[].similarity | Float | 코사인 유사도 점수 |
| data.results[].language | String | 프로그래밍 언어 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `VECTOR_SEARCH_FAILED` | 벡터 검색 | pgvector 검색 중 오류 |

---

## AGENT-SEARCH API 명세서

> 관련 기능 ID: `AGENT-SEARCH-B-201` ~ `AGENT-SEARCH-B-206`

---

### AGENT-SEARCH-API-001 Grep 기반 코드 키워드 검색

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/search/{repo_id}/grep` |
| Method | POST |
| 관련 기능 ID | `AGENT-SEARCH-B-205` |
| 목적 | LLM 에이전트 도구로 사용되는 소스코드 내 키워드/정규식 grep 검색 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 검색 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| pattern | String | Y | - | 검색할 키워드 또는 정규식 패턴 |
| isRegex | Boolean | N | false | 정규식 패턴 여부 |
| fileExtensions | Array<String> | N | 전체 | 검색 대상 파일 확장자 필터 |
| maxResults | Integer | N | 20 | 반환할 최대 결과 수 |

##### 요청 예시

```json
{
  "pattern": "def embed_code",
  "isRegex": false,
  "fileExtensions": [".py"],
  "maxResults": 10
}
```

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.pattern | String | 검색에 사용된 패턴 |
| data.totalMatches | Integer | 전체 매칭 수 |
| data.results | Array<Object> | 검색 결과 목록 |
| data.results[].filePath | String | 파일 경로 |
| data.results[].lineNumber | Integer | 매칭 줄 번호 |
| data.results[].lineContent | String | 매칭 줄 내용 |
| data.results[].context | String | 앞뒤 3줄 컨텍스트 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_PATTERN` | 패턴 검증 | 정규식 패턴 문법 오류 |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `GREP_FAILED` | grep 실행 | grep 도구 실행 중 오류 |

---

### AGENT-SEARCH-API-002 파일 내용 및 디렉토리 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/search/{repo_id}/file` |
| Method | GET |
| 관련 기능 ID | `AGENT-SEARCH-B-206` |
| 목적 | LLM 에이전트 도구로 사용되는 파일 내용 읽기 및 디렉토리 구조 조회 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 조회 대상 저장소 고유 ID |

##### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| path | String | Y | - | 조회할 파일 또는 디렉토리 경로 |
| startLine | Integer | N | 1 | 파일 읽기 시작 줄 (파일인 경우) |
| endLine | Integer | N | 200 | 파일 읽기 끝 줄 (파일인 경우, 최대 200줄) |

#### 응답(Response)

##### 파일 조회 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.type | String | "file" |
| data.path | String | 파일 경로 |
| data.language | String | 프로그래밍 언어 |
| data.totalLines | Integer | 파일 전체 줄 수 |
| data.content | String | 요청된 범위의 파일 내용 |
| data.startLine | Integer | 반환된 내용의 시작 줄 |
| data.endLine | Integer | 반환된 내용의 끝 줄 |

##### 디렉토리 조회 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| data.type | String | "directory" |
| data.path | String | 디렉토리 경로 |
| data.children | Array<Object> | 하위 항목 목록 |
| data.children[].name | String | 항목 이름 |
| data.children[].type | String | file 또는 directory |
| data.children[].size | Integer | 파일 크기 (파일인 경우) |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_PATH` | 경로 검증 | 경로 형식이 잘못되었거나 접근 금지 경로 |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 404 | `FILE_NOT_FOUND` | 파일 접근 | 요청한 경로의 파일이 없음 |
| 500 | `FILE_READ_FAILED` | 파일 읽기 | 파일 읽기 중 오류 |

---

## AGENT-CORE API 명세서

> 관련 기능 ID: `AGENT-CORE-B-201` ~ `AGENT-CORE-B-204`, `AGENT-CORE-F-201`

---

### AGENT-CORE-API-001 에이전트 실행 상태 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/chat/{repo_id}/agent/status` |
| Method | GET |
| 관련 기능 ID | `AGENT-CORE-B-201`, `AGENT-CORE-B-203` |
| 목적 | 현재 실행 중인 에이전트의 상태 및 실행 시간 조회 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 에이전트가 탐색 중인 저장소 고유 ID |

##### Query Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| sessionId | String | Y | 에이전트 실행 세션 ID |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.sessionId | String | 에이전트 세션 ID |
| data.status | String | running / completed / failed / timeout |
| data.currentStep | Integer | 현재 도구 호출 횟수 |
| data.maxSteps | Integer | 최대 도구 호출 횟수 (5) |
| data.elapsedSeconds | Float | 경과 시간 (초) |
| data.maxSeconds | Integer | 최대 실행 시간 (20) |
| data.currentAction | String | 현재 수행 중인 작업 설명 |
| data.startedAt | String | 에이전트 시작 시각 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `SESSION_NOT_FOUND` | 세션 조회 | 해당 세션 ID가 없거나 만료됨 |

---

### AGENT-CORE-API-002 Report JSON 스펙 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/chat/{repo_id}/report` |
| Method | GET |
| 관련 기능 ID | `AGENT-CORE-F-201` |
| 목적 | Frontend와 Backend 간의 분석 리포트 JSON 계약 형식 반환 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 저장소 고유 ID |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.summary | String | 프로젝트 마스터 요약 |
| data.stack | Array<String> | 기술 스택 목록 |
| data.fileMap | Array<Object> | 파일 단위 코드 맵 |
| data.recommendations | Array<String> | 신입 개발자 추천 읽기 순서 |
| data.heatmap | Array<Object> | 파일 복잡도 히트맵 |
| data.durations | Object | 각 에이전트 실행 시간 측정 결과 |
| data.durations.parseSeconds | Float | PARSE 에이전트 실행 시간 |
| data.durations.embedSeconds | Float | EMBED 에이전트 실행 시간 |
| data.durations.agentSeconds | Float | AGENT 탐색 실행 시간 |
| data.durations.docsSeconds | Float | DOCS 생성 실행 시간 |
| data.guide | String | 온보딩 가이드북 Markdown 전문 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 404 | `REPORT_NOT_FOUND` | DB 조회 | 분석 리포트가 아직 생성되지 않음 |

---

## 에러 코드 정의

| Error Code | HTTP Status | 설명 |
| :--- | :--- | :--- |
| `EMBEDDING_NOT_READY` | 404 | 임베딩이 완료되지 않아 검색 불가 |
| `QUESTION_TOO_LONG` | 422 | 질문이 최대 허용 길이 초과 |
| `AGENT_INTERNAL_ERROR` | 500 | LLM 호출 또는 도구 실행 중 내부 오류 |
| `VECTOR_SEARCH_FAILED` | 500 | pgvector 유사도 검색 실패 |
| `INVALID_PATTERN` | 400 | 정규식 패턴 문법 오류 |
| `GREP_FAILED` | 500 | grep 도구 실행 중 오류 |
| `INVALID_PATH` | 400 | 잘못된 파일 경로 또는 접근 금지 경로 |
| `FILE_NOT_FOUND` | 404 | 요청 경로의 파일이 없음 |
| `FILE_READ_FAILED` | 500 | 파일 읽기 중 오류 |
| `SESSION_NOT_FOUND` | 404 | 에이전트 세션 없거나 만료됨 |
| `REPORT_NOT_FOUND` | 404 | 분석 리포트가 아직 생성되지 않음 |
