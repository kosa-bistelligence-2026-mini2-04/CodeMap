# PROJECT ANALYZE 화면 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-ANALYZE | **최종 업데이트**: 2026-06-26

## 배경

`/analyze`는 분석 리포트, Repository 파일 트리, 코드 프리뷰, AI chat, 검색/분석 기록을 한 화면에서 연결하는 작업 공간입니다. Issue #160, #161, #162, #163은 같은 화면의 정보 연결성이 끊기는 문제이므로 별도 화면 명세로 묶어 관리합니다. Issue #178, #179는 화면 상태와 피드백 패턴이 사용자에게 잘못 전달되는 문제를 보강합니다.

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | 관련 이슈 | 작업 상태 |
| --- | --- | --- | --- | --- |
| PROJECT-ANALYZE-F-101 | Repository 파일 클릭 시 코드 프리뷰 표시 | Frontend | Issue #160 | 제안 |
| PROJECT-ANALYZE-F-102 | 근거 파일 클릭 시 해당 라인 이동/하이라이트 | Frontend | Issue #161 | 제안 |
| PROJECT-ANALYZE-F-103 | Repository와 History 동시 접근 | Frontend | Issue #162 | 제안 |
| PROJECT-ANALYZE-F-104 | DashboardCharts 실제 report 데이터 연결 | Frontend | Issue #163 | 제안 |
| PROJECT-ANALYZE-F-105 | 리포트 표시와 RAG 인덱싱 상태 분리 | Frontend | Issue #178 | 제안 |
| PROJECT-ANALYZE-F-106 | 브라우저 기본 alert/confirm 대체 | Frontend | Issue #179 | 제안 |

---

## PROJECT-ANALYZE-F-101: Repository 파일 클릭 시 코드 프리뷰 표시

| 항목 | 내용 |
| --- | --- |
| 관련 파일 | `frontend/src/app/analyze/page.tsx`, `frontend/src/features/chat/components/FileTree.tsx` |
| 관련 API | `PROJECT-REPO-API-010` |

**설명**

Repository 패널의 파일을 클릭하면 선택 상태만 바꾸지 않고, 분석 job workspace 내부 파일 내용을 읽어 코드 프리뷰 패널에 표시합니다.

**구현 노트**

- `selectedFile` 변경 시 `GET /api/repo/analysis/{job_id}/files?path=...`를 호출합니다.
- 코드 프리뷰는 line number, copy, loading, error, empty, binary/large file 상태를 구분합니다.
- 파일 트리와 프리뷰는 같은 `job_id`를 기준으로 동작해야 하며, URL의 `job` 값이 바뀌면 선택 파일과 프리뷰 상태를 초기화합니다.

**완료 조건**

- Repository 파일 클릭 시 실제 파일 내용이 표시됩니다.
- 허용되지 않는 경로/바이너리/대용량 파일은 안전한 오류 상태로 표시됩니다.

---

## PROJECT-ANALYZE-F-102: 근거 파일 클릭 시 해당 라인 이동/하이라이트

| 항목 | 내용 |
| --- | --- |
| 관련 파일 | `frontend/src/app/analyze/page.tsx`, `frontend/src/app/chat/page.tsx`, `frontend/src/features/chat/components/ChatMessage.tsx` |
| 관련 이슈 | Issue #161 |

**설명**

채팅 답변의 근거 칩을 클릭하면 파일뿐 아니라 `lineStart`/`lineEnd`까지 전달해 코드 프리뷰에서 해당 줄로 스크롤하고 하이라이트합니다.

**구현 노트**

- `/analyze`는 `selectedFile`, `selectedLine`, `selectedLineEnd` 상태를 함께 관리합니다.
- `ChatMessage.onReferenceClick(reference.file, reference.lineStart, reference.lineEnd)`의 line 인자를 버리지 않습니다.
- line 정보가 없으면 `라인 미확인`으로 표시하고 `0` 또는 `1`로 오인되지 않게 합니다.
- 코드 프리뷰는 line number DOM에 안정적인 anchor를 두고, line highlight가 layout shift를 만들지 않게 합니다.

**완료 조건**

- 근거 칩 클릭 시 파일 프리뷰가 열리고 해당 줄이 보이는 위치로 이동합니다.
- full chat(`/chat`)과 analyze compact chat에서 같은 reference 계약을 사용합니다.

---

## PROJECT-ANALYZE-F-103: Repository와 History 동시 접근

| 항목 | 내용 |
| --- | --- |
| 관련 파일 | `frontend/src/app/analyze/page.tsx`, `frontend/src/features/history/components/HistoryList.tsx` |
| 관련 이슈 | Issue #162 |

**설명**

분석 완료 후 Repository 파일 트리가 보이는 상태에서도 검색/분석 기록을 확인할 수 있어야 합니다. Repository와 History는 상호 배타적인 화면이 아니라 좌측 aside 안의 탭 또는 접이식 섹션으로 공존합니다.

**구현 노트**

