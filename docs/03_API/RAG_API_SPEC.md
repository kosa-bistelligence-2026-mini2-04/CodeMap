# RAG API 명세서

본 문서는 CodeMap 백엔드의 **RAG(Retrieval-Augmented Generation)** 도메인 API에 대한 상세 명세서입니다.
RAG 도메인은 `PARSE`(코드 파싱 및 분석)와 `EMBED`(벡터 임베딩) 두 모듈로 구성됩니다.

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

## RAG-PARSE API 명세서

> 관련 기능 ID: `RAG-PARSE-B-101` ~ `RAG-PARSE-B-210`, `RAG-PARSE-F-201`

---

### RAG-PARSE-API-001 분석 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-101` |
| 목적 | 특정 저장소의 코드 파싱 및 구조 분석 결과 전체 조회 |
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
| repo_id | UUID | Y | 분석 대상 저장소 고유 ID |

##### 요청 예시

```http
GET /api/parse/analysis/3f7cc46e-d954-83ab-9f12-013b0c9d2a1e HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGci...
Accept: application/json
```

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.repoName | String | 저장소 이름 |
| data.techStack | Array<String> | 탐지된 기술 스택 목록 |
| data.entryPoints | Array<String> | 탐지된 진입점 파일 경로 목록 |
| data.directoryTree | String | 프로젝트 폴더 트리 구조 (텍스트) |
| data.runCommands | Object | 설치 및 실행 명령어 |
| data.runCommands.install | String | 의존성 설치 명령어 |
| data.runCommands.run | String | 프로젝트 실행 명령어 |
| data.configFiles | Array<String> | 탐지된 설정 파일 경로 목록 |
| data.readmeSummary | String | README 기반 프로젝트 요약 |
| data.fileCount | Integer | 분석 대상 파일 총 수 |
| data.analyzedAt | String | 분석 완료 시각 (ISO 8601) |

##### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "repoId": "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
    "repoName": "CodeMap",
    "techStack": ["Python 3.12", "FastAPI", "Next.js 16", "PostgreSQL", "pgvector"],
    "entryPoints": ["backend/app/main.py", "frontend/src/app/page.tsx"],
    "directoryTree": "CodeMap/\n├── frontend/\n├── backend/\n└── database/",
    "runCommands": {
      "install": "pip install -r requirements.txt",
      "run": "uvicorn app.main:app --reload"
    },
    "configFiles": ["backend/requirements.txt", "frontend/package.json"],
    "readmeSummary": "GitHub 레포 URL을 입력하면 신입 개발자용 온보딩 문서를 자동 생성하는 RAG 기반 AI 웹앱",
    "fileCount": 87,
    "analyzedAt": "2026-06-18T10:00:00Z"
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰이 누락되었거나 만료됨 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 해당 repo_id가 존재하지 않음 |
| 404 | `PARSE_RESULT_NOT_FOUND` | DB 조회 | 분석 결과가 아직 생성되지 않음 |
| 500 | `DATABASE_ERROR` | DB 조회 | 데이터베이스 조회 중 예외 발생 |

---

### RAG-PARSE-API-002 README 분석 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}/readme` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-201` |
| 목적 | README 파싱 기반 프로젝트 목적 및 핵심 기능 요약 반환 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Headers

| 헤더명 | 값 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| Authorization | Bearer {access_token} | Y | 인증 토큰 |

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 분석 대상 저장소 고유 ID |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.projectPurpose | String | 프로젝트 목적 요약 |
| data.coreFeatures | Array<String> | 핵심 기능 목록 |
| data.targetAudience | String | 주요 사용자 대상 |
| data.rawReadme | String | README 원문 (Markdown) |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 404 | `README_NOT_FOUND` | 파일 탐색 | README 파일이 존재하지 않음 |
| 500 | `PARSE_FAILED` | LLM 처리 | README 분석 중 오류 발생 |

---

### RAG-PARSE-API-003 디렉토리 구조 분석 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}/tree` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-202` |
| 목적 | 프로젝트 폴더 트리 구조 및 진입점 탐지 결과 반환 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Headers

| 헤더명 | 값 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| Authorization | Bearer {access_token} | Y | 인증 토큰 |

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 분석 대상 저장소 고유 ID |

##### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| depth | Integer | N | 3 | 트리 탐색 최대 깊이 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.directoryTree | String | 폴더 트리 텍스트 (tree 명령 형식) |
| data.entryPoints | Array<Object> | 탐지된 진입점 파일 목록 |
| data.entryPoints[].path | String | 파일 경로 |
| data.entryPoints[].type | String | 진입점 유형 (backend, frontend, config 등) |
| data.configFiles | Array<String> | 설정 파일 경로 목록 |
| data.totalFiles | Integer | 전체 분석 대상 파일 수 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `TREE_PARSE_FAILED` | 파일 탐색 | 디렉토리 트리 생성 중 오류 |

---

### RAG-PARSE-API-004 기술 스택 탐지 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}/stack` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-206` |
| 목적 | package.json, requirements.txt, Dockerfile 기반 기술 스택 자동 탐지 결과 반환 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 분석 대상 저장소 고유 ID |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.techStack | Array<Object> | 탐지된 기술 스택 목록 |
| data.techStack[].name | String | 기술명 |
| data.techStack[].version | String | 버전 (탐지된 경우) |
| data.techStack[].category | String | 분류 (language, framework, database, infra 등) |
| data.techStack[].source | String | 탐지 출처 파일 경로 |
| data.runCommands.install | String | 의존성 설치 명령어 |
| data.runCommands.run | String | 실행 명령어 |
| data.runCommands.build | String | 빌드 명령어 (없으면 null) |

##### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "repoId": "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
    "techStack": [
      { "name": "Python", "version": "3.12", "category": "language", "source": "backend/requirements.txt" },
      { "name": "FastAPI", "version": "0.115.0", "category": "framework", "source": "backend/requirements.txt" },
      { "name": "Next.js", "version": "16.0.0", "category": "framework", "source": "frontend/package.json" },
      { "name": "PostgreSQL", "version": "16", "category": "database", "source": "scripts/docker-compose.yml" },
      { "name": "pgvector", "version": "0.8.0", "category": "extension", "source": "scripts/docker-compose.yml" }
    ],
    "runCommands": {
      "install": "pip install -r requirements.txt",
      "run": "uvicorn app.main:app --reload --port 8000",
      "build": null
    }
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `STACK_DETECTION_FAILED` | 파일 파싱 | 기술 스택 탐지 중 오류 |

---

### RAG-PARSE-API-005 코드 맵(AST 청킹 + import 관계) 분석 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}/codemap` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-207`, `RAG-PARSE-B-208`, `RAG-PARSE-B-210` |
| 목적 | AST 기반 코드 청킹, 파일 간 import 관계 분석, 구조 분석 agent 결과 반환 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 분석 대상 저장소 고유 ID |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.fileMap | Array<Object> | 파일 단위 코드 맵 |
| data.fileMap[].path | String | 파일 경로 |
| data.fileMap[].language | String | 프로그래밍 언어 |
| data.fileMap[].chunkCount | Integer | AST 청크 수 |
| data.fileMap[].imports | Array<String> | 이 파일이 참조하는 파일 경로 목록 |
| data.fileMap[].importedBy | Array<String> | 이 파일을 참조하는 파일 경로 목록 (Fan-in) |
| data.fileMap[].riskScore | Integer | 위험도 점수 (0-100) |
| data.heatmap | Array<Object> | 복잡도 히트맵 데이터 |
| data.heatmap[].path | String | 파일 경로 |
| data.heatmap[].score | Integer | 복잡도 점수 (0-100) |

##### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "repoId": "3f7cc46e-d954-83ab-9f12-013b0c9d2a1e",
    "fileMap": [
      {
        "path": "backend/app/repo/service.py",
        "language": "python",
        "chunkCount": 12,
        "imports": ["backend/app/repo/repository.py", "backend/app/repo/schemas.py"],
        "importedBy": ["backend/app/main.py"],
        "riskScore": 30
      }
    ],
    "heatmap": [
      { "path": "backend/app/repo/service.py", "score": 72 },
      { "path": "backend/app/parse/service.py", "score": 85 }
    ]
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 404 | `CODEMAP_NOT_FOUND` | DB 조회 | 코드 맵 분석 결과가 아직 없음 |
| 500 | `AST_PARSE_FAILED` | AST 처리 | AST 청킹 또는 의존성 분석 중 오류 |

---

### RAG-PARSE-API-006 Bottom-up 계층 요약 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}/summary` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-209` |
| 목적 | 파일→폴더→프로젝트 순서의 Bottom-up 계층 요약 결과 반환 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 분석 대상 저장소 고유 ID |

##### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| level | String | N | all | 요약 수준 (file / folder / project / all) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.projectSummary | String | 프로젝트 전체 마스터 요약 |
| data.folderSummaries | Array<Object> | 폴더 단위 요약 목록 |
| data.folderSummaries[].path | String | 폴더 경로 |
| data.folderSummaries[].summary | String | 폴더 역할 요약 |
| data.fileSummaries | Array<Object> | 파일 단위 요약 목록 |
| data.fileSummaries[].path | String | 파일 경로 |
| data.fileSummaries[].summary | String | 파일 역할 요약 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `SUMMARY_FAILED` | LLM 처리 | Bottom-up 요약 생성 중 오류 |

---

## RAG-EMBED API 명세서

> 관련 기능 ID: `RAG-EMBED-B-201`, `RAG-EMBED-B-301`

---

### RAG-EMBED-API-001 임베딩 생성 요청

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/embed/analysis/{repo_id}` |
| Method | POST |
| 관련 기능 ID | `RAG-EMBED-B-201` |
| 목적 | 파싱된 코드 및 문서를 `text-embedding-3-large` 모델로 벡터화하여 pgvector에 저장 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Headers

| 헤더명 | 값 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| Authorization | Bearer {access_token} | Y | 인증 토큰 |
| Content-Type | application/json | Y | 요청 본문 형식 |

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 임베딩 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| model | String | N | text-embedding-3-large | 사용할 임베딩 모델 |
| dimensions | Integer | N | 3072 | 임베딩 벡터 차원 (마트료시카 지원) |
| forceReembed | Boolean | N | false | 기존 임베딩 삭제 후 재생성 여부 |

##### 요청 예시

```json
{
  "model": "text-embedding-3-large",
  "dimensions": 3072,
  "forceReembed": false
}
```

#### 응답(Response)

##### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (202) |
| message | String | "accepted" |
| data.jobId | UUID | 분석 작업 ID |
| data.repoId | UUID | 저장소 ID |
| data.status | String | embedding_queued |
| data.estimatedFiles | Integer | 임베딩 대상 파일 수 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 409 | `EMBEDDING_IN_PROGRESS` | 작업 중복 검사 | 이미 임베딩이 진행 중인 저장소 |
| 422 | `PARSE_NOT_COMPLETED` | 사전 검증 | 코드 파싱이 완료되지 않은 상태에서 임베딩 요청 |
| 500 | `EMBEDDING_FAILED` | 임베딩 처리 | OpenAI API 호출 또는 벡터 저장 중 오류 |

---

### RAG-EMBED-API-002 임베딩 저장 상태 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/embed/analysis/{repo_id}/status` |
| Method | GET |
| 관련 기능 ID | `RAG-EMBED-B-301` |
| 목적 | pgvector에 저장된 임베딩 현황 및 벡터 DB 저장 상태 조회 |
| 상태 | 시작 전 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 조회할 저장소 고유 ID |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.status | String | not_started / in_progress / completed / failed |
| data.totalChunks | Integer | 전체 생성된 청크 수 |
| data.embeddedChunks | Integer | pgvector에 저장 완료된 청크 수 |
| data.model | String | 사용된 임베딩 모델 |
| data.dimensions | Integer | 벡터 차원 수 |
| data.completedAt | String | 임베딩 완료 시각 (완료된 경우) |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `DATABASE_ERROR` | DB 조회 | 벡터 DB 조회 중 오류 |

---

## 에러 코드 정의

| Error Code | HTTP Status | 설명 |
| :--- | :--- | :--- |
| `README_NOT_FOUND` | 404 | README 파일이 저장소에 존재하지 않음 |
| `PARSE_RESULT_NOT_FOUND` | 404 | 파싱 결과가 아직 생성되지 않음 |
| `CODEMAP_NOT_FOUND` | 404 | 코드 맵 분석 결과가 없음 |
| `TREE_PARSE_FAILED` | 500 | 디렉토리 트리 생성 실패 |
| `STACK_DETECTION_FAILED` | 500 | 기술 스택 탐지 실패 |
| `AST_PARSE_FAILED` | 500 | AST 기반 코드 청킹 실패 |
| `SUMMARY_FAILED` | 500 | Bottom-up 요약 생성 실패 |
| `PARSE_NOT_COMPLETED` | 422 | 임베딩 전 파싱이 완료되지 않음 |
| `EMBEDDING_IN_PROGRESS` | 409 | 임베딩이 이미 진행 중임 |
| `EMBEDDING_FAILED` | 500 | 임베딩 생성 또는 저장 실패 |
