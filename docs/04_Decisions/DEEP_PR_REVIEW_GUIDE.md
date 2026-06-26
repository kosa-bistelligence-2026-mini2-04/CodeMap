# CodeMap 심층 PR 리뷰 가이드

## 목적

이 문서는 GitHub Actions가 이미 확인하는 컴파일, lint, build 성공 여부를
반복 확인하기 위한 문서가 아니다. CodeMap PR 리뷰의 핵심 목적은 변경 코드가
프로젝트 명세, API 계약, 도메인 구조, 병합 순서, 보안/데이터 흐름과 충돌하지
않는지 검증한 뒤 `Approve`, `Request changes`, `Comment`를 일관되게
판단하는 것이다.

현재 CI는 최소 품질 게이트다. 특히 `.github/workflows/ci.yml` 기준으로
백엔드 `pytest`는 차단 게이트지만 `pyright`는 report-only이고, 프론트엔드
`eslint`와 `next build`도 report-only로 운용된다. 따라서 CI 성공은
리뷰 시작 조건이지 승인 근거 자체가 아니다.

## 리뷰 원칙

### 1. 전체 코드 건강 기준

Google Engineering Practices의 코드 리뷰 기준처럼, PR은 전체 코드베이스의
건강을 유지하거나 개선할 때 승인한다. 기능이 "동작할 가능성"만으로 승인하지
않고, 설계, 기능, 복잡도, 테스트, 문서, 명명, 주석, 스타일, 전체 맥락을 함께
검토한다.

CodeMap에서는 이 원칙을 다음 질문으로 바꾼다.

- 이 PR이 `docs/03_Specifications/**` 또는 `docs/04_Decisions/**`의 계약을
  구현하거나 보존하는가?
- PR 설명의 기능 ID, API ID, Issue 번호가 실제 변경 파일과 연결되는가?
- 기존 도메인 구조인 `router -> service -> repository -> schemas/models`를
  깨지 않는가?
- 프론트엔드 타입, 백엔드 Pydantic schema, DB 저장 계약, API 응답 예시가
  서로 같은 이름과 의미를 사용하는가?
- 새 코드가 다음 PR의 병합을 막는 공유 파일 충돌을 만들지 않는가?

### 2. CI와 사람 리뷰의 역할 분리

CI가 확인하는 항목:

- 백엔드 단위 테스트가 기본적으로 깨지지 않는지
- 프론트엔드 의존성 설치, lint, build가 실행 가능한지
- 기본 타입/정적 검사에서 즉시 드러나는 오류가 있는지

사람 또는 심층 AI 리뷰가 확인해야 하는 항목:

- 명세 문서와 실제 구현의 필드명, 엔드포인트, 상태값, 에러 코드가 일치하는지
- API 응답 contract가 프론트 타입과 백엔드 schema 사이에서 깨지지 않는지
- 기존 fallback/legacy 호환 정책을 실수로 제거하지 않았는지
- 여러 열린 PR이 같은 파일, 같은 계약, 같은 DB/API 필드를 서로 다르게
  수정하고 있지 않은지
- 보안 경계, 경로 검증, 인증/토큰 저장, 외부 URL 처리, SSE 이벤트 처리 같은
  전역 위험이 생기지 않았는지
- PR이 너무 넓어서 리뷰 가능한 단위나 명세 단위를 넘어섰는지

## 필수 리뷰 입력

리뷰어는 판단 전에 다음 자료를 먼저 확보한다.

1. PR 메타데이터
   - PR 번호, 제목, base/head 브랜치
   - 연결 Issue, 기능 ID, API ID
   - draft 여부, mergeable 상태, reviewDecision
   - CI 결과와 report-only 항목의 실제 로그 요약

2. 변경 범위
   - `git diff --name-status origin/main...HEAD`
   - `git diff --stat origin/main...HEAD`
   - 삭제/이동/rename 파일 목록
   - lockfile, migration, schema, 공통 타입, 공통 UI 컴포넌트 변경 여부

3. 명세 원본
   - `docs/01_Overview/FUNCTIONAL_SPECIFICATION.md`
   - `docs/03_Specifications/**/spec/*.md`
   - `docs/03_Specifications/**/api/*.md`
   - `docs/03_Specifications/ERROR_CODES.md`
   - 관련 결정 문서: `docs/04_Decisions/*.md`

4. 충돌 가능성
   - 현재 열린 PR 목록
   - 같은 파일을 건드리는 PR
   - 같은 기능 ID/API ID/Issue 범위를 구현하는 PR
   - `main`이 PR 생성 후 변경되어 stale approval 또는 merge-base 변경이
     발생했는지

## CodeMap 계약 매트릭스

PR을 볼 때 변경 성격별로 아래 계약 파일을 우선 연결한다.