- 좌측 aside는 `Repository`, `History` 탭 또는 접이식 섹션을 제공합니다.
- History에서 다른 job을 선택하면 URL `job` 값, report, repository tree, chat thread 상태를 일관되게 갱신합니다.
- 모바일 sidebar에서도 History 접근을 유지합니다.
- Phase 2 팀 기능이 켜진 경우 History는 `PROJECT_LIST_SPEC.md`의 `scope=private|team|all` 계약을 사용합니다.

**완료 조건**

- 분석 완료 화면에서 Repository를 보면서 History도 열 수 있습니다.
- History 선택 시 현재 화면 상태와 URL이 어긋나지 않습니다.

---

## PROJECT-ANALYZE-F-104: DashboardCharts 실제 report 데이터 연결

| 항목 | 내용 |
| --- | --- |
| 관련 파일 | `frontend/src/features/analysis/components/DashboardCharts.tsx`, `frontend/src/features/analysis/components/WorkspaceReport.tsx`, `frontend/src/common/types/contracts.ts` |
| 관련 이슈 | Issue #163 |
| 관련 계약 | `RAG_PARSE_REPORT_CONTRACT.md` |

**설명**

실제 분석 job 화면에서 DashboardCharts는 mock 상수를 사용하지 않고 `WorkspaceReportData` 또는 `report_json`에서 파생한 데이터를 렌더링합니다.

**구현 노트**

- 우선 연결 대상: `language_composition`, file count, line count, test count, risk/heatmap score, entrypoint/readme/stack 기반 health dimensions.
- contributor/git history 데이터가 아직 분석 파이프라인에 없으면 mock 대신 명시적인 empty state를 보여줍니다.
- preview/demo 모드에서만 demo badge 또는 mock fixture 사용을 허용합니다.
- 실제 job 화면에서는 `(Mock)` 문구를 표시하지 않습니다.

**완료 조건**

- 실제 분석 job의 차트는 mock 상수가 아니라 분석 결과를 사용합니다.
- 데이터가 없는 차트는 빈 상태로 표시되고, preview 모드는 demo 데이터임을 명확히 표시합니다.

---

## PROJECT-ANALYZE-F-105: 리포트 표시와 RAG 인덱싱 상태 분리

| 항목 | 내용 |
| --- | --- |
| 관련 파일 | `frontend/src/app/analyze/page.tsx`, `frontend/src/features/analysis/components/WorkspaceReport.tsx`, `frontend/src/features/repository/components/RepositoryLauncher.tsx` |
| 관련 이슈 | Issue #178 |
| 관련 API | `PROJECT-REPO-API-003` |

**설명**

분석 리포트가 준비됐지만 RAG 임베딩/인덱싱이 아직 진행 중인 상태를 전체 `running` 화면으로 취급하지 않습니다. 사용자는 즉시 볼 수 있는 report, Repository, Dashboard를 먼저 확인하고, Chat/RAG 기능만 준비 상태를 별도로 안내받아야 합니다.

**구현 노트**

- 화면 상태는 최소 `reportReady`, `ragReady`, `chatReady`로 분리합니다.
- `reportReady=true`이면 리포트와 Repository를 표시하고, `ragReady=false`이면 Chat 영역에 인덱싱 중 banner를 표시합니다.
- RAG 인덱싱 실패는 전체 분석 실패로 보이지 않게 하며, RAG/Chat action에만 retry 또는 비활성 이유를 표시합니다.
- backend status가 단일 문자열만 제공하는 경우 frontend는 report payload 존재 여부와 indexing status를 조합해 derived state를 만듭니다.

**완료 조건**

- 리포트가 준비된 상태에서는 RAG 인덱싱 중이어도 분석 결과 화면이 표시됩니다.
- Chat이 비활성화된 이유와 다음 상태가 사용자에게 보입니다.
- RAG 인덱싱 실패가 report 표시를 막지 않습니다.

---

## PROJECT-ANALYZE-F-106: 브라우저 기본 alert/confirm 대체

| 항목 | 내용 |
| --- | --- |
| 관련 파일 | `frontend/src/app/analyze/page.tsx`, `frontend/src/features/repository/components/RepositoryLauncher.tsx`, `frontend/src/features/repository/components/RepoInput.tsx` |
| 관련 이슈 | Issue #179 |

**설명**

분석 입력, 검증 실패, 위험 action 확인에 `window.alert`/`window.confirm`을 사용하지 않고 제품 UI 안의 field-level 오류, banner/toast, confirm modal로 표시합니다.

**구현 노트**

- 입력 검증 실패는 입력칸 아래 helper/error text로 표시합니다.
- 비동기 작업 실패는 dismissible banner 또는 toast로 표시합니다.
- 삭제, 재시도, 장시간 실행 같은 action은 focus trap, ESC 닫기, keyboard navigation을 갖춘 confirm modal을 사용합니다.
- 오류 발생 후 사용자가 수정해야 할 입력 또는 action 영역으로 focus를 이동합니다.

**완료 조건**

- analyze/repository 주요 흐름에서 `window.alert`와 `window.confirm`을 사용하지 않습니다.
- 검증 오류, 비동기 실패, 확인 modal이 각각 일관된 UI 패턴으로 표시됩니다.
- 키보드만으로 confirm modal을 완료/취소할 수 있습니다.
