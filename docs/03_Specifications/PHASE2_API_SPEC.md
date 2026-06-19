# Phase 2 고도화 기능 API 명세서

본 문서는 CodeMap **Phase 2(고도화)** 기능에 해당하는 API에 대한 상세 명세서입니다.
MVP 이후 점진적으로 도입되는 23개 기능을 포함하며, 각 도메인별로 정리합니다.

> **Phase 2 도메인 목록**:
> - **PROJECT-PIPELINE**: 비동기 깊은 분석 파이프라인
> - **RAG-GRAPH**: 코드 의존성 그래프 시각화
> - **RAG-PARSE 고도화**: 위험 신호 태깅, 기술 스택 점수화
> - **AGENT 고도화**: 장기 기억, Advanced Reasoning, 자율 외부 도구
> - **DOCS-UTIL**: HTML-PDF 변환, 이메일/Slack 공유
> - **PROJECT-REPO**: 중복 저장소 검사

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

---

## PROJECT-PIPELINE API 명세서

> 관련 기능 ID: `PROJECT-PIPELINE-B-201` ~ `PROJECT-PIPELINE-F-301`

---

### PIPELINE-API-001 분석 단계 상태 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/pipeline/{job_id}/stages` |
| Method | GET |
| 관련 기능 ID | `PROJECT-PIPELINE-B-201` |
| 목적 | 비동기 분석 파이프라인의 각 단계별 실행 상태 조회 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Headers

| 헤더명 | 값 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| Authorization | Bearer {access_token} | Y | 인증 토큰 |

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| job_id | UUID | Y | 분석 작업 고유 ID |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.jobId | UUID | 분석 작업 ID |
| data.overallStatus | String | 전체 파이프라인 상태 (queued, running, completed, failed) |
| data.stages | Array<Object> | 각 단계 상태 목록 |
| data.stages[].name | String | 단계명 (clone, parse, embed, agent, docs) |
| data.stages[].status | String | 단계 상태 |
| data.stages[].startedAt | String | 단계 시작 시각 |
| data.stages[].completedAt | String | 단계 완료 시각 (완료된 경우) |
| data.stages[].elapsedSeconds | Float | 단계 소요 시간 |

##### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "jobId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "overallStatus": "running",
    "stages": [
      { "name": "clone", "status": "completed", "startedAt": "2026-06-18T10:00:00Z", "completedAt": "2026-06-18T10:00:30Z", "elapsedSeconds": 30.5 },
      { "name": "parse", "status": "completed", "startedAt": "2026-06-18T10:00:31Z", "completedAt": "2026-06-18T10:01:00Z", "elapsedSeconds": 29.0 },
      { "name": "embed", "status": "running", "startedAt": "2026-06-18T10:01:01Z", "completedAt": null, "elapsedSeconds": null },
      { "name": "agent", "status": "queued", "startedAt": null, "completedAt": null, "elapsedSeconds": null },
      { "name": "docs", "status": "queued", "startedAt": null, "completedAt": null, "elapsedSeconds": null }
    ]
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `JOB_NOT_FOUND` | DB 조회 | 해당 job_id가 존재하지 않음 |

---

### PIPELINE-API-002 비동기 깊은 분석 파이프라인 실행

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/pipeline/{job_id}/deep` |
| Method | POST |
| 관련 기능 ID | `PROJECT-PIPELINE-B-202` |
| 목적 | 기본 분석 완료 후 심층 분석 파이프라인(Advanced Reasoning 포함) 비동기 실행 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| job_id | UUID | Y | 분석 작업 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| includeRiskAnalysis | Boolean | N | true | 위험 신호 태깅 포함 여부 |
| includeStackScore | Boolean | N | true | 기술 스택 점수화 포함 여부 |
| includeDependencyGraph | Boolean | N | true | 의존성 그래프 생성 포함 여부 |

#### 응답(Response)

##### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (202) |
| message | String | "accepted" |
| data.jobId | UUID | 분석 작업 ID |
| data.deepPipelineStatus | String | deep_analysis_queued |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `JOB_NOT_FOUND` | DB 조회 | 작업 없음 |
| 409 | `BASIC_ANALYSIS_NOT_COMPLETED` | 사전 검증 | 기본 분석이 완료되지 않은 상태에서 심층 분석 요청 |
| 500 | `PIPELINE_START_FAILED` | 파이프라인 초기화 | 심층 분석 시작 중 오류 |

---

### PIPELINE-API-003 파이프라인 외부 연동 Webhook 등록

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/pipeline/{job_id}/webhook` |
| Method | POST |
| 관련 기능 ID | `PROJECT-PIPELINE-B-203` |
| 목적 | 분석 완료 시 외부 시스템에 Webhook 알림을 발송하도록 URL 등록 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Request Body

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| webhookUrl | String | Y | Webhook 수신 URL |
| events | Array<String> | Y | 알림 받을 이벤트 목록 (completed, failed) |
| secret | String | N | HMAC 서명 검증용 시크릿 키 |