| 변경 영역 | 우선 확인 문서 | 코드 확인 지점 |
|---|---|---|
| 프로젝트 등록/목록/팀/API | `docs/03_Specifications/01_Project/**` | `backend/app/repo`, `backend/app/list`, `backend/app/project`, `frontend/src/features/*` |
| RAG parse/embed/graph | `docs/03_Specifications/02_RAG/**`, `RAG_PARSE_REPORT_CONTRACT.md`, `EMBEDDING_MODEL_DECISION.md` | `backend/app/parse`, `backend/app/rag`, `database`, `frontend/src/common/types/contracts.ts` |
| LLM chat/run/agent/tool | `docs/03_Specifications/03_LLM/**`, `MULTI_AGENT_ARCHITECTURE_DECISION.md` | `backend/app/chat`, `backend/app/agent`, `backend/app/tool`, `frontend/src/features/chat` |
| 문서 생성/내보내기 | `docs/03_Specifications/04_Docs/**` | `backend/app/gen`, `frontend/src/features/docs` |
| 에러/인증/보안 | `ERROR_CODES.md`, `ERROR_HANDLING.md`, `PROJECT_AUTH_SPEC.md` | `backend/app/auth`, `backend/app/common`, API client, token storage |
| 공통 UI/타입 | 기능별 spec와 `contracts.ts` | `frontend/src/common`, `frontend/src/features` |

## 심층 리뷰 절차

### 1. PR 의도와 명세 범위를 먼저 고정한다

PR 제목과 본문에서 기능 ID/API ID/Issue 번호를 뽑는다. 예를 들어
`LLM-CHAT-F-207`, `RAG-PARSE-B-210`, `DOCS-GEN-API-005`처럼 추적 가능한
ID가 있으면 해당 문서를 먼저 읽는다.

Change request 조건:

- PR 설명에 명세/Issue 연결이 없고 변경 범위가 기능성 코드인 경우
- PR 제목은 한 기능처럼 보이지만 실제 diff가 여러 명세 단위를 동시에 바꾸는 경우
- 문서에는 "시작 전", "Phase 2 예정"으로 되어 있는데 구현은 완료처럼 보이거나
  그 반대인 경우

### 2. API 계약을 양방향으로 검증한다

백엔드에서 시작하지도, 프론트에서 시작하지도 말고 문서 계약을 기준으로 양쪽을
대조한다.

확인 순서:

1. 명세의 endpoint, method, path parameter, request body, response body,
   error code를 적는다.
2. 백엔드 `router.py`, `schemas.py`, `service.py`, `repository.py`가 같은
   계약을 구현하는지 확인한다.
3. 프론트 API client, hook, component, `contracts.ts`가 같은 이름과 타입을
   쓰는지 확인한다.
4. snake_case/camelCase 변환 지점이 명시되어 있는지 확인한다.
5. legacy fallback이 필요한 계약이면 fallback이 제거되지 않았는지 확인한다.

Change request 조건:

- 문서의 필수 필드가 응답에서 빠져 있다.
- 백엔드 schema와 프론트 타입이 다른 상태값 집합을 사용한다.
- error code가 문서와 다르거나 공통 에러 처리 경로를 우회한다.
- DB 저장 계약은 snake_case인데 프론트 camelCase를 그대로 저장한다.
- 기존 분석 결과와의 호환 fallback을 제거한다.

### 3. 전역 구조와 의존성 방향을 확인한다

CodeMap 백엔드는 도메인 단위 `router -> service -> repository` 흐름을
기본으로 한다. 프론트엔드는 `src/common`과 `src/features`의 역할 분리를
보존해야 한다.

확인할 위험:

- `router.py`에 비즈니스 로직이 과도하게 들어간다.
- repository가 HTTP 요청, LLM 호출, 파일 시스템 스캔 같은 외부 작업을 직접 한다.
- service가 Pydantic/SQLAlchemy 모델을 불필요하게 섞어 반환한다.
- `common`에 특정 feature 전용 로직이 들어간다.
- feature 컴포넌트가 API 응답 원형을 화면에서 매번 임시 변환한다.
- 새로운 compatibility wrapper가 생겼지만 제거 기준이나 소유 모듈이 없다.

Approve 조건:

- 기존 계층 경계를 지키며 변경 범위가 명세 단위와 맞다.
- 공통 모듈 변경은 최소이고, 호출부가 실제로 공유 이득을 얻는다.
- 파일 이동/rename은 import 경로, 테스트, 문서, PR 설명까지 함께 정리되어 있다.

### 4. 열린 PR 간 충돌 가능성을 본다

GitHub의 mergeable 상태가 `MERGEABLE`이어도 의미 충돌은 남을 수 있다. 특히
같은 공통 타입, API schema, DB migration, lockfile, 라우터 등록, SSE 이벤트
이름을 만지는 PR들은 순서가 바뀌면 한쪽이 다른 쪽 계약을 덮어쓸 수 있다.

