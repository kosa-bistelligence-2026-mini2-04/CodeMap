# 작업 결과 보고서 — 이슈 #160 파일 클릭 시 코드 프리뷰 표시

작성일: 2026-06-26
브랜치: fix/issue-160

---

## 1. 작업 개요

`/analyze` 페이지 REPOSITORY 패널에서 파일을 클릭하면 선택 상태만 바뀌고 실제 코드가 표시되지 않던 문제를 해결합니다. 백엔드에 job-scoped 파일 읽기 API를 추가하고, 프론트엔드에 `CodePreviewPanel` 컴포넌트를 신설하여 파일 클릭 → 코드 미리보기를 구현합니다.

---

## 2. 변경 파일 목록

| 파일 | 유형 | 내용 |
|------|------|------|
| `backend/app/common/exceptions.py` | 수정 | 신규 예외 3종 추가 |
| `backend/app/repo/schemas.py` | 수정 | `FileContentData`, `FileContentResponse` 스키마 추가 |
| `backend/app/repo/router.py` | 수정 | `GET /api/repo/analysis/{job_id}/files/content` 엔드포인트 추가 |
| `frontend/src/features/analysis/api/api.ts` | 수정 | `fetchFileContent` 함수 추가 |
| `frontend/src/features/analysis/components/CodePreviewPanel.tsx` | 신규 | 코드 미리보기 패널 컴포넌트 |
| `frontend/src/app/analyze/page.tsx` | 수정 | `CodePreviewPanel` 연결 |
| `docs/03_Specifications/PHASE2_API_SPEC.md` | 수정 | `REPO-FILE-API-001` 명세 추가 |

---

## 3. 구현 상세

### 3-1. 백엔드 — 파일 컨텐츠 조회 API

**엔드포인트**: `GET /api/repo/analysis/{job_id}/files/content?path=...`

처리 순서:
1. `AnalysisService.get_job_status(job_id)` 로 job 존재 확인 → 없으면 `JobNotFoundError` (404)
2. clone workspace 경로 계산: `{CLONE_BASE_DIR}/{job_id}/repo`
3. workspace 디렉토리 존재 확인 → 없으면 `WorkspaceNotReadyError` (404)
4. `..` 세그먼트 포함 여부 + `Path.resolve().relative_to()` 이중 path traversal 차단 → `FilePathForbiddenError` (403)
5. 바이너리 확장자 집합 (`_BINARY_EXTENSIONS`) 매칭 → `BinaryFileError` (422)
6. `asyncio.to_thread(_read_file_safe, ...)` 로 블로킹 I/O를 이벤트 루프 외부에서 실행
7. UTF-8 → CP949 → latin-1 순서로 인코딩 fallback
8. 50,000자 초과 시 잘린 내용 + `truncated=true` 반환

### 3-2. 프론트엔드 — CodePreviewPanel

- `filePath` prop 변경 시 `useEffect`에서 `fetchFileContent` 호출
- `AbortController`로 이전 요청 취소 (컴포넌트 언마운트 또는 파일 재선택 시 cleanup)
- loading / error / success / truncated 경고 상태를 각각 UI로 표시
- 줄 번호 + 코드 내용을 `<table>` 구조로 렌더링
- 복사 버튼, 닫기 버튼 제공

### 3-3. 프론트엔드 — analyze/page.tsx 연결

- `status === "completed"` 이고 `selectedFile` 이 있을 때 `CodePreviewPanel` 표시
- `xl:` 브레이크포인트 이상에서는 `WorkspaceReport`와 좌우 병렬 배치; 미만에서는 `CodePreviewPanel`이 전체 너비 차지
- `onClose` 콜백으로 `setSelectedFile(null)` 연결

---

## 4. Self 리뷰 — 정적 분석 9대 항목 검증 결과

| 항목 | 결과 | 비고 |
|------|------|------|
| 1. KeyError 방어 | 이상 없음 | 딕셔너리 직접 접근 없음 |
| 2. Null-Safety (AttributeError/TypeError) | 이상 없음 | `target.exists()`, `target.is_file()` 가드 처리 |
| 3. Exception Safety | 이상 없음 | 파일 I/O를 `try-except` 블록으로 처리, 인코딩 fallback 적용 |
| 4. 비동기 블로킹 방어 | 이상 없음 | 파일 읽기를 `asyncio.to_thread` 로 격리 |
| 5. 데이터 불변성 | 이상 없음 | 공유 상태 직접 수정 없음 |
| 6. 연계 코드 영향도 | 이상 없음 | 기존 엔드포인트·스키마·예외 클래스 비파괴적 확장 |
| 7. 리소스 누수 방어 | 이상 없음 | `AbortController` cleanup, 파일 스트림은 `Path.read_text()` 자동 해제 |
| 8. 관측 가능성 | 이상 없음 | 빈 `except` 없음 |
| 9. 스키마 검증 / 타입 엄격성 | 이상 없음 | Pydantic `FileContentResponse`, TypeScript `tsc --noEmit` 오류 없음 |

---

## 5. 완료 기준 충족 여부

| 완료 기준 | 충족 여부 |
|-----------|-----------|
| Repository 파일 클릭 시 실제 파일 내용이 표시됨 | ✓ |
| 허용되지 않는 경로, 바이너리, 대용량 파일은 안전한 오류 UI로 표시됨 | ✓ |
| `/analyze` compact layout에서 report / repository / chat 간 이동이 깨지지 않음 | ✓ |