#### 응답(Response)

##### 성공 응답 - 201 Created

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (201) |
| message | String | "created" |
| data.webhookId | UUID | 등록된 Webhook 고유 ID |
| data.webhookUrl | String | 등록된 Webhook URL |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_WEBHOOK_URL` | URL 검증 | 유효하지 않은 Webhook URL 형식 |
| 404 | `JOB_NOT_FOUND` | DB 조회 | 작업 없음 |

---

## RAG-GRAPH API 명세서

> 관련 기능 ID: `RAG-GRAPH-B-201`, `RAG-GRAPH-F-201`

---

### GRAPH-API-001 코드 의존성 그래프 생성

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/graph/{repo_id}` |
| Method | POST |
| 관련 기능 ID | `RAG-GRAPH-B-201` |
| 목적 | import 관계를 기반으로 코드 의존성 그래프 데이터 생성 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 그래프 생성 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| maxDepth | Integer | N | 3 | 의존성 탐색 최대 깊이 |
| excludePaths | Array<String> | N | [] | 그래프에서 제외할 경로 목록 |

#### 응답(Response)

##### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (202) |
| message | String | "accepted" |
| data.graphId | UUID | 생성된 그래프 고유 ID |
| data.status | String | graph_queued |

---

### GRAPH-API-002 의존성 그래프 데이터 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/graph/{repo_id}` |
| Method | GET |
| 관련 기능 ID | `RAG-GRAPH-B-201`, `RAG-GRAPH-F-201` |
| 목적 | 프론트엔드 시각화용 코드 의존성 그래프 데이터 반환 |
| 상태 | 시작 전 (Phase 2) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.nodes | Array<Object> | 그래프 노드 목록 (파일) |
| data.nodes[].id | String | 노드 ID (파일 경로) |
| data.nodes[].label | String | 표시 레이블 (파일명) |
| data.nodes[].type | String | 노드 유형 (entry, service, model 등) |
| data.nodes[].riskScore | Integer | 위험도 점수 (0-100) |
| data.edges | Array<Object> | 그래프 엣지 목록 (의존성) |
| data.edges[].source | String | 참조하는 파일 경로 |
| data.edges[].target | String | 참조되는 파일 경로 |
| data.edges[].type | String | 의존성 유형 (import, export) |

##### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "nodes": [
      { "id": "backend/app/main.py", "label": "main.py", "type": "entry", "riskScore": 20 },
      { "id": "backend/app/repo/service.py", "label": "service.py", "type": "service", "riskScore": 45 }
    ],
    "edges": [
      { "source": "backend/app/main.py", "target": "backend/app/repo/service.py", "type": "import" }
    ]
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `GRAPH_NOT_FOUND` | DB 조회 | 의존성 그래프가 아직 생성되지 않음 |
| 500 | `GRAPH_BUILD_FAILED` | 그래프 처리 | 의존성 그래프 생성 중 오류 |

---

## RAG-PARSE 고도화 API 명세서

> 관련 기능 ID: `RAG-PARSE-B-211`, `RAG-PARSE-B-212`, `RAG-PARSE-F-202`

---

