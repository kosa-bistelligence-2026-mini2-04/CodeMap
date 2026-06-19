# CodeMap HTTP API 명세

이 디렉토리는 CodeMap의 **API 계약 + 실행 가능한 요청 예시**를 관리한다. VS Code REST Client 또는 JetBrains HTTP Client에서 `.http` 요청을 바로 실행할 수 있다.

## 문서 계층

| 계층 | 위치 | 역할 |
| --- | --- | --- |
| 실행 명세 | `backend/tests/http/{DOMAIN}/*.http` | API별 요청, 성공 응답, 오류 계약, 제약 조건 |
| 변환 명세 | `docs/03_API/*.md` | 도메인 단위 읽기용 통합 명세 초안 |

## 계약 상태 표기

- `source-confirmed`: Notion의 기존 API 명세에 endpoint와 필드가 명시됨.
- `기능 명세 기반 설계 계약`: 기능 명세를 API로 구체화한 초안. 구현 전 백엔드·프론트엔드 합의 필요.
- `보류 기능의 설계 계약`: Phase 2 또는 범위 외 기능. 문서가 존재해도 구현됐다는 뜻이 아님.
- `구현 확인`: 실제 FastAPI 라우터와 일치 여부를 현재 코드로 검증함.

상태가 다른 정보를 섞어 확정 사실처럼 쓰지 않는다. 원문에 허용값·정책·산식이 없으면 `TODO_CONFIRM_*` 또는 “구현 전 확정”으로 남긴다.

## 디렉토리

| 도메인 | 주요 범위 |
| --- | --- |
| `PROJECT-LIST` | 분석 이력 목록, URL 검증, 목록 진행 상태 |
| `PROJECT-REPO` | 저장소 등록·검증·clone·상태·SSE/WS·workspace 정리 |
| `PROJECT-PIPELINE` | shallow/deep 단계 상태, 깊은 분석, 진행률, 외부 연동 |
| `RAG-PARSE` | README·트리·스택·AST·요약·위험도·스택 점수 |
| `RAG-EMBED` | 임베딩 생성 및 상태 |
| `RAG-GRAPH` | 의존성 그래프 생성 및 조회 |
| `AGENT-CHAT` | 저장소 Q&A, 대화 이력, 장기 기억 |
| `AGENT-SEARCH` | vector/grep/file 탐색 도구 |
| `AGENT-CORE` | 세션 상태와 정리 |
| `DOCS-GEN` | 가이드 조회·생성·재생성·다운로드·저장 |
| `DOCS-GUARD` | 민감정보 탐지·마스킹 |
| `DOCS-UTIL` | PDF 내보내기와 외부 공유(보류 기능) |

## 실행 환경

각 파일은 안전한 placeholder를 자체 선언한다.

```http
@baseUrl = http://localhost:8000
@accessToken = replace-me
@repoId = 3f7cc46e-d954-83ab-9f12-013b0c9d2a1e
```

실제 토큰이나 사설 URL은 Git에 기록하지 않는다. 로컬 REST Client 환경 변수로 덮어쓴다.

## 작성 규칙

1. API 하나당 실행 `.http` 파일 하나를 사용한다.
2. 상단에 API ID, endpoint, 관련 기능 ID, 계약 상태, 선행 조건을 적는다.
3. 정상 요청과 대표 오류 요청을 `###` 구분자로 분리한다.
4. 성공 응답에는 필드 타입·enum·nullable 여부를 설명한다.
5. 오류에는 HTTP status, error code, 발생 시점, 재시도 가능 여부를 적는다.
6. SSE/WS는 이벤트 타입, 종료 조건, 재연결/close code 계약을 적는다.
7. 응답 예시는 반드시 주석 처리해 요청 body로 전송되지 않게 한다.
8. 원문 근거가 없으면 추측으로 채우지 않고 미확정임을 표시한다.

## 공통 응답 계약

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

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

기존 PROJECT API 일부는 과거 명세의 평면형 `error` 문자열을 포함한다. 구현 전 공통 오류 envelope로 통일할지 명시적으로 결정해야 한다.

현재 표준은 `docs/04_Decisions/ERROR_HANDLING.md`와
`docs/03_API/ERROR_CODES.md`의 `code/message/data/error` envelope이다. 과거
평면형 예시는 호환성 확인 자료이며 신규 구현 계약으로 사용하지 않는다.