필수 확인:

- 현재 열린 PR의 변경 파일 목록과 겹치는가?
- 같은 기능 ID나 Issue 그룹을 다른 PR도 구현하는가?
- 같은 docs 계약을 서로 다르게 갱신하는가?
- `origin/main`이 PR 승인 이후 이동해서 stale approval이 되었는가?
- `.github/ruleset-main.json`의 리뷰 정책상 재승인이 필요한가?

Change request 조건:

- 같은 API response field를 두 PR이 다른 이름으로 추가한다.
- 한 PR은 legacy 호환을 유지하고 다른 PR은 제거한다.
- migration 순서가 불명확하거나 같은 테이블/컬럼을 동시에 수정한다.
- lockfile 변경이 PR 목적과 무관하거나 다른 PR 의존성을 우연히 포함한다.
- PR이 최신 `main` 기준으로는 통과하지만 이미 열린 상위/선행 PR과 의미 충돌한다.

### 5. 데이터 흐름과 실패 흐름을 검증한다

정상 흐름만 보면 approve가 쉬워진다. CodeMap에서는 실패 상태, 취소, fallback,
권한 없음, 빈 결과, line unknown, DB 없음, LLM key 없음 같은 경계 상태가 실제
제품 품질을 좌우한다.

확인 질문:

- 실패 응답이 `ERROR_CODES.md`와 맞는가?
- 사용자에게 보여지는 빈 상태와 오류 상태가 구분되는가?
- SSE/run lifecycle 변경이면 `created -> streaming -> completed/failed/cancelled`
  흐름이 끊기지 않는가?
- RAG/parse 변경이면 바이너리 파일, 빈 파일, 큰 파일, 제외 경로가 안전한가?
- 인증 변경이면 access token, refresh token, cookie, localStorage 정책이
  기존 결정과 충돌하지 않는가?

Change request 조건:

- 정상 케이스만 구현하고 실패/취소/빈 결과 처리가 빠져 있다.
- 보안 검증이 UI나 클라이언트에만 있다.
- path traversal, 외부 URL, 파일 확장자 allowlist 검증이 약해진다.
- 테스트가 happy path만 있고 contract regression을 못 잡는다.

### 6. 테스트는 "있는가"보다 "무엇을 증명하는가"를 본다

CI 통과 여부와 별개로, 새 테스트가 PR의 위험을 실제로 고정하는지 확인한다.

좋은 테스트:

- 문서 contract의 필수 필드/상태값/에러 코드를 검증한다.
- legacy fallback과 신규 canonical 계약을 함께 검증한다.
- 실패/빈 결과/권한 없음/취소처럼 깨지기 쉬운 경계를 포함한다.
- 프론트 타입 helper나 formatter는 브라우저 없이도 순수 테스트로 검증한다.

부족한 테스트:

- 변경된 계약과 무관한 snapshot만 추가한다.
- API 응답의 존재만 보고 필드 의미를 검증하지 않는다.
- 실패 흐름 없이 정상 흐름만 확인한다.
- report-only CI가 놓칠 타입 불일치를 contract 테스트로 보완하지 않는다.

## 판정 기준

### Approve

다음 조건이 모두 만족될 때 승인한다.

- PR 목적, Issue, 기능 ID, API ID가 실제 diff와 일치한다.
- 관련 명세 문서와 코드 계약이 같은 용어, 필드, 상태값, 에러 코드를 쓴다.
- 기존 public API, DB 저장 계약, 프론트 타입, run/SSE 이벤트가 깨지지 않는다.
- 열린 PR과의 파일/계약/마이그레이션 충돌 위험이 없거나 병합 순서가 명확하다.
- 실패/빈 상태/권한/취소/fallback 등 경계 상태가 코드나 테스트로 다뤄진다.
- 변경 범위가 PR 템플릿의 "단일 명세 원칙"을 넘지 않는다.

### Request changes

다음 중 하나라도 있으면 변경 요청을 남긴다.

- 명세와 구현 계약이 다르다.
- 프론트 타입과 백엔드 schema가 다르다.
- 기존 호환/fallback/보안 검증을 설명 없이 제거한다.
- 공유 파일 변경이 다른 열린 PR과 충돌할 가능성이 크다.
- PR 범위가 너무 넓어서 리뷰 가능한 단위가 아니다.
- 보안, 인증, path handling, external URL, token storage, migration 순서에
  명확한 위험이 있다.
- CI가 성공했더라도 report-only 항목에 실제 회귀가 보인다.

### Comment

다음 경우에는 blocking하지 않고 comment로 남긴다.