### PARSE-ADVANCED-API-001 위험 신호 태깅 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}/risks` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-211` |
| 목적 | 코드 복잡도, 민감정보 패턴, 병목 파일 등 위험 신호 태깅 결과 반환 |
| 상태 | 시작 전 (Phase 2) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.risks | Array<Object> | 위험 신호 목록 |
| data.risks[].path | String | 위험 파일 경로 |
| data.risks[].type | String | 위험 유형 (high_complexity, sensitive_data, bottleneck 등) |
| data.risks[].severity | String | 심각도 (critical, high, medium, low) |
| data.risks[].description | String | 위험 사유 설명 |
| data.risks[].riskScore | Integer | 위험도 점수 (0-100) |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `RISK_ANALYSIS_NOT_FOUND` | DB 조회 | 위험 분석 결과가 없음 |
| 500 | `RISK_ANALYSIS_FAILED` | 분석 처리 | 위험 신호 분석 중 오류 |

---

### PARSE-ADVANCED-API-002 기술 스택 점수화 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}/stack-score` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-212`, `RAG-PARSE-F-202` |
| 목적 | 기술 스택 성숙도, 보안 취약점 버전 여부, 최신성 점수 반환 |
| 상태 | 시작 전 (Phase 2) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.overallScore | Integer | 전체 기술 스택 점수 (0-100) |
| data.stacks | Array<Object> | 개별 기술별 점수 |
| data.stacks[].name | String | 기술명 |
| data.stacks[].version | String | 사용 버전 |
| data.stacks[].latestVersion | String | 최신 버전 |
| data.stacks[].score | Integer | 기술별 점수 |
| data.stacks[].hasVulnerability | Boolean | 알려진 보안 취약점 여부 |
| data.stacks[].isOutdated | Boolean | 구버전 여부 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `STACK_SCORE_NOT_FOUND` | DB 조회 | 점수화 결과 없음 |
| 500 | `STACK_SCORE_FAILED` | 점수 계산 | 기술 스택 점수화 처리 중 오류 |

---

## AGENT 고도화 API 명세서

> 관련 기능 ID: `AGENT-CHAT-B-203`, `AGENT-SEARCH-B-206`, `AGENT-SEARCH-B-207`

---

### AGENT-ADVANCED-API-001 에이전트 장기 기억 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/chat/{repo_id}/memory` |
| Method | GET |
| 관련 기능 ID | `AGENT-CHAT-B-203` |
| 목적 | 이전 대화 세션에서 에이전트가 학습한 장기 기억 컨텍스트 조회 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 저장소 고유 ID |

##### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| userId | String | N | - | 사용자 ID (없으면 전체 조회) |
| limit | Integer | N | 20 | 반환할 최대 기억 항목 수 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.memories | Array<Object> | 장기 기억 목록 |
| data.memories[].key | String | 기억 키 (파일명, 개념명 등) |
| data.memories[].value | String | 기억 내용 |
| data.memories[].createdAt | String | 기억 생성 시각 |
| data.memories[].accessCount | Integer | 참조 횟수 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `MEMORY_RETRIEVAL_FAILED` | 기억 조회 | 장기 기억 조회 중 오류 |

---

## DOCS-UTIL API 명세서

> 관련 기능 ID: `DOCS-UTIL-B-201`, `DOCS-UTIL-B-202`

---

### UTIL-API-001 HTML-PDF 파일 렌더링 및 변환

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/gen/docs/{repo_id}/export/pdf` |
| Method | POST |
| 관련 기능 ID | `DOCS-UTIL-B-201` |
| 목적 | 온보딩 가이드북 Markdown을 서버 사이드에서 PDF로 변환하여 다운로드 제공 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | PDF 변환 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| theme | String | N | default | PDF 스타일 테마 (default, dark, minimal) |
| includeCodeHighlight | Boolean | N | true | 코드 블록 구문 강조 포함 여부 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 헤더명 | 값 | 설명 |
| :--- | :--- | :--- |
| Content-Type | application/pdf | PDF 파일 |
| Content-Disposition | attachment; filename="{repoName}_onboarding.pdf" | 다운로드 파일명 |

> 응답 body는 PDF 바이너리 데이터입니다.

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `DOCS_NOT_FOUND` | DB 조회 | 가이드북 없음 |
| 500 | `PDF_RENDER_FAILED` | PDF 변환 | HTML→PDF 렌더링 중 오류 |

---

### UTIL-API-002 이메일 및 Slack 외부 공유

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/gen/docs/{repo_id}/share` |
| Method | POST |
| 관련 기능 ID | `DOCS-UTIL-B-202` |
| 목적 | 분석 완료된 온보딩 가이드북을 이메일 또는 Slack 채널로 공유 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 공유 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| channels | Array<Object> | Y | - | 공유 채널 목록 |
| channels[].type | String | Y | - | 채널 유형 (email / slack) |
| channels[].target | String | Y | - | 이메일 주소 또는 Slack Webhook URL |
| includeFullGuide | Boolean | N | false | 가이드북 전문 포함 여부 (false면 요약만) |

