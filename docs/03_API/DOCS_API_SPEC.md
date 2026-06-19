# DOCS API 명세서

본 문서는 CodeMap 백엔드의 **DOCS** 도메인 API에 대한 상세 명세서입니다.
DOCS 도메인은 `GEN`(가이드북 생성), `GUARD`(민감정보 보호) 두 모듈로 구성됩니다.

> **핵심 특징**: Map-Reduce 방식으로 파일→폴더→프로젝트 단계를 거쳐 신입 개발자용 온보딩 가이드북을 자동 생성합니다.

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

## DOCS-GEN API 명세서

> 관련 기능 ID: `DOCS-GEN-B-101` ~ `DOCS-GEN-B-207`, `DOCS-GEN-F-101` ~ `DOCS-GEN-F-205`

---

### DOCS-GEN-API-001 온보딩 가이드북 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/gen/docs/{repo_id}` |
| Method | GET |
| 관련 기능 ID | `DOCS-GEN-B-101` |
| 목적 | 생성 완료된 온보딩 가이드북 Markdown 전문 반환 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Headers

| 헤더명 | 값 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| Authorization | Bearer {access_token} | Y | 인증 토큰 |
| Accept | application/json | N | 응답 형식 |

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 가이드북 조회 대상 저장소 고유 ID |

##### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| format | String | N | markdown | 반환 형식 (markdown / json) |

##### 요청 예시

```http
GET /api/gen/docs/3f7cc46e-d954-83ab-9f12-013b0c9d2a1e?format=markdown HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGci...
```

#### 응답(Response)

##### 성공 응답 - 200 OK (format=markdown)

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.repoName | String | 저장소 이름 |
| data.content | String | 온보딩 가이드북 전체 Markdown 내용 |
| data.generatedAt | String | 가이드북 생성 시각 |
| data.version | Integer | 가이드북 버전 (재생성 시 증가) |

##### 성공 응답 - 200 OK (format=json)

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| data.summary | String | 프로젝트 요약 |
| data.stack | Array<String> | 기술 스택 목록 |
| data.readingOrder | Array<Object> | 추천 파일 읽기 순서 |
| data.readingOrder[].rank | Integer | 읽기 우선순위 순위 |
| data.readingOrder[].path | String | 파일 경로 |
| data.readingOrder[].reason | String | 이 파일을 먼저 읽어야 하는 이유 |
| data.dangerFiles | Array<Object> | 주의/위험 파일 목록 |
| data.dangerFiles[].path | String | 파일 경로 |
| data.dangerFiles[].reason | String | 위험 사유 (민감 정보, 고복잡도 등) |
| data.coreFlow | String | 핵심 실행 플로우 설명 |
| data.folderSummaries | Array<Object> | 폴더 단위 요약 |

##### 응답 예시 (format=json)

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "repoId": "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
    "repoName": "CodeMap",
    "summary": "GitHub 레포를 분석해 신입 개발자용 온보딩 가이드를 자동 생성하는 AI 웹앱",
    "stack": ["Python 3.12", "FastAPI", "Next.js 16", "PostgreSQL", "pgvector", "GPT-4o"],
    "readingOrder": [
      { "rank": 1, "path": "docs/GETTING_STARTED.md", "reason": "프로젝트 목적과 실행 방법 파악" },
      { "rank": 2, "path": "backend/app/main.py", "reason": "FastAPI 앱 진입점 및 라우터 구성 파악" }
    ],
    "dangerFiles": [
      { "path": "backend/app/core/config.py", "reason": "API 키 등 환경변수 관리 파일. 직접 수정 주의" }
    ],
    "coreFlow": "사용자 GitHub URL 입력 → Clone → Parse → Embed → Agent 탐색 → Docs 생성",
    "generatedAt": "2026-06-18T10:15:00Z",
    "version": 1
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 404 | `DOCS_NOT_FOUND` | DB 조회 | 가이드북이 아직 생성되지 않음 |
| 500 | `DATABASE_ERROR` | DB 조회 | 데이터베이스 조회 중 예외 발생 |

