# PROJECT CORE 기능 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-CORE | **최종 업데이트**: 2026-06-26

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 관련 이슈 | 작업 상태 |
| --- | --- | --- | --- | --- | --- |
| PROJECT-CORE-F-201 | 공통 API 에러 파서 | Frontend | Phase 2 | Issue #176 | 제안 |
| PROJECT-CORE-F-202 | 접근성/i18n/motion baseline | Frontend | Phase 2 | Issue #180 | 제안 |

---

## PROJECT-CORE-F-201: 공통 API 에러 파서

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CORE |
| 관련 이슈 | Issue #176 |
| 관련 문서 | `ERROR_CODES.md`, `ERROR_HANDLING.md` |

**설명**

Auth, Analysis, Chat, List 등 frontend API client가 backend 오류 envelope를 서로 다른 방식으로 해석하지 않도록 공통 `parseApiError` 규칙을 둡니다.

**구현 노트**

- parser 출력 형태는 `{ status, code, message, field, retryable, detail }`을 기준으로 합니다.
- UI에 표시할 문구는 최상위 `message` 또는 `error.code`별 사용자 문구 mapping을 우선합니다.
- `error.detail`이 객체여도 `[object Object]`를 직접 렌더링하지 않습니다.
- `error.field`가 있으면 field-level 오류로, 없으면 page/form-level 오류로 전달합니다.

**완료 조건**

- 주요 frontend API client가 같은 parser를 사용합니다.
- Auth/Analysis/Chat/List 오류 표시 방식이 일관됩니다.
- parser 단위 테스트 또는 대표 API client 테스트가 추가됩니다.

---

## PROJECT-CORE-F-202: 접근성/i18n/motion baseline

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CORE |
| 관련 이슈 | Issue #180 |
| 관련 문서 | `ARCHITECTURE.md` |

**설명**

제품 전반의 언어 기준, 접근성 이름, focus 처리, motion 감소 설정을 공통 UI 품질 기준으로 정리합니다.

**구현 노트**

- `html lang`과 앱 locale 기본값은 제품 기본 언어와 일치해야 합니다.
- icon-only button은 `aria-label`을 필수로 갖고, `title`은 tooltip 보조 용도로만 사용합니다.
- modal, toast, banner는 screen reader label, focus 이동, keyboard navigation을 만족해야 합니다.
- framer-motion 등 애니메이션은 `prefers-reduced-motion`에서 duration 0 또는 정적 강조로 대체합니다.

**완료 조건**

- 주요 auth/analyze/chat/repository/history 화면의 언어 기준이 일관됩니다.
- icon-only control이 의미 있는 accessible name을 갖습니다.
- reduced motion 설정에서 흔들림/전환 애니메이션이 과하게 실행되지 않습니다.