- 명세와 구현은 맞지만 네이밍 또는 설명이 더 명확해질 수 있다.
- 후속 PR에서 처리해도 되는 작은 리팩터링이다.
- 테스트 보강이 있으면 좋지만 현재 변경의 핵심 계약은 이미 보호된다.
- UI 문구, 스타일, 파일 위치에 취향성 의견이 있다.

## 리뷰 코멘트 작성 형식

### Approve 예시

```markdown
Approve합니다.

- 관련 명세: `docs/03_Specifications/...`
- 확인한 계약: endpoint/request/response/error code가 백엔드 schema와 프론트 타입까지 일치합니다.
- 충돌 확인: 현재 열린 PR 중 같은 contract 또는 migration을 수정하는 PR이 없어 병합 순서 리스크가 낮습니다.
- 남은 비차단 의견: ...
```

### Request changes 예시

```markdown
Request changes입니다.

Blocking 사유:
- `docs/03_Specifications/...`의 `data.status`는 `queued | running | completed | failed`인데,
  구현은 `pending | in_progress | done`을 반환합니다.
- 프론트 `contracts.ts`도 구현 값에 맞춰져 있어 문서/API/프론트 계약이 동시에 갈라졌습니다.

수정 방향:
- 명세를 바꿀 의도라면 관련 spec/api 문서를 함께 업데이트하고 기존 호출부 호환 정책을 적어주세요.
- 구현을 명세에 맞출 의도라면 백엔드 schema, service 반환값, 프론트 타입을 명세 값으로 통일해 주세요.
```

### Comment 예시

```markdown
비차단 의견입니다.

현재 계약은 맞지만 `normalizeRunStatus()` 같은 변환 helper가 있으면 같은 status 매핑이
컴포넌트마다 반복되지 않을 것 같습니다. 이번 PR 범위 밖이면 후속 이슈로 남겨도 됩니다.
```

## 심층 리뷰용 AI 프롬프트

다음 프롬프트는 GPT 계열, Claude, Gemini 등 모델에 공통으로 줄 수 있는
리뷰 지시문이다. 핵심은 "approve 먼저"가 아니라 "blocking evidence 먼저"이다.

```text
너는 CodeMap 저장소의 PR reviewer다.
CI 통과 여부를 승인 근거로 삼지 말고, docs 명세와 실제 코드 계약의 일치 여부를 중심으로 검토한다.

반드시 다음 순서로 답하라.
1. PR 범위: 제목, Issue, 기능 ID/API ID, 변경 파일을 기준으로 이 PR이 어떤 계약을 바꾸는지 요약
2. 관련 명세: 읽어야 할 docs 파일과 해당 계약 항목
3. Blocking findings: approve를 막는 문제만, 파일/라인/명세 근거와 함께 작성
4. Non-blocking comments: 취향/리팩터링/후속 보강 의견
5. Conflict risk: 열린 PR 또는 main 변경과 충돌할 수 있는 파일/계약/migration 여부
6. Verdict: APPROVE, REQUEST_CHANGES, COMMENT 중 하나

규칙:
- 빌드/컴파일 실패는 CI가 담당하므로 주요 판단 근거로 반복하지 않는다.
- 명세와 구현이 다르면 REQUEST_CHANGES를 기본값으로 한다.
- 근거 없는 "looks good" 또는 "문제 없어 보임"으로 승인하지 않는다.
- 코드 diff만 보지 말고 docs/03_Specifications와 docs/04_Decisions를 함께 대조한다.
- report-only CI 항목은 성공 표시가 있어도 실제 로그에 회귀가 있으면 언급한다.
```

## 빠른 체크리스트

- [ ] PR이 단일 명세/기능 단위인가?
- [ ] PR 설명의 Issue/기능 ID/API ID가 실제 diff와 연결되는가?
- [ ] 관련 spec/api/decision 문서를 읽었는가?
- [ ] 백엔드 schema와 프론트 타입이 같은 필드/상태값을 쓰는가?
- [ ] legacy fallback 또는 migration 순서가 보존되는가?
- [ ] 실패/빈 상태/취소/권한 없음/보안 경계가 다뤄지는가?
- [ ] 같은 파일/계약을 수정하는 열린 PR이 있는가?
- [ ] report-only CI 항목에 숨은 회귀가 없는가?
- [ ] approve/comment/request changes 중 하나를 근거와 함께 명확히 썼는가?

## 참고한 외부 기준

- Google Engineering Practices, "The Standard of Code Review":
  https://google.github.io/eng-practices/review/reviewer/standard.html
- Google Engineering Practices, "What to look for in a code review":
  https://google.github.io/eng-practices/review/reviewer/looking-for.html
- GitHub Docs, "Reviewing proposed changes in a pull request":
  https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/reviewing-proposed-changes-in-a-pull-request
- GitHub Docs, "About pull request reviews":
  https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews
- GitHub Docs, "About protected branches":
  https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