---

### DOCS-GEN-API-002 가이드북 생성 트리거

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/gen/docs/{repo_id}` |
| Method | POST |
| 관련 기능 ID | `DOCS-GEN-B-201`, `DOCS-GEN-B-202`, `DOCS-GEN-B-203`, `DOCS-GEN-B-204` |
| 목적 | Map-Reduce 파이프라인으로 온보딩 가이드북 생성 시작 |
| 상태 | 시작 전 |

> **생성 파이프라인 순서**: 문서 요약 agent → 폴더 단위 요약 → 온보딩 guide agent → 마스터 리포트 통합

#### 요청(Request)

##### Headers

| 헤더명 | 값 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| Authorization | Bearer {access_token} | Y | 인증 토큰 |
| Content-Type | application/json | Y | 요청 본문 형식 |

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 가이드북 생성 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| force | Boolean | N | false | 기존 가이드북 덮어쓰기 여부 |
| model | String | N | gpt-4o-mini | 문서 생성에 사용할 LLM 모델 |

##### 요청 예시

```json
{
  "force": false,
  "model": "gpt-4o-mini"
}
```

#### 응답(Response)

##### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (202) |
| message | String | "accepted" |
| data.jobId | UUID | 문서 생성 작업 ID |
| data.repoId | UUID | 저장소 ID |
| data.status | String | docs_queued |
| data.estimatedMinutes | Integer | 예상 생성 소요 시간 (분) |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 409 | `DOCS_ALREADY_EXISTS` | 중복 검사 | 가이드북이 이미 존재하고 force=false인 경우 |
| 409 | `DOCS_GENERATION_IN_PROGRESS` | 중복 검사 | 가이드북 생성이 이미 진행 중 |
| 422 | `ANALYSIS_NOT_COMPLETED` | 사전 검증 | RAG 파이프라인(Parse/Embed)이 완료되지 않음 |
| 500 | `DOCS_GENERATION_FAILED` | LLM 처리 | 가이드북 생성 중 오류 |

---

### DOCS-GEN-API-003 가이드북 재생성

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `PUT /api/gen/docs/{repo_id}` |
| Method | PUT |
| 관련 기능 ID | `DOCS-GEN-B-207` |
| 목적 | 기존 분석 기반으로 온보딩 가이드북 재생성 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 재생성 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| model | String | N | gpt-4o-mini | 재생성에 사용할 LLM 모델 |
| reason | String | N | - | 재생성 요청 사유 (로그용) |

#### 응답(Response)

##### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (202) |
| message | String | "accepted" |
| data.jobId | UUID | 재생성 작업 ID |
| data.repoId | UUID | 저장소 ID |
| data.previousVersion | Integer | 기존 가이드북 버전 |
| data.newVersion | Integer | 생성될 새 가이드북 버전 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 404 | `DOCS_NOT_FOUND` | DB 조회 | 재생성할 기존 가이드북이 없음 |
| 500 | `DOCS_GENERATION_FAILED` | LLM 처리 | 재생성 중 오류 |

---

### DOCS-GEN-API-004 가이드북 Markdown 파일 다운로드

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/gen/docs/{repo_id}/download` |
| Method | GET |
| 관련 기능 ID | `DOCS-GEN-F-201` |
| 목적 | 생성된 온보딩 가이드북을 `.md` 파일로 다운로드 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 다운로드 대상 저장소 고유 ID |

##### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| format | String | N | md | 다운로드 형식 (md / pdf) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 헤더명 | 값 | 설명 |
| :--- | :--- | :--- |
| Content-Type | text/markdown; charset=utf-8 | Markdown 파일 |
| Content-Disposition | attachment; filename="{repoName}_onboarding.md" | 다운로드 파일명 |

> 응답 body는 Markdown 파일 원문입니다.

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 404 | `DOCS_NOT_FOUND` | DB 조회 | 가이드북이 아직 생성되지 않음 |
| 500 | `FILE_GENERATION_FAILED` | 파일 생성 | Markdown 또는 PDF 파일 생성 중 오류 |