##### 요청 예시

```json
{
  "channels": [
    { "type": "email", "target": "newdev@company.com" },
    { "type": "slack", "target": "https://hooks.slack.com/services/T00/B00/xxx" }
  ],
  "includeFullGuide": false
}
```

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.sentChannels | Array<Object> | 발송 성공 채널 목록 |
| data.failedChannels | Array<Object> | 발송 실패 채널 목록 |
| data.sentAt | String | 발송 시각 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_CHANNEL` | 채널 검증 | 유효하지 않은 이메일 또는 Slack URL |
| 404 | `DOCS_NOT_FOUND` | DB 조회 | 가이드북 없음 |
| 500 | `SHARE_FAILED` | 발송 처리 | 이메일 또는 Slack 발송 중 오류 |

---

## PROJECT-REPO 고도화 API 명세서

> 관련 기능 ID: `PROJECT-REPO-B-303`

---

### REPO-ADVANCED-API-001 중복 저장소 검사

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/repo/check-duplicate` |
| Method | POST |
| 관련 기능 ID | `PROJECT-REPO-B-303` |
| 목적 | 동일한 GitHub URL의 분석 이력 존재 여부 사전 확인 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Request Body

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repoUrl | String | Y | 중복 검사할 GitHub 저장소 URL |
| branch | String | N | 검사 대상 브랜치 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.isDuplicate | Boolean | 중복 여부 |
| data.existingJob | Object | 기존 분석 작업 정보 (중복인 경우) |
| data.existingJob.jobId | UUID | 기존 작업 ID |
| data.existingJob.status | String | 기존 작업 상태 |
| data.existingJob.createdAt | String | 기존 작업 생성 시각 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_REPO_URL` | URL 검증 | 잘못된 GitHub URL 형식 |
| 500 | `DATABASE_ERROR` | DB 조회 | 데이터베이스 조회 중 오류 |

---

## 에러 코드 정의

| Error Code | HTTP Status | 설명 |
| :--- | :--- | :--- |
| `BASIC_ANALYSIS_NOT_COMPLETED` | 409 | 기본 분석이 완료되지 않은 상태 |
| `INVALID_WEBHOOK_URL` | 400 | 유효하지 않은 Webhook URL |
| `GRAPH_NOT_FOUND` | 404 | 의존성 그래프가 생성되지 않음 |
| `GRAPH_BUILD_FAILED` | 500 | 의존성 그래프 생성 실패 |
| `RISK_ANALYSIS_NOT_FOUND` | 404 | 위험 신호 분석 결과 없음 |
| `RISK_ANALYSIS_FAILED` | 500 | 위험 신호 분석 처리 실패 |
| `STACK_SCORE_NOT_FOUND` | 404 | 기술 스택 점수화 결과 없음 |
| `STACK_SCORE_FAILED` | 500 | 기술 스택 점수화 실패 |
| `MEMORY_RETRIEVAL_FAILED` | 500 | 에이전트 장기 기억 조회 실패 |
| `PDF_RENDER_FAILED` | 500 | HTML→PDF 렌더링 실패 |
| `SHARE_FAILED` | 500 | 이메일 또는 Slack 발송 실패 |
| `INVALID_CHANNEL` | 400 | 유효하지 않은 이메일 또는 Slack URL |