---

### DOCS-GEN-API-005 Markdown DB 저장

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/gen/docs/{repo_id}/save` |
| Method | POST |
| 관련 기능 ID | `DOCS-GEN-B-301` |
| 목적 | 생성된 Markdown 가이드북을 PostgreSQL DB에 저장 (내부 파이프라인 호출용) |
| 상태 | 시작 전 |

> 이 API는 내부 파이프라인에서 호출하는 API입니다. 프론트엔드에서 직접 호출하지 않습니다.

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 저장 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| content | String | Y | 저장할 Markdown 가이드북 전문 |
| version | Integer | Y | 가이드북 버전 |
| jobId | UUID | Y | 연결된 분석 작업 ID |

#### 응답(Response)

##### 성공 응답 - 201 Created

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (201) |
| message | String | "created" |
| data.docId | UUID | 저장된 문서 고유 ID |
| data.repoId | UUID | 저장소 ID |
| data.version | Integer | 저장된 가이드북 버전 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `DATABASE_SAVE_FAILED` | DB 저장 | 문서 저장 중 오류 |

---

## DOCS-GUARD API 명세서

> 관련 기능 ID: `DOCS-GUARD-B-201`

---

### DOCS-GUARD-API-001 민감정보 마스킹 검증

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/gen/docs/{repo_id}/guard` |
| Method | POST |
| 관련 기능 ID | `DOCS-GUARD-B-201` |
| 목적 | 가이드북 생성 전 API 키, 토큰, 비밀번호 패턴 탐지 및 마스킹 적용 |
| 상태 | 시작 전 |

> 이 API는 내부 파이프라인의 가이드북 생성 직전 단계에서 자동 호출됩니다.
> 민감정보가 탐지되면 원문을 제거하고 `[MASKED]` 처리 후 내부 알람을 발송합니다.

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 검증 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| content | String | Y | 민감정보 검사 대상 Markdown 원문 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.maskedContent | String | 민감정보가 마스킹 처리된 Markdown |
| data.detectedCount | Integer | 탐지된 민감정보 패턴 수 |
| data.detectedPatterns | Array<Object> | 탐지된 패턴 목록 |
| data.detectedPatterns[].type | String | 패턴 유형 (api_key, token, password 등) |
| data.detectedPatterns[].location | String | 탐지 위치 (파일 경로 또는 섹션) |

##### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "maskedContent": "## 환경 설정\nOPENAI_API_KEY=[MASKED]\n",
    "detectedCount": 1,
    "detectedPatterns": [
      { "type": "api_key", "location": "backend/app/core/config.py" }
    ]
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_CONTENT` | 입력 검증 | 검사 대상 content가 비어있음 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `GUARD_FAILED` | 패턴 탐지 | 민감정보 탐지 처리 중 오류 |

---

## 에러 코드 정의

| Error Code | HTTP Status | 설명 |
| :--- | :--- | :--- |
| `DOCS_NOT_FOUND` | 404 | 가이드북이 아직 생성되지 않음 |
| `DOCS_ALREADY_EXISTS` | 409 | 가이드북이 이미 존재함 (force=false) |
| `DOCS_GENERATION_IN_PROGRESS` | 409 | 가이드북 생성이 이미 진행 중 |
| `ANALYSIS_NOT_COMPLETED` | 422 | RAG 파이프라인이 완료되지 않음 |
| `DOCS_GENERATION_FAILED` | 500 | 가이드북 생성 중 LLM 오류 |
| `FILE_GENERATION_FAILED` | 500 | Markdown/PDF 파일 생성 실패 |
| `DATABASE_SAVE_FAILED` | 500 | 문서 DB 저장 실패 |
| `GUARD_FAILED` | 500 | 민감정보 탐지 처리 실패 |
| `INVALID_CONTENT` | 400 | 검사 대상 content가 비어있음 |
